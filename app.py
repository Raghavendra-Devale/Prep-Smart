from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite Configuration
def get_db_connection():
    try:
        conn = sqlite3.connect('placement_preparation.db', timeout=20)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise

# Home/Login Page
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('base/login.html')  # Serve the login page

    # Handle POST login logic here
    email = request.form.get('email').strip()
    password = request.form.get('password').strip()
    role = request.form.get('role')

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ? AND role = ?", (email, role))
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if not user:
            flash("No user found with that email and role!", "danger")
            return redirect(url_for('home'))

        if check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['role'] = user['role']

            if role == "student":
                return redirect(url_for('student_dashboard'))
            elif role == "company":
                return redirect(url_for('company_dashboard'))
            elif role == "admin":
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Incorrect password!", "danger")
            return redirect(url_for('home'))
    except Exception as err:
        flash(f"Database Error: {err}", "danger")
        return redirect(url_for('home'))


# Register User
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = None
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            phone = request.form.get('phone')  # Capture phone number

            # Print form data for debugging
            print("Form data:", request.form)

            db = get_db_connection()
            cursor = db.cursor()

            # First create user
            cursor.execute("""
                INSERT INTO users (email, password, role)
                VALUES (?, ?, ?)
            """, (email, generate_password_hash(password), role))
            
            user_id = cursor.lastrowid

            if role == 'student':
                # Include phone and graduation_year in the student insertion
                cursor.execute("""
                    INSERT INTO students (user_id, name, email, phone, department, graduation_year)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    name,
                    email,
                    phone,
                    request.form.get('department'),
                    request.form.get('graduation_year')
                ))
            
            elif role == 'company':
                company_name = request.form.get('company_name')
                cursor.execute("""
                    INSERT INTO companies (user_id, company_name, email, industry)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id,
                    company_name,
                    email,
                    request.form.get('industry')
                ))

            db.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            if db:
                db.rollback()
            print("Registration error:", str(e))
            flash('Registration failed: ' + str(e), 'error')
            return redirect(url_for('register'))

        finally:
            if db:
                db.close()

    return render_template('base/register.html')

# Logout
# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('home'))

# Unified Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('home'))
    if session['role'] == 'student':
        return redirect(url_for('student_dashboard'))
    elif session['role'] == 'company':
        return redirect(url_for('company_dashboard'))
    elif session['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('home'))

@app.route('/aptitude')
def aptitude():
    return render_template('apti/aptitude.html')

@app.route('/communication')
def communication():
    return render_template('communication/communication.html')

@app.route('/dsa')
def dsa():
    return render_template('dsa/dsa.html')

# Student Dashboard with Progress Tracking
@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('home'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT topic_id, COUNT(*) as completed 
        FROM student_progress 
        WHERE usn = ?
        GROUP BY topic_id
    """, (session['user_id'],))
    
    progress_data = cursor.fetchall()
    db.close()

    progress_summary = {row['topic_id']: row['completed'] for row in progress_data}
    
    return render_template('student/student_dashboard.html', username=session.get('email'), progress_summary=progress_summary)

# Company Dashboard
@app.route('/company_dashboard')
def company_dashboard():
    if 'role' not in session or session['role'] != 'company':
        return redirect(url_for('home'))
    return render_template('company_dashboard.html', username=session.get('email'), progress_summary={})

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html', username=session.get('email'), progress_summary={})

# Profile Page
@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('profile.html', username=session.get('email'))

@app.route('/user_profile')
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if not logged in

    print("User ID from session:", session['user_id'])  # Debugging

    user_id = session['user_id']
    
    conn = sqlite3.connect("placement_preparation.db")
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE user_id = ?", (user_id,))
    student = cursor.fetchone()
    
    conn.close()
    
    if not student:
        return "Student profile not found", 404  

    return render_template('student/user.html', student=student)


@app.route('/interview')
def interview():
    return render_template('interview/interview.html')

@app.route('/user')
def user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get all student details including graduation_year
        cursor.execute("""
            SELECT s.*, u.email 
            FROM students s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.user_id = ?
        """, (session['user_id'],))
        
        student = cursor.fetchone()
        if student:
            student_dict = {
                'name': student['name'],
                'email': student['email'],
                'phone': student['phone'],
                'department': student['department'],
                'graduation_year': student['graduation_year']  # Make sure this is included
            }
            return render_template('student/user.html', student=student_dict)
        
        return redirect(url_for('login'))
        
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return redirect(url_for('login'))
    finally:
        db.close()

@app.route('/aptitude_quantative')
def aptitude_quantative():
    return render_template('apti/aptitude_quantative.html')

@app.route('/aptitude_numbers')
def aptitude_numbers():
    return render_template('apti/aptitude_numbers.html')

@app.route('/communication_basics')
def communication_basics():
    return render_template('communication/communication_basics.html')

@app.route('/communication_intermediate')
def communication_intermediate():
    return render_template('communication/communication_intermediate.html')
@app.route('/communication_advanced')
def communication_advanced():
    return render_template('communication/communication_advanced.html')

@app.route('/dsa_basic_program')
def dsa_basic_program():
    return render_template('dsa/dsa_basic_program.html')

@app.route('/dsa_arrays_and_strings')
def dsa_arrays_and_strings():
    return render_template('dsa/dsa_arrays_and_strings.html')
@app.route('/dsa/linked-lists')
def dsa_linked_lists():
    return render_template('dsa/dsa_linked_lists.html')

@app.route('/dsa/stacks-and-queues')
def dsa_stacks_and_queues():
    return render_template('dsa/dsa_stacks_and_queues.html')
@app.route('/dsa/trees-and-graphs')
def dsa_trees_and_graphs():
    return render_template('dsa/dsa_trees_and_graphs.html')
@app.route('/dsa/trees-and-graphs')
def dsa_trees():
    return render_template('dsa/dsa_trees_and_graphs.html')
@app.route('/dsa/searching-and-sorting')
def dsa_searching_and_sorting():
    return render_template('dsa/dsa_searching_and_sorting.html')
@app.route('/dsa/dp-problems')
def dsa_dp_problems():
    return render_template('dsa/dsa_dp_problems.html')

@app.route('/dsa/recursion-and-backtracking')
def dsa_recursion_and_backtracking():
    return render_template('dsa/dsa_recursion_and_backtracking.html')
@app.route('/dsa/greedy-algorithms')
def dsa_greedy_algorithms():
    return render_template('dsa/dsa_greedy_algorithms.html')
@app.route('/dsa/bit-manipulation')
def dsa_bit_manipulation():
    return render_template('dsa/dsa_bit_manipulation.html')

@app.route('/notifications')
def notifications():
    return render_template('base/notifications.html')

@app.route('/logout')
def logout():
    session.clear()  # Remove all session data
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))  # Redirect to homepage after logout




# Update Student Progress
@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    data = request.get_json()
    usn = session['user_id']
    question_id = data.get('question_id')

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT topic_id FROM questions WHERE question_id = ?", (question_id,))
    topic = cursor.fetchone()
    
    if not topic:
        return jsonify({'success': False, 'message': 'Invalid question'})

    topic_id = topic['topic_id']

    cursor.execute("SELECT completed_questions FROM student_progress WHERE usn = ? AND topic_id = ?", (usn, topic_id))
    progress = cursor.fetchone()

    if progress:
        cursor.execute("UPDATE student_progress SET completed_questions = completed_questions + 1 WHERE usn = ? AND topic_id = ?", 
                       (usn, topic_id))
    else:
        cursor.execute("INSERT INTO student_progress (usn, topic_id, completed_questions, total_questions) VALUES (?, ?, 1, (SELECT COUNT(*) FROM questions WHERE topic_id = ?))",
                       (usn, topic_id, topic_id))

    db.commit()
    db.close()

    return jsonify({'success': True})


@app.route('/debug_db')
def debug_db():
    conn = sqlite3.connect("placement_preparation.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    conn.close()
    
    return {"tables": [table[0] for table in tables]}  # Check if 'students' exists


if __name__ == '__main__':
    app.run(debug=True)
