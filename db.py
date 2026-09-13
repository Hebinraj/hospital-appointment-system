import os
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "hospital_appointment")

def get_connection():
    """Returns a new PyMySQL connection to the database."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def test_connection():
    """Tests if MySQL is reachable and returns (success: bool, message: str)."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return True, "Connected successfully"
    except Exception as e:
        return False, str(e)

def query_all(sql, params=None):
    """Executes a SELECT query and returns all rows as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()

def query_one(sql, params=None):
    """Executes a SELECT query and returns a single row as a dict."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()

def execute(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and returns affected rows or lastrowid."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid or cur.rowcount
    finally:
        conn.close()

def get_table_schema(table_name):
    """Inspects table columns, data types, and primary key from MySQL."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE `{table_name}`;")
            cols = cur.fetchall()
            pk = None
            for c in cols:
                if c["Key"] == "PRI":
                    pk = c["Field"]
                    break
            if not pk and cols:
                pk = cols[0]["Field"]
            return {"columns": cols, "pk": pk}
    finally:
        conn.close()

def get_all_tables():
    """Lists all table names in the target database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            rows = cur.fetchall()
            return [list(r.values())[0] for r in rows]
    finally:
        conn.close()

# ==========================================================
# AUTHENTICATION & USERS TABLE MANAGEMENT
# ==========================================================
def init_users_table():
    """Creates the users table if it does not already exist."""
    create_sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role ENUM('Admin', 'Doctor', 'Receptionist') NOT NULL,
            doctor_id INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE SET NULL
        );
    """
    execute(create_sql)

    

def get_user_by_username(username):
    """Retrieves a user record by username."""
    return query_one("SELECT * FROM users WHERE username = %s", (username,))

def get_user_by_id(user_id):
    """Retrieves a user record by user_id."""
    return query_one("SELECT * FROM users WHERE user_id = %s", (user_id,))

def check_password(plain_password, password_hash):
    """Verifies a plain-text password against its stored hash."""
    return check_password_hash(password_hash, plain_password)

