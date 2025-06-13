from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from datetime import datetime
import os

# Flask app setup
app = Flask(__name__)
app.secret_key = '1a2d3e7r8t9d7tg4d5'  # Consider using os.urandom(24).hex() for production

# MySQL Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',      # Replace with your MySQL username
    'password': 'gopi@001',  # Replace with your MySQL password
    'database': 'college_bookings'   # Replace with your MySQL database name
}

# Database connection
def get_db():
    return mysql.connector.connect(**db_config)

# Initialize tables and sample data
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create users table with TEXT for password to handle long hashes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # Create resources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            resource_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            location VARCHAR(255),
            description TEXT
        )
    """)

    # Create bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            resource_id INT,    
            date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending',
            reason TEXT,
            FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
        )
    """)

    # Insert sample resources
    cursor.execute("""
        INSERT IGNORE INTO resources (name, category, location, description)
        VALUES 
        ('Seminar Hall A', 'Hall', 'Main Building', 'Seats 100'),
        ('Computer Lab 1', 'Lab', 'Tech Block', '40 PCs'),
        ('LCD Projector', 'Projector', 'Library', 'Portable')
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Home route
@app.route('/home')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/home1')
def home1():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/resources')
def resources():
    if 'username' not in session:
        flash('Please log in to view resources.', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM resources")
        resources = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template('resources.html', resources=resources)

# Book resource
@app.route('/bookresources', methods=['GET', 'POST'])
def bookresources():
    if 'username' not in session:
        flash('Please log in to book resources.', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            data = (
                request.form['student_name'],
                request.form['email'],
                int(request.form['resource_id']),

                request.form['date'],
                request.form['start_time'],
                request.form['end_time'],
                request.form['reason']
            )
            cursor.execute("""
                INSERT INTO bookings (student_name, email, resource_id, date, start_time, end_time, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, data)
            conn.commit()
            flash('Booking request submitted successfully!', 'success')
            return redirect(url_for('booking_status', email=request.form['email']))
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    else:
        try:
            cursor.execute("SELECT * FROM resources")
            resources = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template('bookresources.html', resources=resources)

# Booking status
@app.route('/booking_status')
def booking_status():
    if 'username' not in session:
        flash('Please log in to view booking status.', 'error')
        return redirect(url_for('login'))

    email = request.args.get('email')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        if email:
            cursor.execute("""
                SELECT b.*, r.name AS resource_name
                FROM bookings b
                JOIN resources r ON b.resource_id = r.resource_id
                WHERE b.email = %s AND b.status = 'Approved'
                ORDER BY b.date DESC
            """, (email,))
        else:
            cursor.execute("""
                SELECT b.*, r.name AS resource_name
                FROM bookings b
                JOIN resources r ON b.resource_id = r.resource_id
                WHERE b.status = 'Approved'
                ORDER BY b.date DESC
            """)
        bookings = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    
    return render_template('booking_status.html', bookings=bookings)

# Admin dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session:
        flash('Please log in as admin to access this page.', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            booking_id = request.form['booking_id']
            status = request.form['status']
            cursor.execute("UPDATE bookings SET status = %s WHERE booking_id = %s", (status, booking_id))
            conn.commit()
            flash('Booking status updated successfully!', 'success')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        return redirect(url_for('admin'))

    try:
        cursor.execute("""
            SELECT b.*, r.name AS resource_name
            FROM bookings b
            JOIN resources r ON b.resource_id = r.resource_id
            ORDER BY b.date DESC
        """)
        bookings = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    
    return render_template('administrator.html', bookings=bookings)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('login'))

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[0], password):
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'error')
                return redirect(url_for('login'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Basic input validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', 
                          (username, hashed_password))
            conn.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            if err.errno == 1062:  # Duplicate entry error
                flash('Username already exists. Please choose a different one.', 'error')
            else:
                flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))
@app.route('/adminlogin1', methods=['POST'])
def adminlogin1():
    username = request.form['username']
    password = request.form['password']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
      # Assuming admin login is for Faculty only

    select_query = "SELECT * FROM user WHERE username = %s AND password = %s"
    cursor.execute(select_query, (username, password))
    user = cursor.fetchone()

    if user:
        session['username'] = username 
        
        return redirect(url_for('admin'))
    else:
        flash('Invalid admin credentials. Please try again.', 'error')
        return redirect(url_for('adminlogin'))
@app.route('/adminlogin')
def adminlogin():   
    return render_template('adminlogin.html')

if __name__ == '__main__':
    init_db()  # Initialize database (run only once, comment out after first run)
    app.run(debug=True, host='0.0.0.0', port=8000)