from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
import os
from datetime import datetime
from database import get_db_connection, init_db

# --- CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'

# Get DB path (default to 'clinic.db')
DB_PATH = os.environ.get('DB_PATH', 'clinic.db')

# Initialize DB if not exists
if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}. Initializing...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

# --- FLASK-LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


class User(UserMixin):
    """User model for Flask-Login."""
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    """Load user from session."""
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_row:
        return User(id=user_row['id'], username=user_row['username'])
    return None


# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_row and check_password_hash(user_row['password_hash'], password):
            user_obj = User(id=user_row['id'], username=user_row['username'])
            login_user(user_obj)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# --- DASHBOARD ---
@app.route('/')
@login_required
def index():
    """Dashboard: Shows upcoming appointments."""
    conn = get_db_connection()
    appointments = conn.execute("""
        SELECT a.id, p.name AS patient_name, d.name AS doctor_name, a.appt_datetime, a.status
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.status = 'Scheduled' AND a.appt_datetime >= CURRENT_TIMESTAMP
        ORDER BY a.appt_datetime ASC
    """).fetchall()
    conn.close()
    return render_template('index.html', appointments=appointments)


# --- PATIENT ROUTES ---
@app.route('/patients')
@login_required
def list_patients():
    conn = get_db_connection()
    patients = conn.execute("SELECT * FROM patients ORDER BY name").fetchall()
    conn.close()
    return render_template('patients.html', patients=patients)


@app.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    name = request.form['name']
    dob = request.form['dob']
    contact = request.form['contact']
    medical_history = request.form['medical_history']

    conn = get_db_connection()
    conn.execute("INSERT INTO patients (name, dob, contact, medical_history) VALUES (?, ?, ?, ?)",
                 (name, dob, contact, medical_history))
    conn.commit()
    conn.close()
    flash('Patient added successfully!', 'success')
    return redirect(url_for('list_patients'))


@app.route('/patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def patient_detail(patient_id):
    conn = get_db_connection()

    if request.method == 'POST':
        medical_history = request.form['medical_history']
        conn.execute("UPDATE patients SET medical_history = ? WHERE id = ?", (medical_history, patient_id))
        conn.commit()
        flash('Medical history updated.', 'success')

    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    history = conn.execute("""
        SELECT a.appt_datetime, d.name AS doctor_name, a.status
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ? ORDER BY a.appt_datetime DESC
    """, (patient_id,)).fetchall()
    conn.close()

    if not patient:
        flash('Patient not found.', 'error')
        return redirect(url_for('list_patients'))

    return render_template('patient_detail.html', patient=patient, history=history)


# --- APPOINTMENT ROUTES ---
@app.route('/appointments')
@login_required
def list_appointments():
    conn = get_db_connection()
    appointments = conn.execute("""
        SELECT a.id, p.name AS patient_name, d.name AS doctor_name, a.appt_datetime, a.status
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.appt_datetime DESC
    """).fetchall()
    patients = conn.execute("SELECT id, name FROM patients").fetchall()
    doctors = conn.execute("SELECT id, name, specialization FROM doctors").fetchall()
    conn.close()
    return render_template('appointments.html', appointments=appointments, patients=patients, doctors=doctors)


@app.route('/appointments/book', methods=['POST'])
@login_required
def book_appointment():
    patient_id = request.form['patient_id']
    doctor_id = request.form['doctor_id']
    appt_datetime_str = request.form['appt_datetime']

    try:
        appt_datetime = datetime.fromisoformat(appt_datetime_str)
        appt_time = appt_datetime.time()
    except ValueError:
        flash('Invalid date/time format.', 'error')
        return redirect(url_for('list_appointments'))

    conn = get_db_connection()
    doctor = conn.execute("SELECT avail_start_time, avail_end_time FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    doc_start = datetime.strptime(doctor['avail_start_time'], '%H:%M:%S').time()
    doc_end = datetime.strptime(doctor['avail_end_time'], '%H:%M:%S').time()

    if not (doc_start <= appt_time <= doc_end):
        flash(f"Doctor available from {doc_start} to {doc_end}.", 'error')
        conn.close()
        return redirect(url_for('list_appointments'))

    existing_appt = conn.execute("""
        SELECT 1 FROM appointments
        WHERE doctor_id = ? AND status = 'Scheduled' AND appt_datetime = ?
    """, (doctor_id, appt_datetime)).fetchone()

    if existing_appt:
        flash('Doctor already has an appointment at this time.', 'error')
        conn.close()
        return redirect(url_for('list_appointments'))

    conn.execute("INSERT INTO appointments (patient_id, doctor_id, appt_datetime) VALUES (?, ?, ?)",
                 (patient_id, doctor_id, appt_datetime))
    conn.commit()
    conn.close()
    flash('Appointment booked successfully!', 'success')
    return redirect(url_for('list_appointments'))


@app.route('/appointment/update_status', methods=['POST'])
@login_required
def update_appointment_status():
    appt_id = request.form['appointment_id']
    new_status = request.form['status']

    conn = get_db_connection()
    conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appt_id))
    conn.commit()
    conn.close()

    flash(f"Appointment {appt_id} status updated to {new_status}.", 'success')
    return redirect(request.referrer or url_for('index'))


# --- DOCTOR ROUTES ---
@app.route('/doctors', methods=['GET', 'POST'])
@login_required
def doctors():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        avail_start = request.form['avail_start_time']
        avail_end = request.form['avail_end_time']

        if avail_start >= avail_end:
            flash('Available start time must be before end time.', 'error')
        else:
            try:
                conn.execute("""
                    INSERT INTO doctors (name, specialization, avail_start_time, avail_end_time) 
                    VALUES (?, ?, ?, ?)
                """, (name, specialization, avail_start, avail_end))
                conn.commit()
                flash(f"Dr. {name} added successfully!", 'success')
            except Exception as e:
                flash(f"Error adding doctor: {e}", 'error')

        conn.close()
        return redirect(url_for('doctors'))

    doctors = conn.execute("SELECT * FROM doctors ORDER BY name").fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors)


# --- BILLING ROUTES ---
@app.route('/billing')
@login_required
def list_billing():
    conn = get_db_connection()
    bills = conn.execute("""
        SELECT b.id, b.amount, b.status, b.issued_date,
               p.name AS patient_name, d.name AS doctor_name, a.appt_datetime
        FROM billing b
        JOIN appointments a ON b.appointment_id = a.id
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY b.issued_date DESC
    """).fetchall()
    conn.close()
    return render_template('billing.html', bills=bills)


@app.route('/billing/update_status', methods=['POST'])
@login_required
def update_billing_status():
    bill_id = request.form['bill_id']
    new_status = request.form['status']

    conn = get_db_connection()
    conn.execute("UPDATE billing SET status = ? WHERE id = ?", (new_status, bill_id))
    conn.commit()
    conn.close()

    flash(f"Bill {bill_id} status updated to {new_status}.", 'success')
    return redirect(url_for('list_billing'))


# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)
