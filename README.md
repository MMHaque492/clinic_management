# Clinic Management System

A simple clinic management system built with Flask and SQLite.

## Features
- Staff login and authentication
- Add, list, and archive doctors
- Add and list patients (with medical history)
- Book and manage appointments
- Automatic billing generation when appointments are completed

## How to Run

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/clinic-management-system.git](https://github.com/YOUR_USERNAME/clinic-management-system.git)
    cd clinic-management-system
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install Flask flask-login
    ```

4.  **Initialize the database:**
    ```bash
    python database.py
    ```

5.  **Create your staff user:**
    ```bash
    python create_user.py
    ```

6.  **Run the application:**
    ```bash
    flask --app app run --debug
    ```

7.  Open `http://127.0.0.1:5000` in your browser.