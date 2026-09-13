import os
import sys
import json
import pymysql
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "")
db_name = os.getenv("DB_NAME", "hospital_appointment_system")

def mask_password(pwd):
    if not pwd:
        return "<EMPTY>"
    return "*" * len(pwd)

print("=" * 60)
print("Hospital Appointment System - Database Connection Verification")
print("=" * 60)
print(f"Host:     {db_host}")
print(f"Port:     {db_port}")
print(f"User:     {db_user}")
print(f"Password: {mask_password(db_password)}")
print(f"Database: {db_name}")
print("-" * 60)

if not db_password and db_password != "":
    # Note: user might have blank password if explicitly set to blank, but usually not
    pass

try:
    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )
    print("SUCCESS: Connected to MySQL database successfully!\n")
    
    schema_info = {}
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables in '{db_name}':")
        for t in tables:
            print(f" - {t}")
            cursor.execute(f"DESCRIBE `{t}`;")
            columns = cursor.fetchall()
            schema_info[t] = {
                "columns": columns,
                "primary_key": [c["Field"] for c in columns if c["Key"] == "PRI"]
            }
            
        # Get foreign keys
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, 
                   REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL;
        """, (db_name,))
        foreign_keys = cursor.fetchall()
        
        for fk in foreign_keys:
            t = fk["TABLE_NAME"]
            if t in schema_info:
                if "foreign_keys" not in schema_info[t]:
                    schema_info[t]["foreign_keys"] = []
                schema_info[t]["foreign_keys"].append(fk)
                
    # Save schema metadata to schema_meta.json
    meta_path = os.path.join(os.path.dirname(__file__), "schema_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(schema_info, f, indent=2)
    print(f"\nSchema metadata successfully extracted and saved to: {meta_path}")
    print("=" * 60)
    conn.close()
    sys.exit(0)

except pymysql.MySQLError as e:
    print(f"ERROR: Failed to connect to MySQL database:")
    print(f"Code: {e.args[0] if len(e.args) > 0 else 'Unknown'}")
    print(f"Message: {e.args[1] if len(e.args) > 1 else str(e)}")
    print("-" * 60)
    if "Access denied" in str(e):
        print("Please check your MySQL username and password in the .env file:")
        print(f"File location: {os.path.abspath('.env')}")
    elif "Unknown database" in str(e):
        print(f"The database '{db_name}' was not found on your MySQL server.")
        print(f"You can create it by running: CREATE DATABASE {db_name};")
    sys.exit(1)
except Exception as e:
    print(f"UNEXPECTED ERROR: {e}")
    sys.exit(1)
