# Hospital Appointment System - Full-Stack DBMS Project

A clean, responsive hospital management web application designed for a college DBMS project, running on **Python 3.11 + Flask** and connecting directly to local **MySQL** (`hospital_appointment_system`).

---

## Features

1. **Dashboard Overview**:
   - Live metrics (Total Patients, Active Doctors, Total Appointments, Pending Invoices, Paid Revenue).
   - Recent appointments list with patient & doctor relational details.
   - Quick action shortcuts.
2. **Patients Page**:
   - View all registered patients in MySQL.
   - Real-time client-side search.
   - Add new patient modal.
   - Edit patient modal.
   - Delete patient with confirmation dialog.
3. **Doctors Page**:
   - Manage hospital specialists, departments, contact info, and consultation fees.
   - Full CRUD operations.
4. **Appointments Page**:
   - Relational appointment booking linking Patients and Doctors.
   - Status tracking (`Scheduled`, `Completed`, `Cancelled`).
   - Full CRUD operations.
5. **Prescriptions Page**:
   - Record medication orders with dosages, usage instructions, and dates.
   - Relational links to patient and doctor.
   - Full CRUD operations.
6. **Billing & Invoices Page**:
   - Generate patient bills with payment status (`Pending`, `Paid`) and payment methods (`Cash`, `Card`, `UPI`, `Insurance`).
   - One-click "Mark Paid" action.
   - Full CRUD operations.

---

## Setup & Running Instructions

### 1. Configure Environment Variables
Open the `.env` file in the project root:
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=hospital_appointment_system
SECRET_KEY=hospital_appointment_system_secret_key_2026
```
Enter your MySQL password in `DB_PASSWORD`.

### 2. Verify Database Connection & Inspect Tables
Run the verification script to test connection and inspect existing database tables:
```bash
.venv\Scripts\python.exe verify_db.py
```

### 3. Start the Web Application
```bash
.venv\Scripts\python.exe app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
