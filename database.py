import sqlite3
import os  # <-- ADD THIS IMPORT
from werkzeug.security import generate_password_hash # <-- ADD THIS IMPORT

# Use Render's persistent disk path if 'DB_PATH' env var is set,
# otherwise, use 'clinic.db' for local development.
DB_PATH = os.environ.get('DB_PATH', 'clinic.db')

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_PATH) # <-- CHANGE THIS LINE
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with the required schema and a trigger."""
    print(f"Initializing database at {DB_PATH}") # Optional: good for logging
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ... (rest of your init_db function is unchanged) ...

    # Drop tables if they exist (for easy re-initialization)
    cursor.execute("DROP TABLE IF EXISTS billing;")
    cursor.execute("DROP TABLE IF EXISTS appointments;")
    cursor.execute("DROP TABLE IF EXISTS patients;")
    cursor.execute("DROP TABLE IF EXISTS doctors;")

    # --- Create Tables ---

    # Doctors Table
    cursor.execute("""
    CREATE TABLE doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        avail_start_time TIME NOT NULL,
        avail_end_time TIME NOT NULL
    );
    """)
    # ... after creating doctors table ...

    # Drop user table if exists
    cursor.execute("DROP TABLE IF EXISTS users;")
    
    # Users Table
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT_NULL UNIQUE,
        password_hash TEXT NOT_NULL
    );
    """)

    # ... before creating patients table ...
    # Patients Table
    # medical_history: In a real system, this sensitive data should be encrypted.
    cursor.execute("""
    CREATE TABLE patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        dob DATE NOT NULL,
        contact TEXT NOT NULL,
        medical_history TEXT
    );
    """)

    # Appointments Table
    cursor.execute("""
    CREATE TABLE appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appt_datetime DATETIME NOT NULL,
        status TEXT NOT NULL DEFAULT 'Scheduled',  -- Scheduled, Completed, Cancelled
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (doctor_id) REFERENCES doctors (id)
    );
    """)

    # Billing Table
    cursor.execute("""
    CREATE TABLE billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending', -- Pending, Paid
        issued_date DATE DEFAULT (CURRENT_DATE),
        FOREIGN KEY (appointment_id) REFERENCES appointments (id)
    );
    """)

    # --- DBMS Concept: Trigger ---
    # This trigger automatically creates a bill when an appointment status
    # is updated to 'Completed'. We set a default amount for simplicity.
    cursor.execute("""
    CREATE TRIGGER create_bill_after_appointment
    AFTER UPDATE ON appointments
    FOR EACH ROW
    WHEN NEW.status = 'Completed' AND OLD.status != 'Completed'
    BEGIN
        INSERT INTO billing (appointment_id, amount, status)
        VALUES (NEW.id, 150.00, 'Pending');
    END;
    """)
    
    # --- Insert Sample Data ---
    cursor.execute("INSERT INTO doctors (name, specialization, avail_start_time, avail_end_time) VALUES (?, ?, ?, ?)",
                   ('Dr. Alice Smith', 'Cardiologist', '09:00:00', '17:00:00'))
    cursor.execute("INSERT INTO doctors (name, specialization, avail_start_time, avail_end_time) VALUES (?, ?, ?, ?)",
                   ('Dr. Bob Johnson', 'Pediatrician', '10:00:00', '18:00:00'))

    cursor.execute("INSERT INTO patients (name, dob, contact, medical_history) VALUES (?, ?, ?, ?)",
                   ('John Doe', '1990-05-15', '555-1234', 'Allergy to penicillin.'))
    cursor.execute("INSERT INTO patients (name, dob, contact, medical_history) VALUES (?, ?, ?, ?)",
                   ('Jane Roe', '1985-11-20', '555-5678', 'History of asthma.'))


    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")