import os
import sys
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hospital_appointment_system_secret_key_2026")

# ==========================================================
# AUTH DECORATORS
# ==========================================================

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Return 403-style flash + redirect if user's role is not in allowed roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash(f"Access denied. This action requires: {', '.join(roles)} role.", "error")
                return redirect(request.referrer or url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def check_db_health():
    """Checks if MySQL database is reachable and returns status."""
    return db.test_connection()

from functools import wraps


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("dashboard"))

            return view(*args, **kwargs)
        return wrapped_view
    return decorator

@app.context_processor
def inject_db_status():
    """Injects database status and metadata into all templates."""
    status, err = check_db_health()
    return {
        "db_status": status,
        "db_error": err if not status else None,
        "db_name": db.DB_NAME
    }


# ==========================================================
# AUTH ROUTES
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in → redirect to dashboard
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")

        user = db.get_user_by_username(username)

        if user and db.check_password(password, user["password_hash"]):
            session.clear()
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}! Logged in as {user['role']}.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    full_name = session.get("full_name", "User")
    session.clear()
    flash(f"You have been logged out successfully, {full_name}.", "success")
    return redirect(url_for("login"))

# ==========================================================
# AUTHENTICATION
# ==========================================================

# ==========================================================
# 1. DASHBOARD
# ==========================================================
@app.route("/")
@login_required
def dashboard():
    status, _ = check_db_health()
    stats = {
        "patients_count": 0,
        "doctors_count": 0,
        "appointments_count": 0,
        "pending_bills_count": 0,
        "total_revenue": 0.0
    }
    recent_appointments = []

    if status:
        try:
            # Query counts
            p_cnt = db.query_one("SELECT COUNT(*) AS cnt FROM patients")
            if p_cnt: stats["patients_count"] = p_cnt["cnt"]

            d_cnt = db.query_one("SELECT COUNT(*) AS cnt FROM doctors")
            if d_cnt: stats["doctors_count"] = d_cnt["cnt"]

            a_cnt = db.query_one("SELECT COUNT(*) AS cnt FROM appointments")
            if a_cnt: stats["appointments_count"] = a_cnt["cnt"]

            # Pending and revenue from billing
            b_pending = db.query_one("SELECT COUNT(*) AS cnt FROM billing WHERE LOWER(payment_status) = 'pending'")
            if b_pending: stats["pending_bills_count"] = b_pending["cnt"]

            b_rev = db.query_one("SELECT COALESCE(SUM(amount), 0) AS total FROM billing WHERE LOWER(payment_status) = 'paid'")
            if b_rev: stats["total_revenue"] = float(b_rev["total"])

            # Recent appointments with relational JOIN
            recent_sql = """
                SELECT a.appointment_id, a.appointment_date, a.appointment_time, a.status,
                       p.patient_id, p.name AS patient_name, p.phone AS patient_phone,
                       d.doctor_id, d.name AS doctor_name, d.specialization AS doctor_spec
                FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
                ORDER BY a.appointment_id DESC
                LIMIT 5
            """
            recent_appointments = db.query_all(recent_sql)
        except Exception as e:
            flash(f"Error loading dashboard metrics: {e}", "warning")

    return render_template("dashboard.html", active_page="dashboard", stats=stats, recent_appointments=recent_appointments)


# ==========================================================
# 2. PATIENTS CRUD
# Table columns: patient_id, name, age, gender, phone, address
# ==========================================================
@app.route("/patients")
@login_required
def patients_list():
    patients = []
    if check_db_health()[0]:
        try:
            patients = db.query_all("SELECT * FROM patients ORDER BY patient_id DESC")
        except Exception as e:
            flash(f"Error fetching patients: {e}", "error")
    return render_template("patients.html", active_page="patients", patients=patients)

@app.route("/patients/add", methods=["POST"])
@role_required("Admin", "Receptionist")
def patients_add():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not name or not phone:
        flash("Patient Name and Phone Number are required!", "error")
        return redirect(url_for("patients_list"))

    try:
        sql = """
            INSERT INTO patients (name, age, gender, phone, address)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute(sql, (name, int(age) if age.isdigit() else None, gender or None, phone, address or None))
        flash(f"Patient '{name}' successfully registered in MySQL!", "success")
    except Exception as e:
        flash(f"Failed to add patient: {e}", "error")

    return redirect(url_for("patients_list"))

@app.route("/patients/edit/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def patients_edit(id):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    try:
        sql = """
            UPDATE patients
            SET name = %s, age = %s, gender = %s, phone = %s, address = %s
            WHERE patient_id = %s
        """
        db.execute(sql, (name, int(age) if age.isdigit() else None, gender or None, phone, address or None, id))
        flash(f"Patient #{id} details updated successfully!", "success")
    except Exception as e:
        flash(f"Failed to update patient: {e}", "error")

    return redirect(url_for("patients_list"))

@app.route("/patients/delete/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def patients_delete(id):
    try:
        db.execute("DELETE FROM patients WHERE patient_id = %s", (id,))
        flash(f"Patient #{id} deleted successfully from database.", "success")
    except Exception as e:
        flash(f"Failed to delete patient #{id}: {e}", "error")
    return redirect(url_for("patients_list"))


# ==========================================================
# 3. DOCTORS CRUD
# Table columns: doctor_id, name, specialization, phone, email
# ==========================================================
@app.route("/doctors")
@login_required
def doctors_list():
    doctors = []
    if check_db_health()[0]:
        try:
            doctors = db.query_all("SELECT * FROM doctors ORDER BY doctor_id DESC")
        except Exception as e:
            flash(f"Error fetching doctors: {e}", "error")
    return render_template("doctors.html", active_page="doctors", doctors=doctors)

@app.route("/doctors/add", methods=["POST"])
@role_required("Admin")
def doctors_add():
    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not phone:
        flash("Doctor Name and Phone Number are required!", "error")
        return redirect(url_for("doctors_list"))

    try:
        sql = """
            INSERT INTO doctors (name, specialization, phone, email)
            VALUES (%s, %s, %s, %s)
        """
        db.execute(sql, (name, specialization or None, phone, email or None))
        flash(f"Doctor '{name}' added successfully to MySQL!", "success")
    except Exception as e:
        flash(f"Failed to add doctor: {e}", "error")

    return redirect(url_for("doctors_list"))

@app.route("/doctors/edit/<int:id>", methods=["POST"])
@role_required("Admin")
def doctors_edit(id):
    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    try:
        sql = """
            UPDATE doctors
            SET name = %s, specialization = %s, phone = %s, email = %s
            WHERE doctor_id = %s
        """
        db.execute(sql, (name, specialization or None, phone, email or None, id))
        flash(f"Doctor #{id} ('{name}') updated successfully!", "success")
    except Exception as e:
        flash(f"Failed to update doctor: {e}", "error")

    return redirect(url_for("doctors_list"))

@app.route("/doctors/delete/<int:id>", methods=["POST"])
@role_required("Admin")
def doctors_delete(id):
    try:
        db.execute("DELETE FROM doctors WHERE doctor_id = %s", (id,))
        flash(f"Doctor #{id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete doctor #{id}: {e}", "error")
    return redirect(url_for("doctors_list"))


# ==========================================================
# 4. APPOINTMENTS CRUD
# Table columns: appointment_id, patient_id, doctor_id, appointment_date, appointment_time, status
# ==========================================================
@app.route("/appointments")
@login_required
def appointments_list():
    appointments = []
    patients = []
    doctors = []

    if check_db_health()[0]:
        try:
            sql = """
                SELECT a.appointment_id, a.patient_id, a.doctor_id, 
                       a.appointment_date, a.appointment_time, a.status,
                       p.name AS patient_name, p.phone AS patient_phone,
                       d.name AS doctor_name, d.specialization AS doctor_spec
                FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
                ORDER BY a.appointment_id DESC
            """
            appointments = db.query_all(sql)
            patients = db.query_all("SELECT patient_id, name, phone FROM patients ORDER BY name ASC")
            doctors = db.query_all("SELECT doctor_id, name, specialization FROM doctors ORDER BY name ASC")
        except Exception as e:
            flash(f"Error fetching appointments: {e}", "error")

    return render_template("appointments.html",
                           active_page="appointments",
                           appointments=appointments,
                           patients=patients,
                           doctors=doctors)

@app.route("/appointments/add", methods=["POST"])
@role_required("Admin", "Receptionist")
def appointments_add():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    app_date = request.form.get("appointment_date")
    app_time = request.form.get("appointment_time")
    status = request.form.get("status", "Scheduled")

    if not patient_id or not doctor_id or not app_date or not app_time:
        flash("Patient, Doctor, Date, and Time are required!", "error")
        return redirect(url_for("appointments_list"))

    try:
        sql = """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute(sql, (patient_id, doctor_id, app_date, app_time, status))
        flash("Appointment scheduled successfully!", "success")
    except Exception as e:
        flash(f"Failed to schedule appointment: {e}", "error")

    return redirect(url_for("appointments_list"))

@app.route("/appointments/edit/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist", "Doctor")
def appointments_edit(id):
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    app_date = request.form.get("appointment_date")
    app_time = request.form.get("appointment_time")
    status = request.form.get("status", "Scheduled")

    try:
        sql = """
            UPDATE appointments
            SET patient_id = %s, doctor_id = %s, appointment_date = %s, 
                appointment_time = %s, status = %s
            WHERE appointment_id = %s
        """
        db.execute(sql, (patient_id, doctor_id, app_date, app_time, status, id))
        flash(f"Appointment #{id} updated successfully!", "success")
    except Exception as e:
        flash(f"Failed to update appointment: {e}", "error")

    return redirect(url_for("appointments_list"))

@app.route("/appointments/delete/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def appointments_delete(id):
    try:
        db.execute("DELETE FROM appointments WHERE appointment_id = %s", (id,))
        flash(f"Appointment #{id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete appointment #{id}: {e}", "error")
    return redirect(url_for("appointments_list"))


# ==========================================================
# 5. PRESCRIPTIONS CRUD
# Table columns: prescription_id, appointment_id, medicines, dosage, instructions
# ==========================================================
@app.route("/prescriptions")
@login_required
def prescriptions_list():
    prescriptions = []
    appointments = []

    if check_db_health()[0]:
        try:
            sql = """
                SELECT pr.prescription_id, pr.appointment_id, pr.medicines, pr.dosage, pr.instructions,
                       a.appointment_date, a.appointment_time,
                       p.name AS patient_name,
                       d.name AS doctor_name
                FROM prescriptions pr
                LEFT JOIN appointments a ON pr.appointment_id = a.appointment_id
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
                ORDER BY pr.prescription_id DESC
            """
            prescriptions = db.query_all(sql)

            # Available appointments for writing prescription
            appointments_sql = """
                SELECT a.appointment_id, a.appointment_date, a.appointment_time,
                       p.name AS patient_name,
                       d.name AS doctor_name
                FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
                ORDER BY a.appointment_id DESC
            """
            appointments = db.query_all(appointments_sql)
        except Exception as e:
            flash(f"Error fetching prescriptions: {e}", "error")

    return render_template("prescriptions.html",
                           active_page="prescriptions",
                           prescriptions=prescriptions,
                           appointments=appointments)

@app.route("/prescriptions/add", methods=["POST"])
@role_required("Admin", "Doctor")
def prescriptions_add():
    appointment_id = request.form.get("appointment_id")
    medicines = request.form.get("medicines", "").strip()
    dosage = request.form.get("dosage", "").strip()
    instructions = request.form.get("instructions", "").strip()

    if not appointment_id or not medicines:
        flash("Appointment selection and Medicine name are required!", "error")
        return redirect(url_for("prescriptions_list"))

    try:
        sql = """
            INSERT INTO prescriptions (appointment_id, medicines, dosage, instructions)
            VALUES (%s, %s, %s, %s)
        """
        db.execute(sql, (appointment_id, medicines, dosage or None, instructions or None))
        flash("Prescription recorded successfully in MySQL!", "success")
    except Exception as e:
        flash(f"Failed to add prescription: {e}", "error")

    return redirect(url_for("prescriptions_list"))

@app.route("/prescriptions/edit/<int:id>", methods=["POST"])
@role_required("Admin", "Doctor")
def prescriptions_edit(id):
    appointment_id = request.form.get("appointment_id")
    medicines = request.form.get("medicines", "").strip()
    dosage = request.form.get("dosage", "").strip()
    instructions = request.form.get("instructions", "").strip()

    try:
        sql = """
            UPDATE prescriptions
            SET appointment_id = %s, medicines = %s, dosage = %s, instructions = %s
            WHERE prescription_id = %s
        """
        db.execute(sql, (appointment_id, medicines, dosage or None, instructions or None, id))
        flash(f"Prescription #{id} updated successfully!", "success")
    except Exception as e:
        flash(f"Failed to update prescription: {e}", "error")

    return redirect(url_for("prescriptions_list"))

@app.route("/prescriptions/delete/<int:id>", methods=["POST"])
@role_required("Admin", "Doctor")
def prescriptions_delete(id):
    try:
        db.execute("DELETE FROM prescriptions WHERE prescription_id = %s", (id,))
        flash(f"Prescription #{id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete prescription #{id}: {e}", "error")
    return redirect(url_for("prescriptions_list"))


# ==========================================================
# 6. BILLING CRUD
# Table columns: bill_id, patient_id, appointment_id, amount, payment_status, payment_date
# ==========================================================
@app.route("/billing")
@login_required
def billing_list():
    bills = []
    patients = []
    appointments = []

    if check_db_health()[0]:
        try:
            sql = """
                SELECT b.bill_id, b.patient_id, b.appointment_id, b.amount, b.payment_status, b.payment_date,
                       p.name AS patient_name, p.phone AS patient_phone
                FROM billing b
                LEFT JOIN patients p ON b.patient_id = p.patient_id
                ORDER BY b.bill_id DESC
            """
            bills = db.query_all(sql)
            patients = db.query_all("SELECT patient_id, name, phone FROM patients ORDER BY name ASC")
            appointments = db.query_all("""
                SELECT a.appointment_id, a.appointment_date, p.name AS patient_name
                FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.patient_id
                ORDER BY a.appointment_id DESC
            """)
        except Exception as e:
            flash(f"Error fetching billing records: {e}", "error")

    return render_template("billing.html",
                           active_page="billing",
                           bills=bills,
                           patients=patients,
                           appointments=appointments)

@app.route("/billing/add", methods=["POST"])
@role_required("Admin", "Receptionist")
def billing_add():
    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id") or None
    amount = request.form.get("amount", "0.00").strip()
    payment_status = request.form.get("payment_status", "Pending")
    payment_date = request.form.get("payment_date") or None

    if not patient_id or not amount:
        flash("Patient and Bill Amount are required!", "error")
        return redirect(url_for("billing_list"))

    try:
        sql = """
            INSERT INTO billing (patient_id, appointment_id, amount, payment_status, payment_date)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute(sql, (patient_id, appointment_id, float(amount), payment_status, payment_date or None))
        flash("Invoice generated successfully in MySQL!", "success")
    except Exception as e:
        flash(f"Failed to generate invoice: {e}", "error")

    return redirect(url_for("billing_list"))

@app.route("/billing/edit/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def billing_edit(id):
    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id") or None
    amount = request.form.get("amount", "0.00").strip()
    payment_status = request.form.get("payment_status", "Pending")
    payment_date = request.form.get("payment_date") or None

    try:
        sql = """
            UPDATE billing
            SET patient_id = %s, appointment_id = %s, amount = %s,
                payment_status = %s, payment_date = %s
            WHERE bill_id = %s
        """
        db.execute(sql, (patient_id, appointment_id, float(amount), payment_status, payment_date or None, id))
        flash(f"Invoice #{id} updated successfully!", "success")
    except Exception as e:
        flash(f"Failed to update invoice: {e}", "error")

    return redirect(url_for("billing_list"))

@app.route("/billing/mark-paid/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def billing_mark_paid(id):
    try:
        today_str = date.today().isoformat()
        db.execute("UPDATE billing SET payment_status = 'Paid', payment_date = %s WHERE bill_id = %s", (today_str, id))
        flash(f"Invoice #{id} marked as Paid!", "success")
    except Exception as e:
        flash(f"Failed to update payment status: {e}", "error")
    return redirect(url_for("billing_list"))

@app.route("/billing/delete/<int:id>", methods=["POST"])
@role_required("Admin", "Receptionist")
def billing_delete(id):
    try:
        db.execute("DELETE FROM billing WHERE bill_id = %s", (id,))
        flash(f"Invoice #{id} deleted successfully from database.", "success")
    except Exception as e:
        flash(f"Failed to delete invoice #{id}: {e}", "error")
    return redirect(url_for("billing_list"))


# ==========================================================
# RUN APPLICATION
# ==========================================================
if __name__ == "__main__":
    print(f"Connected Database: {db.DB_NAME}")
    print("Starting Hospital Appointment System Web Application...")
    print("Accessible locally at: http://127.0.0.1:5000")

app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    debug=False
)