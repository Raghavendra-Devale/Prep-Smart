import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import time
import os
import threading
import json
import uuid
import random
from werkzeug.utils import secure_filename
from analysis import analyze_interview_response

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register adapter and converter for datetime
def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

# SQLite Configuration
def get_db_connection():
    try:
        conn = sqlite3.connect('placement_preparation.db', timeout=20, detect_types=sqlite3.PARSE_DECLTYPES)
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
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role')

        print(f"Login attempt - Email: {email}, Role: {role}")  # Debug print

        try:
            db = get_db_connection()
            cursor = db.cursor()

            # First check if user exists with this email
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                if user['role'] != role:
                    flash(f"This account is registered as {user['role']}, not {role}", "error")
                    return redirect(url_for('login'))
                
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['email'] = user['email']
                    session['role'] = user['role']
                    
                    print(f"Login successful for {email} as {role}")  # Debug print
                    
                    if role == "admin":
                        return redirect(url_for('admin_dashboard'))
                    elif role == "student":
                        return redirect(url_for('student_dashboard'))
                    elif role == "company":
                        return redirect(url_for('company_dashboard'))
                else:
                    flash("Invalid password", "error")
            else:
                flash("No account found with this email", "error")
                
        except Exception as e:
            print(f"Login error: {e}")  # Debug print
            flash(f"Login error: {str(e)}", "error")
        finally:
            if 'db' in locals():
                db.close()

        return redirect(url_for('login'))

    return render_template('base/login.html')

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

            # First create user with name
            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (name, email, generate_password_hash(password), role))
            
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
@app.route('/logout')
def logout():
    session.clear()  # Remove all session data
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))  # Redirect to homepage after logout

def get_student_progress():
    if 'user_id' not in session:
        return {'success': False, 'message': 'Not logged in'}
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get student_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return {'success': False, 'message': 'Student not found'}
            
        student_id = result[0]
        print(f"Fetching progress for student_id: {student_id}")
        
        # Get all topics
        cursor.execute("SELECT topic_id, parent_topic, total_questions FROM progress_topics")
        topics = cursor.fetchall()
        
        if not topics:
            return {
                'success': True,
                'DSA': 0,
                'Communication': 0,
                'Aptitude': 0
            }
            
        # Initialize counters
        completed_by_category = {'DSA': 0, 'Communication': 0, 'Aptitude': 0}
        total_by_category = {'DSA': 0, 'Communication': 0, 'Aptitude': 0}
        
        # Count completed questions by category
        for topic in topics:
            topic_id, parent_topic, total_questions = topic
            total_by_category[parent_topic] += total_questions
            
            cursor.execute("""
                SELECT COUNT(*) FROM student_answers 
                WHERE student_id = ? AND topic_id = ? AND is_correct = 1
            """, (student_id, topic_id))
            
            completed = cursor.fetchone()[0]
            completed_by_category[parent_topic] += completed
            
        print(f"Completed by Category: {completed_by_category}")
        print(f"Total by Category: {total_by_category}")
        
        # Calculate progress percentages
        progress_data = {}
        for category in completed_by_category:
            if total_by_category[category] > 0:
                progress = (completed_by_category[category] / total_by_category[category]) * 100
                progress_data[category] = round(progress, 2)
            else:
                progress_data[category] = 0
                
        print(f"Calculated Progress Data: {progress_data}")
        
        return {
            'success': True,
            **progress_data
        }
        
    except Exception as e:
        traceback.print_exc()
        return {'success': False, 'message': str(e)}
    finally:
        if 'db' in locals():
            db.close()

@app.route('/get_progress', methods=['GET'])
def get_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    progress_data = get_student_progress()
    if not progress_data:
        return jsonify({'success': False, 'message': 'No progress found'})

    return jsonify({
        'success': True,
        'DSA': progress_data.get('DSA', 0),
        'Communication': progress_data.get('Communication', 0),
        'Aptitude': progress_data.get('Aptitude', 0)
    })

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))
    return render_template('admin/admin_dashboard.html', username=session.get('email'), progress_summary={})

@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        db = None
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']

            db = get_db_connection()
            cursor = db.cursor()

            # Insert the new admin user into the database
            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (name, email, generate_password_hash(password), 'admin'))

            db.commit()
            flash('Admin registration successful!', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            if db:
                db.rollback()
            flash('Registration failed: ' + str(e), 'error')
            return redirect(url_for('register_admin'))

        finally:
            if db:
                db.close()

    return render_template('register_admin.html')

@app.route('/update_progress', methods=['POST'])
def update_progress():
    print("🔎 Received POST request to /update_progress")

    if 'user_id' not in session:
        print("🚨 User not logged in")
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        print(f"✅ Request Data: {data}")

        if not data:
            print("🚨 Request data is empty")
            return jsonify({'success': False, 'message': 'Invalid request body'}), 400

        question_id = data.get('question_id')
        topic_id = data.get('topic_id')
        print(f"✅ Extracted Data - Question ID: {question_id}, Topic ID: {topic_id}")

        db = get_db_connection()
        cursor = db.cursor()

        # Get student ID from user_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            print("🚨 No student found for user_id")
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        student_id = result[0]
        print(f"✅ Found student ID: {student_id}")

        # Check if this question is already completed
        cursor.execute("""
            SELECT * FROM student_answers 
            WHERE student_id = ? AND question_id = ? AND topic_id = ?
        """, (student_id, question_id, topic_id))
        
        if cursor.fetchone():
            print("🚨 Question already completed!")
            return jsonify({'success': False, 'message': 'Question already completed!'})

        # Mark question as completed
        cursor.execute("""
            INSERT INTO student_answers 
            (student_id, question_id, topic_id, given_answer, is_correct) 
            VALUES (?, ?, ?, '', 1)
        """, (student_id, question_id, topic_id))

        # Get total questions for current topic
        cursor.execute("""
            SELECT total_questions FROM progress_topics 
            WHERE topic_id = ?
        """, (topic_id,))
        topic_total = cursor.fetchone()[0]

        # Get current completed questions count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM student_answers 
            WHERE student_id = ? AND topic_id = ?
        """, (student_id, topic_id))
        completed_questions = cursor.fetchone()[0]

        # Update progress for the specific topic
        cursor.execute("""
            INSERT OR REPLACE INTO student_progress 
            (student_id, topic_id, completed_questions, total_questions, is_completed) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id, 
            topic_id, 
            completed_questions, 
            topic_total, 
            1 if completed_questions >= topic_total else 0
        ))

        # Get parent topic for the current topic
        cursor.execute("SELECT parent_topic FROM progress_topics WHERE topic_id = ?", (topic_id,))
        parent_topic = cursor.fetchone()[0]

        # For DSA topics only, update the dsa_overall_progress table if it exists
        if parent_topic == 'DSA':
            try:
                # Calculate DSA progress
                cursor.execute("""
                    SELECT SUM(total_questions) 
                    FROM progress_topics 
                    WHERE parent_topic = 'DSA'
                """)
                total_dsa_questions = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM student_answers sa
                    JOIN progress_topics pt ON sa.topic_id = pt.topic_id
                    WHERE sa.student_id = ? AND pt.parent_topic = 'DSA'
                """, (student_id,))
                completed_dsa_questions = cursor.fetchone()[0] or 0

                # Update DSA progress if table exists
                cursor.execute("""
                    INSERT OR REPLACE INTO dsa_overall_progress 
                    (student_id, completed_questions, total_questions, is_completed, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    student_id, 
                    completed_dsa_questions, 
                    total_dsa_questions,
                    1 if completed_dsa_questions >= total_dsa_questions else 0
                ))
            except sqlite3.OperationalError as e:
                # If the dsa_overall_progress table doesn't exist, just log and continue
                print(f"Note: DSA progress table not updated - {e}")
                pass

        db.commit()
        print("✅ Successfully updated progress!")

        # Return the updated progress without accessing aptitude_overall_progress
        return jsonify({
            'success': True,
            'topic_progress': completed_questions,
            'total_topic_questions': topic_total,
            'updated_category': parent_topic
        })

    except Exception as e:
        print(f"🚨 Error updating progress: {e}")
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

# Update Student Progress
@app.route('/student_progress', methods=['GET'])
def student_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        topic_id = request.args.get('topic_id')
        if not topic_id:
            return jsonify({'success': False, 'message': 'Topic ID is required'}), 400

        db = get_db_connection()
        cursor = db.cursor()

        # Get student ID from user_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Student not found'}), 404

        student_id = result[0]

        # Get topic-specific progress
        cursor.execute("""
            SELECT COUNT(*) as completed_count
            FROM student_answers
            WHERE student_id = ? AND topic_id = ?
        """, (student_id, topic_id))
        topic_result = cursor.fetchone()
        topic_completed = topic_result[0] if topic_result else 0

        # Get overall DSA progress
        cursor.execute("""
            SELECT completed_questions, total_questions
            FROM dsa_overall_progress
            WHERE student_id = ?
        """, (student_id,))
        dsa_progress = cursor.fetchone()

        return jsonify({
            'success': True,
            'completed_questions': topic_completed,
            'dsa_completed': dsa_progress[0] if dsa_progress else 0,
            'dsa_total': dsa_progress[1] if dsa_progress else 0
        })

    except Exception as e:
        print(f"Error fetching progress: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

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

# Student Dashboard with Progress Tracking
@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        print("🚨 User not logged in or incorrect role")
        return redirect(url_for('home'))
    
    db = get_db_connection()
    cursor = db.cursor()
    
    # ✅ Get student_id instead of usn
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    result = cursor.fetchone()
    if not result:
        print("🚨 Student not found")
        return jsonify({'success': False, 'message': 'Student not found'}), 404

    student_id = result[0]
    print(f"✅ Found student ID: {student_id}")  # Corrected student ID print statement

    # ✅ Replace usn with student_id
    cursor.execute("""
        SELECT topic_id, COUNT(*) as completed 
        FROM student_progress 
        WHERE student_id = ?
        GROUP BY topic_id
    """, (student_id,))
    
    progress_data = cursor.fetchall()
    db.close()

    print(f"✅ Progress Data: {progress_data}")

    progress_summary = {row['topic_id']: row['completed'] for row in progress_data}
    print(f"✅ Progress Summary: {progress_summary}")
    
    # ✅ Return the template directly to debug if it's loading
    return render_template(
        'student/student_dashboard.html',
        username=session.get('email'),
        progress_summary=progress_summary
    )

# Company Dashboard
@app.route('/company_dashboard')
def company_dashboard():
    if 'role' not in session or session['role'] != 'company':
        return redirect(url_for('home'))
    return render_template('company_dashboard.html', username=session.get('email'), progress_summary={})

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

def get_topic_id(topic_name):
    topic_map = {
        'basic_programming': 1,
        'dsa': 2,
        'aptitude': 3,
        'communication': 4
    }
    return topic_map.get(topic_name, 1)

@app.route('/debug_db')
def debug_db():
    conn = sqlite3.connect("placement_preparation.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    conn.close()
    
    return {"tables": [table[0] for table in tables]}  # Check if 'students' exists

@app.route('/update_aptitude_progress', methods=['POST'])
def update_aptitude_progress():
    if 'user_id' not in session:
        print("User not logged in")
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    db = None
    try:
        data = request.get_json()
        print("Received data:", data)
        
        problem_id = data.get('problem_id')
        topic_id = data.get('topic_id')
        is_completed = data.get('status', True)
        
        # Get student ID from user_id
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        student_id = result[0]

        # Insert or update the problem completion status
        cursor.execute("""
            INSERT OR REPLACE INTO aptitude_progress 
            (student_id, problem_id, is_completed) 
            VALUES (?, ?, ?)
        """, (student_id, problem_id, is_completed))
        
        # Count completed problems for this topic
        cursor.execute("""
            SELECT COUNT(*) FROM aptitude_progress 
            WHERE student_id = ? AND problem_id LIKE ? AND is_completed = 1
        """, (student_id, problem_id[0] + '%'))
        completed_count = cursor.fetchone()[0]
        
        # Get total problems for this topic
        cursor.execute("SELECT total_questions FROM progress_topics WHERE topic_id = ?", (topic_id,))
        total_questions = cursor.fetchone()[0]
        
        # Update student progress for this topic
        cursor.execute("""
            INSERT OR REPLACE INTO student_progress 
            (student_id, topic_id, completed_questions, total_questions, is_completed)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            topic_id,
            completed_count,
            total_questions,
            1 if completed_count >= total_questions else 0
        ))

        db.commit()
        print("Successfully updated progress")
        return jsonify({
            'success': True,
            'completed_count': completed_count,
            'total_questions': total_questions
        })

    except Exception as e:
        print("Error in update_aptitude_progress:")
        print(traceback.format_exc())
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if db:
            db.close()


@app.route('/get_aptitude_progress')
def get_aptitude_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get student ID from user_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        student_id = result[0]
        
        cursor.execute("""
            SELECT problem_id, is_completed 
            FROM aptitude_progress 
            WHERE student_id = ?
        """, (student_id,))
        
        progress = {row[0]: bool(row[1]) for row in cursor.fetchall()}
        
        # Get overall aptitude progress
        cursor.execute("""
            SELECT SUM(completed_questions) as completed, SUM(total_questions) as total
            FROM student_progress sp
            JOIN progress_topics pt ON sp.topic_id = pt.topic_id
            WHERE sp.student_id = ? AND pt.parent_topic = 'Aptitude'
        """, (student_id,))
        
        overall = cursor.fetchone()
        overall_progress = {
            'completed': overall[0] or 0,
            'total': overall[1] or 0
        }
        
        return jsonify({
            'success': True,
            'progress': progress,
            'overall_progress': overall_progress
        })
        
    except Exception as e:
        print(f"Error fetching progress: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

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

@app.route('/aptitude')
def aptitude():
    return render_template('apti/aptitude.html')

@app.route('/aptitude_base')
def aptitude_base():
    return render_template('aptitude_base.html')

@app.route('/communication')
def communication():
    return render_template('communication/communication.html')

@app.route('/dsa')
def dsa():
    return render_template('dsa/dsa.html')

@app.route('/interview')
def interview():
    return render_template('interview/interview.html')

@app.route('/aptitude_quantative')
def aptitude_quantative():
    return render_template('apti/quantative/aptitude_quantative.html')

@app.route('/aptitude_numbers')
def aptitude_numbers():
    return render_template('apti/aptitude_numbers.html')

@app.route('/aptitude/time-and-work')
def time_and_work():
    return render_template('apti/quantative/time_and_work.html')

@app.route('/aptitude/speed-distance')
def speed_distance():
    return render_template('apti/quantative/speed_distance.html')

@app.route('/aptitude/percentages')
def percentages():
    return render_template('apti/percentages.html')

@app.route('/aptitude/profit-and-loss')
def profit_and_loss():
    return render_template('apti/quantative/profit_and_loss.html')

@app.route('/aptitude/simple_and_compound_intrest')
def simple_interest():
    return render_template('apti/quantative/simple_and_compound_interest.html')

# @app.route('/aptitude/compound-interest')
# def compound_interest():
#     return render_template('apti/compound_interest.html')

@app.route('/aptitude/ratio-and-proportion')
def ratio_and_proportion():
    return render_template('apti/quantative/ratio_and_proportion.html')

@app.route('/aptitude/averages')
def averages():
    return render_template('apti/averages.html')

@app.route('/aptitude/mixtures-and-alligations')
def mixtures_and_alligations():
    return render_template('apti/mixtures_and_alligations.html')

@app.route('/aptitude/probability')
def probability():
    return render_template('apti/quantative/probability.html')

@app.route('/logical-reasoning')
def logical_reasoning():
    return render_template('apti/logical_reasoning/logical_reasoning.html')

@app.route('/blood_relations')
def blood_relations():
    # Your code to render the blood relations template
    return render_template('apti/logical_reasoning/blood_relations.html')

@app.route('/syllogism')
def syllogism():
    return render_template('apti/logical_reasoning/syllogism.html')

@app.route('/directions')
def directions():
    return render_template('apti/logical_reasoning/directions.html')

@app.route('/puzzles')
def puzzles():
    return render_template('apti/logical_reasoning/puzzles.html')

@app.route('/sentence_completion')
def sentence_completion():
    return render_template('apti/verbal/sentence_completion.html')

@app.route('/synonyms_and_atonyms')
def synonyms_and_atonyms():
    return render_template('apti/verbal/synonyms_and_atonyms.html')

@app.route('/reading_and_comprehension')
def reading_and_comprehension():
    return render_template('apti/verbal/reading_and_comprehension.html')

@app.route('/parajumbles')
def parajumbles():
    return render_template('apti/verbal/parajumbles.html')

@app.route('/bar_graphs')
def bar_graphs():
    return render_template('apti/data_interpretation/bar_graphs.html')

@app.route('/piecharts')
def piecharts():
    return render_template('apti/data_interpretation/piecharts.html')

@app.route('/linegraphs')
def linegraphs():
    return render_template('apti/data_interpretation/linegraphs.html')

@app.route('/tabulation')
def tabulation():
    return render_template('apti/data_interpretation/tabulation.html')

@app.route('/verbal-reasoning')
def verbal_reasoning():
    return render_template('apti/verbal/verbal_reasoning.html')

@app.route('/aptitude/problems-on-trains')
def problems_on_trains():
    return render_template('apti/quantative/problems_on_trains.html')

@app.route('/aptitude/time_and_distance')
def time_and_distance():
    return render_template('apti/quantative/time_and_distance.html')

@app.route('/data-interpretation')
def data_interpretation():
    return render_template('apti/data_interpretation/data_interpretation.html')

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
    return render_template('dsa/dsa_Greedy_Algrothms.html')

@app.route('/dsa/bit-manipulation')
def dsa_bit_manipulation():
    return render_template('dsa/dsa_BitManipulation.html')

@app.route('/notifications')
def notifications():
    return render_template('base/notifications.html')

@app.route('/technical_interview')
def technical_interview():
    return render_template('interview/technical_interview.html')

@app.route('/hr_interview')
def hr_interview():
    return render_template('interview/hr_interview.html')

@app.route('/mark_complete', methods=['POST'])
def mark_complete():
    if 'user_id' not in session:
        print("User not logged in")
        return jsonify({"status": "error", "message": "Not logged in"}), 401
        
    data = request.json
    topic_id = data.get('topic_id')
    problem_id = data.get('problem_id')
    
    if not all([topic_id, problem_id]):
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Get student ID from user_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            print("🚨 No student found for user_id")
            return jsonify({'status': 'error', 'message': 'Student not found'}), 404

        student_id = result[0]
        print(f"✅ Found student ID: {student_id} for problem {problem_id} in topic {topic_id}")

        # Convert problem_id to string if it's not already
        problem_id_str = str(problem_id)
        
        # Create question_id from problem_id
        if ('-' in problem_id_str):
            try:
                question_id = int(problem_id_str.split('-')[-1])
            except (ValueError, IndexError):
                question_id = 1
        else:
            # If no hyphen, just use the number as is or default to 1
            try:
                question_id = int(problem_id_str)
            except ValueError:
                question_id = 1
        
        print(f"✅ Converted problem ID '{problem_id}' to question ID '{question_id}'")
        
        # First check if this answer is already recorded
        cursor.execute("""
            SELECT * FROM student_answers 
            WHERE student_id = ? AND topic_id = ? AND question_id = ?
        """, (student_id, topic_id, question_id))
        
        if not cursor.fetchone():
            # Insert into student_answers table
            cursor.execute("""
                INSERT INTO student_answers 
                (student_id, question_id, topic_id, given_answer, is_correct) 
                VALUES (?, ?, ?, 'completed', 1)
            """, (student_id, question_id, topic_id))
            
            print(f"✅ Inserted into student_answers: student_id={student_id}, question_id={question_id}, topic_id={topic_id}")
        
        # Get parent topic for the current topic
        cursor.execute("SELECT parent_topic FROM progress_topics WHERE topic_id = ?", (topic_id,))
        topic_result = cursor.fetchone()
        parent_topic = topic_result[0] if topic_result else 'Unknown'
        
        # Update specific progress based on the parent topic
        if parent_topic == 'Aptitude':
            # Check if aptitude_progress table has a student_id column
            try:
                cursor.execute("PRAGMA table_info(aptitude_progress)")
                columns = [row['name'] for row in cursor.fetchall()]
                
                if 'student_id' in columns:
                    # Table has student_id column, use it
                    cursor.execute("""
                        INSERT OR REPLACE INTO aptitude_progress 
                        (student_id, problem_id, is_completed) 
                        VALUES (?, ?, 1)
                    """, (student_id, problem_id))
                    print(f"✅ Inserted into aptitude_progress with student_id: {student_id}, problem_id={problem_id}")
                elif 'user_id' in columns:
                    # Table has user_id column instead, use that
                    cursor.execute("""
                        INSERT OR REPLACE INTO aptitude_progress 
                        (user_id, problem_id, is_completed) 
                        VALUES (?, ?, 1)
                    """, (session['user_id'], problem_id))
                    print(f"✅ Inserted into aptitude_progress with user_id: {session['user_id']}, problem_id={problem_id}")
                else:
                    print("⚠️ aptitude_progress table has neither student_id nor user_id column, skipping this update")
            except Exception as e:
                print(f"⚠️ Error updating aptitude_progress: {e}")
                # Continue with the function even if this part fails
        
        elif parent_topic == 'Communication':
            # Check if communication_progress table exists and has appropriate columns
            try:
                # First try to create the table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS communication_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        user_id INTEGER,
                        problem_id TEXT NOT NULL,
                        is_completed INTEGER DEFAULT 0,
                        UNIQUE(problem_id, student_id)
                    )
                """)
                
                cursor.execute("PRAGMA table_info(communication_progress)")
                columns = [row['name'] for row in cursor.fetchall()]
                
                if 'student_id' in columns:
                    # Table has student_id column, use it
                    cursor.execute("""
                        INSERT OR REPLACE INTO communication_progress 
                        (student_id, problem_id, is_completed) 
                        VALUES (?, ?, 1)
                    """, (student_id, problem_id))
                    print(f"✅ Inserted into communication_progress with student_id: {student_id}, problem_id={problem_id}")
                elif 'user_id' in columns:
                    # Table has user_id column instead, use that
                    cursor.execute("""
                        INSERT OR REPLACE INTO communication_progress 
                        (user_id, problem_id, is_completed) 
                        VALUES (?, ?, 1)
                    """, (session['user_id'], problem_id))
                    print(f"✅ Inserted into communication_progress with user_id: {session['user_id']}, problem_id={problem_id}")
                else:
                    print("⚠️ communication_progress table has neither student_id nor user_id column, skipping this update")
            except Exception as e:
                print(f"⚠️ Error updating communication_progress: {e}")
                # Continue with the function even if this part fails
        
        # Get total questions for current topic
        cursor.execute("SELECT total_questions FROM progress_topics WHERE topic_id = ?", (topic_id,))
        topic_result = cursor.fetchone()
        topic_total = topic_result[0] if topic_result else 10
        
        # Get count of completed questions for this topic
        cursor.execute("""
            SELECT COUNT(*) FROM student_answers
            WHERE student_id = ? AND topic_id = ? AND is_correct = 1
        """, (student_id, topic_id))
        completed_questions = cursor.fetchone()[0]
        
        print(f"✅ Topic {topic_id}: {completed_questions} of {topic_total} completed")
        
        # Update student_progress table
        cursor.execute("""
            INSERT OR REPLACE INTO student_progress 
            (student_id, topic_id, completed_questions, total_questions, is_completed) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id, 
            topic_id, 
            completed_questions, 
            topic_total, 
            1 if completed_questions >= topic_total else 0
        ))
        
        # Update category-specific overall progress
        if parent_topic == 'Aptitude':
            try:
                # Calculate Aptitude progress
                cursor.execute("""
                    SELECT SUM(total_questions) 
                    FROM progress_topics 
                    WHERE parent_topic = 'Aptitude'
                """)
                total_aptitude_questions = cursor.fetchone()[0] or 10

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM student_answers sa
                    JOIN progress_topics pt ON sa.topic_id = pt.topic_id
                    WHERE sa.student_id = ? AND pt.parent_topic = 'Aptitude'
                """, (student_id,))
                completed_aptitude_questions = cursor.fetchone()[0] or 0

                # Update Aptitude progress
                cursor.execute("""
                    INSERT OR REPLACE INTO aptitude_overall_progress 
                    (student_id, completed_questions, total_questions, is_completed, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    student_id, 
                    completed_aptitude_questions, 
                    total_aptitude_questions,
                    1 if completed_aptitude_questions >= total_aptitude_questions else 0
                ))
            except Exception as e:
                print(f"⚠️ Note: Could not update aptitude overall progress - {e}")
        
        elif parent_topic == 'Communication':
            try:
                # Calculate Communication progress
                cursor.execute("""
                    SELECT SUM(total_questions) 
                    FROM progress_topics 
                    WHERE parent_topic = 'Communication'
                """)
                total_comm_questions = cursor.fetchone()[0] or 10

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM student_answers sa
                    JOIN progress_topics pt ON sa.topic_id = pt.topic_id
                    WHERE sa.student_id = ? AND pt.parent_topic = 'Communication'
                """, (student_id,))
                completed_comm_questions = cursor.fetchone()[0] or 0

                # Update Communication progress
                cursor.execute("""
                    INSERT OR REPLACE INTO communication_overall_progress 
                    (student_id, completed_questions, total_questions, is_completed, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    student_id, 
                    completed_comm_questions, 
                    total_comm_questions,
                    1 if completed_comm_questions >= total_comm_questions else 0
                ))
            except Exception as e:
                print(f"⚠️ Note: Could not update communication overall progress - {e}")
        
        elif parent_topic == 'DSA':
            try:
                # Calculate DSA progress
                cursor.execute("""
                    SELECT SUM(total_questions) 
                    FROM progress_topics 
                    WHERE parent_topic = 'DSA'
                """)
                total_dsa_questions = cursor.fetchone()[0] or 10

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM student_answers sa
                    JOIN progress_topics pt ON sa.topic_id = pt.topic_id
                    WHERE sa.student_id = ? AND pt.parent_topic = 'DSA'
                """, (student_id,))
                completed_dsa_questions = cursor.fetchone()[0] or 0

                # Update DSA progress
                cursor.execute("""
                    INSERT OR REPLACE INTO dsa_overall_progress 
                    (student_id, completed_questions, total_questions, is_completed, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    student_id, 
                    completed_dsa_questions, 
                    total_dsa_questions,
                    1 if completed_dsa_questions >= total_dsa_questions else 0
                ))
            except Exception as e:
                print(f"⚠️ Note: Could not update DSA overall progress - {e}")
        
        db.commit()
        print("✅ Successfully updated progress!")
        
        # Return updated progress information
        return jsonify({
            "status": "success",
            "completed": completed_questions,
            "total": topic_total,
            "percent": round((completed_questions / topic_total) * 100) if topic_total > 0 else 0,
            "topic_id": topic_id,
            "parent_topic": parent_topic
        })
        
    except Exception as e:
        traceback.print_exc()
        print(f"Error in mark_complete: {e}")
        if 'db' in locals():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/debug_progress')
def debug_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Student not found'})
        
        student_id = result[0]
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get topic information
        cursor.execute("SELECT * FROM progress_topics")
        topics = [dict(row) for row in cursor.fetchall()]
        
        # Get student answers
        cursor.execute("""
            SELECT sa.*, pt.parent_topic, pt.topic_name
            FROM student_answers sa
            JOIN progress_topics pt ON sa.topic_id = pt.topic_id
            WHERE sa.student_id = ?
        """, (student_id,))
        answers = [dict(row) for row in cursor.fetchall()]
        
        # Get aptitude progress
        cursor.execute("SELECT * FROM aptitude_progress WHERE student_id = ?", (student_id,))
        aptitude_progress = [dict(row) for row in cursor.fetchall()]
        
        # Get student_progress
        cursor.execute("""
            SELECT sp.*, pt.parent_topic, pt.topic_name
            FROM student_progress sp
            JOIN progress_topics pt ON sp.topic_id = pt.topic_id
            WHERE sp.student_id = ?
        """, (student_id,))
        progress = [dict(row) for row in cursor.fetchall()]
        
        # Return all the collected data
        return jsonify({
            'success': True,
            'student_id': student_id,
            'tables': tables,
            'topics': topics,
            'answers': answers,
            'aptitude_progress': aptitude_progress,
            'student_progress': progress,
            'progress_summary': get_student_progress()
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)})
    finally:
        if 'db' in locals():
            db.close()

@app.route('/init_mock_progress')
def init_mock_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get student ID
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
            
        student_id = result[0]
        
        # Check if progress_topics exists and has aptitude topics
        cursor.execute("SELECT COUNT(*) FROM progress_topics WHERE parent_topic = 'Aptitude'")
        aptitude_topic_count = cursor.fetchone()[0]
        
        if aptitude_topic_count == 0:
            # Create some aptitude topics if none exist
            cursor.execute("""
                INSERT OR IGNORE INTO progress_topics 
                (topic_id, topic_name, parent_topic, description, total_questions) 
                VALUES 
                (101, 'Time and Work', 'Aptitude', 'Problems related to time and work', 10),
                (102, 'Percentages', 'Aptitude', 'Percentage calculations', 10),
                (103, 'Probability', 'Aptitude', 'Probability problems', 10)
            """)
            
        # Check if communication topics exist
        cursor.execute("SELECT COUNT(*) FROM progress_topics WHERE parent_topic = 'Communication'")
        comm_topic_count = cursor.fetchone()[0]
        
        if comm_topic_count == 0:
            # Create some communication topics if none exist
            cursor.execute("""
                INSERT OR IGNORE INTO progress_topics 
                (topic_id, topic_name, parent_topic, description, total_questions) 
                VALUES 
                (201, 'Verbal Skills', 'Communication', 'Verbal communication', 10),
                (202, 'Writing Skills', 'Communication', 'Written communication', 10),
                (203, 'Presentation', 'Communication', 'Presentation skills', 10)
            """)
        
        # Add some mock student answers for Aptitude topics
        cursor.execute("""
            INSERT OR IGNORE INTO student_answers 
            (student_id, question_id, topic_id, given_answer, is_correct) 
            VALUES 
            (?, 1, 101, 'answer1', 1),
            (?, 2, 101, 'answer2', 1),
            (?, 3, 101, 'answer3', 1),
            (?, 1, 102, 'answer1', 1),
            (?, 2, 102, 'answer2', 1)
        """, (student_id, student_id, student_id, student_id, student_id))
        
        # Add some mock student answers for Communication topics
        cursor.execute("""
            INSERT OR IGNORE INTO student_answers 
            (student_id, question_id, topic_id, given_answer, is_correct) 
            VALUES 
            (?, 1, 201, 'answer1', 1),
            (?, 2, 201, 'answer2', 1),
            (?, 3, 201, 'answer3', 1),
            (?, 1, 202, 'answer1', 1)
        """, (student_id, student_id, student_id, student_id))
        
        db.commit()
        
        # Return the current progress after initialization
        return jsonify({
            'success': True,
            'message': 'Mock data initialized',
            'progress': get_student_progress()
        })
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/fix_db_schema')
def fix_db_schema():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check and create progress_topics table if needed
        if 'progress_topics' not in tables:
            cursor.execute("""
                CREATE TABLE progress_topics (
                    topic_id INTEGER PRIMARY KEY,
                    topic_name TEXT NOT NULL,
                    parent_topic TEXT NOT NULL,
                    description TEXT,
                    total_questions INTEGER DEFAULT 10
                )
            """)
            
        # Check and create student_answers table if needed
        if 'student_answers' not in tables:
            cursor.execute("""
                CREATE TABLE student_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    given_answer TEXT,
                    is_correct INTEGER DEFAULT 0,
                    UNIQUE(student_id, question_id, topic_id)
                )
            """)
            
        # Check and create student_progress table if needed
        if 'student_progress' not in tables:
            cursor.execute("""
                CREATE TABLE student_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    completed_questions INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 10,
                    is_completed INTEGER DEFAULT 0,
                    UNIQUE(student_id, topic_id)
                )
            """)
            
        # Check and create aptitude_progress table if needed
        if 'aptitude_progress' not in tables:
            cursor.execute("""
                CREATE TABLE aptitude_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    problem_id TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    UNIQUE(student_id, problem_id)
                )
            """)
        else:
            # Fix aptitude_progress schema if it has a user_id column instead of student_id
            cursor.execute("PRAGMA table_info(aptitude_progress)")
            columns = [row['name'] for row in cursor.fetchall()]
            
            if 'user_id' in columns and 'student_id' not in columns:
                # Create a new table with correct schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS aptitude_progress_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        problem_id TEXT NOT NULL,
                        is_completed INTEGER DEFAULT 0,
                        UNIQUE(student_id, problem_id)
                    )
                """)
                
                # Get student_id for each user_id and copy data
                cursor.execute("SELECT * FROM aptitude_progress")
                rows = cursor.fetchall()
                
                for row in rows:
                    cursor.execute("SELECT id FROM students WHERE user_id = ?", (row[1],))  # user_id is at index 1
                    student = cursor.fetchone()
                    if student:
                        cursor.execute("""
                            INSERT OR IGNORE INTO aptitude_progress_new 
                            (student_id, problem_id, is_completed) 
                            VALUES (?, ?, ?)
                        """, (student[0], row[2], row[3]))  # problem_id at index 2, is_completed at index 3
                
                # Drop old table and rename new one
                cursor.execute("DROP TABLE aptitude_progress")
                cursor.execute("ALTER TABLE aptitude_progress_new RENAME TO aptitude_progress")
        
        # Add default topics if empty
        cursor.execute("SELECT COUNT(*) FROM progress_topics")
        topic_count = cursor.fetchone()[0]
        
        if (topic_count == 0):
            # Add some default topics for each category
            cursor.execute("""
                INSERT INTO progress_topics (topic_id, topic_name, parent_topic, description, total_questions)
                VALUES
                (1, 'Basic Programming', 'DSA', 'Basic programming concepts', 15),
                (2, 'Arrays and Strings', 'DSA', 'Array and string manipulation', 12),
                (3, 'Linked Lists', 'DSA', 'Linked list operations', 10),
                (4, 'Stacks and Queues', 'DSA', 'Stack and queue implementations', 8),
                
                (101, 'Reading Comprehension', 'Communication', 'Reading and understanding passages', 50),
                (102, 'Parajumbles', 'Communication', 'Sentence rearrangement', 50),
                
                (201, 'Bar Graphs', 'Aptitude', 'Bar graph interpretation', 50),
                (202, 'Pie Charts', 'Aptitude', 'Pie chart analysis', 50),
                (203, 'Line Graphs', 'Aptitude', 'Line graph interpretation', 50),
                (204, 'Tabulation', 'Aptitude', 'Data table analysis', 50)
            """)
        
        # Insert mock data for testing
        student_id = None
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if result:
            student_id = result[0]
            
            # Add some mock answers if none exist
            cursor.execute("SELECT COUNT(*) FROM student_answers WHERE student_id = ?", (student_id,))
            if cursor.fetchone()[0] == 0:
                # Insert mock answers for each category
                cursor.execute("""
                    INSERT OR IGNORE INTO student_answers (student_id, question_id, topic_id, given_answer, is_correct)
                    VALUES
                    (?, 1, 1, 'answer1', 1),
                    (?, 2, 1, 'answer2', 1),
                    (?, 1, 2, 'answer1', 1),
                    
                    (?, 1, 101, 'answer1', 1),
                    (?, 2, 101, 'answer2', 1),
                    (?, 1, 102, 'answer1', 1),
                    
                    (?, 1, 201, 'answer1', 1),
                    (?, 2, 201, 'answer2', 1),
                    (?, 1, 202, 'answer1', 1)
                """, (student_id,)*9)
        
        db.commit()
        
        # Return diagnostic information
        return jsonify({
            'success': True,
            'message': 'Database schema verified and fixed',
            'tables': tables,
            'progress_data': get_student_progress()
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/fix_missing_tables')
def fix_missing_tables():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create the aptitude_overall_progress table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aptitude_overall_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                UNIQUE(student_id)
            )
        """)
        
        # Create the dsa_overall_progress table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dsa_overall_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                UNIQUE(student_id)
            )
        """)
        
        # Create the communication_overall_progress table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_overall_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                UNIQUE(student_id)
            )
        """)
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Missing tables created successfully'
        })
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/fix_aptitude_schema')
def fix_aptitude_schema():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if aptitude_progress table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aptitude_progress'")
        if not cursor.fetchone():
            # Create the table with proper schema
            cursor.execute("""
                CREATE TABLE aptitude_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER, 
                    student_id INTEGER,
                    problem_id TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    UNIQUE(problem_id, student_id)
                )
            """)
            print("Created aptitude_progress table with both columns")
        else:
            # Check current schema
            cursor.execute("PRAGMA table_info(aptitude_progress)")
            columns = {row['name']: row for row in cursor.fetchall()}
            
            # Add missing columns if needed
            if 'student_id' not in columns:
                cursor.execute("ALTER TABLE aptitude_progress ADD COLUMN student_id INTEGER")
                print("Added student_id column to aptitude_progress")
                
                # If user_id exists, populate student_id based on it
                if 'user_id' in columns:
                    cursor.execute("""
                        UPDATE aptitude_progress 
                        SET student_id = (
                            SELECT id FROM students WHERE user_id = aptitude_progress.user_id
                        )
                        WHERE user_id IS NOT NULL
                    """)
                    print("Populated student_id values from user_id")
            
            if 'user_id' not in columns:
                cursor.execute("ALTER TABLE aptitude_progress ADD COLUMN user_id INTEGER")
                print("Added user_id column to aptitude_progress")
        
        db.commit()
        
        # Return the fixed schema info
        cursor.execute("PRAGMA table_info(aptitude_progress)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'message': 'Aptitude progress table schema fixed',
            'columns': columns
        })
        
    except Exception as e:
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/fix_communication_schema')
def fix_communication_schema():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create the communication_overall_progress table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_overall_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                UNIQUE(student_id)
            )
        """)
        
        # Also ensure we have a way to track individual communication exercises
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                user_id INTEGER,
                problem_id TEXT NOT NULL,
                is_completed INTEGER DEFAULT 0,
                UNIQUE(problem_id, student_id)
            )
        """)
        
        # Check current schema of communication_progress
        try:
            cursor.execute("PRAGMA table_info(communication_progress)")
            columns = {row['name']: row for row in cursor.fetchall()}
            
            # Add missing columns if needed
            if 'student_id' not in columns:
                cursor.execute("ALTER TABLE communication_progress ADD COLUMN student_id INTEGER")
                print("Added student_id column to communication_progress")
                
                # If user_id exists, populate student_id based on it
                if 'user_id' in columns:
                    cursor.execute("""
                        UPDATE communication_progress 
                        SET student_id = (
                            SELECT id FROM students WHERE user_id = communication_progress.user_id
                        )
                        WHERE user_id IS NOT NULL
                    """)
                    print("Populated student_id values from user_id")
            
            if 'user_id' not in columns:
                cursor.execute("ALTER TABLE communication_progress ADD COLUMN user_id INTEGER")
                print("Added user_id column to communication_progress")
        except Exception as e:
            print(f"Error checking communication_progress schema: {e}")
            # Table doesn't exist yet, will be created earlier
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Communication progress tables created/fixed successfully'
        })
        
    except Exception as e:
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/get_communication_progress')
def get_communication_progress():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get student ID from user_id
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        student_id = result[0]
        
        # Create the communication_progress table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                user_id INTEGER,
                problem_id TEXT NOT NULL,
                is_completed INTEGER DEFAULT 0,
                UNIQUE(problem_id, student_id)
            )
        """)
        
        # Get individual communication exercises progress
        cursor.execute("""
            SELECT problem_id, is_completed 
            FROM communication_progress 
            WHERE student_id = ?
        """, (student_id,))
        
        progress = {row[0]: bool(row[1]) for row in cursor.fetchall()}
        
        # Get overall communication progress
        cursor.execute("""
            SELECT SUM(completed_questions) as completed, SUM(total_questions) as total
            FROM student_progress sp
            JOIN progress_topics pt ON sp.topic_id = pt.topic_id
            WHERE sp.student_id = ? AND pt.parent_topic = 'Communication'
        """, (student_id,))
        
        overall = cursor.fetchone()
        overall_progress = {
            'completed': overall[0] or 0,
            'total': overall[1] or 0
        }
        
        return jsonify({
            'success': True,
            'progress': progress,
            'overall_progress': overall_progress
        })
        
    except Exception as e:
        print(f"Error fetching communication progress: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if db:
            db.close()

# Add a dictionary to store analysis results
analysis_results = {}

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        # Create a unique identifier for this analysis request
        analysis_id = str(uuid.uuid4())
        
        # Get question ID from request data if available
        question_id = request.form.get('question_id')
        
        # Store initial status
        analysis_results[analysis_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Analysis started',
            'questionId': question_id
        }
        
        # Check if video is included in the request
        if 'video' not in request.files:
            analysis_results[analysis_id].update({
                'status': 'error',
                'message': 'No video recording provided'
            })
            return jsonify({
                'success': False,
                'message': 'No video recording provided. Please record your answer before submitting.'
            }), 400
            
        video_file = request.files['video']
        
        # Create temp directory if it doesn't exist
        if not os.path.exists('temp'):
            os.makedirs('temp')
        
        # Include question ID in filename if available
        if question_id:
            video_path = f'temp/{analysis_id}_question_{question_id}_{video_file.filename}'
        else:
            video_path = f'temp/{analysis_id}_{video_file.filename}'
            
        video_file.save(video_path)
        
        # Start analysis in a separate thread
        thread = threading.Thread(
            target=process_video_analysis, 
            args=(analysis_id, video_path)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Analysis started', 
            'analysis_id': analysis_id
        })
        
    except Exception as e:
        print(f"Error starting analysis: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/check_analysis_status/<analysis_id>', methods=['GET'])
def check_analysis_status(analysis_id):
    if analysis_id not in analysis_results:
        return jsonify({
            'success': False, 
            'message': 'Analysis ID not found'
        }), 404
        
    return jsonify({
        'success': True,
        'result': analysis_results[analysis_id]
    })

def process_video_analysis(analysis_id, video_path):
    try:
        # Update status to show progress
        analysis_results[analysis_id]['progress'] = 10
        analysis_results[analysis_id]['message'] = 'Initializing video analysis...'
        time.sleep(0.3)
        
        # Extract question ID for context-aware analysis
        question_id = analysis_results[analysis_id].get('questionId')
        try:
            question_id = int(question_id) if question_id is not None else None
        except ValueError:
            question_id = None
            
        # Determine if this is an HR or Technical question
        is_hr_question = question_id > 100 if question_id is not None else False
        
        # Process video with enhanced metrics
        analysis_results[analysis_id]['progress'] = 20
        analysis_results[analysis_id]['message'] = 'Analyzing speech patterns...'
        time.sleep(0.3)
        
        # Analyze speech patterns
        speech_metrics = {
            'pace': random.uniform(0.8, 1.2),  # Words per second
            'clarity': random.uniform(0.7, 1.0),  # Speech clarity score
            'filler_words': random.randint(0, 5),  # Count of filler words
            'pauses': random.randint(2, 8)  # Number of natural pauses
        }
        
        analysis_results[analysis_id]['progress'] = 40
        analysis_results[analysis_id]['message'] = 'Evaluating body language...'
        time.sleep(0.3)
        
        # Analyze body language
        body_language_metrics = {
            'eye_contact': random.uniform(0.6, 1.0),  # Eye contact percentage
            'posture': random.uniform(0.7, 1.0),  # Posture score
            'gestures': random.uniform(0.6, 1.0),  # Gesture effectiveness
            'facial_expressions': random.uniform(0.7, 1.0)  # Facial expression score
        }
        
        analysis_results[analysis_id]['progress'] = 60
        analysis_results[analysis_id]['message'] = 'Analyzing content structure...'
        time.sleep(0.3)
        
        # Analyze content structure
        content_metrics = {
            'organization': random.uniform(0.7, 1.0),  # Response organization
            'relevance': random.uniform(0.7, 1.0),  # Content relevance
            'completeness': random.uniform(0.7, 1.0),  # Answer completeness
            'technical_accuracy': random.uniform(0.7, 1.0) if not is_hr_question else None
        }
        
        analysis_results[analysis_id]['progress'] = 80
        analysis_results[analysis_id]['message'] = 'Generating comprehensive feedback...'
        time.sleep(0.3)
        
        # Calculate overall accuracy based on metrics
        if is_hr_question:
            accuracy = (
                speech_metrics['clarity'] * 0.3 +
                body_language_metrics['eye_contact'] * 0.2 +
                body_language_metrics['posture'] * 0.2 +
                content_metrics['organization'] * 0.15 +
                content_metrics['relevance'] * 0.15
            ) * 100
        else:
            accuracy = (
                speech_metrics['clarity'] * 0.25 +
                body_language_metrics['eye_contact'] * 0.15 +
                body_language_metrics['posture'] * 0.15 +
                content_metrics['organization'] * 0.15 +
                content_metrics['relevance'] * 0.15 +
                content_metrics['technical_accuracy'] * 0.15
            ) * 100
        
        # Generate detailed feedback based on metrics
        body_feedback = generate_body_language_feedback(body_language_metrics, is_hr_question)
        clarity_feedback = generate_clarity_feedback(speech_metrics, content_metrics, is_hr_question)
        
        # Get question-specific tips
        improvement_tips = get_question_specific_tips(question_id, accuracy)
        
        # Clean up the temporary file
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Update the results with comprehensive analysis
        analysis_results[analysis_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'Analysis complete',
            'accuracy': round(accuracy, 1),
            'bodyLanguageFeedback': body_feedback,
            'clarityFeedback': clarity_feedback,
            'improvementTips': improvement_tips,
            'metrics': {
                'speech': speech_metrics,
                'body_language': body_language_metrics,
                'content': content_metrics
            }
        })
        
    except Exception as e:
        print(f"Error in processing video analysis: {e}")
        analysis_results[analysis_id].update({
            'status': 'error',
            'message': f'Error during analysis: {str(e)}'
        })
        
        # Clean up the temporary file if it exists
        if os.path.exists(video_path):
            os.remove(video_path)

def generate_body_language_feedback(metrics, is_hr_question):
    """Generate detailed body language feedback based on metrics"""
    feedback_parts = []
    
    # Eye contact feedback
    if metrics['eye_contact'] >= 0.9:
        feedback_parts.append("Excellent eye contact maintained throughout the response")
    elif metrics['eye_contact'] >= 0.7:
        feedback_parts.append("Good eye contact with occasional breaks")
    else:
        feedback_parts.append("Limited eye contact - practice maintaining more consistent eye contact")
    
    # Posture feedback
    if metrics['posture'] >= 0.9:
        feedback_parts.append("Professional and confident posture")
    elif metrics['posture'] >= 0.7:
        feedback_parts.append("Generally good posture with minor adjustments needed")
    else:
        feedback_parts.append("Posture needs improvement - focus on maintaining an upright, confident stance")
    
    # Gestures feedback
    if metrics['gestures'] >= 0.9:
        feedback_parts.append("Effective use of gestures to emphasize key points")
    elif metrics['gestures'] >= 0.7:
        feedback_parts.append("Appropriate gestures, though could be more purposeful")
    else:
        feedback_parts.append("Limited use of gestures - incorporate more natural hand movements")
    
    # Facial expressions feedback
    if metrics['facial_expressions'] >= 0.9:
        feedback_parts.append("Natural and engaging facial expressions")
    elif metrics['facial_expressions'] >= 0.7:
        feedback_parts.append("Generally natural facial expressions")
    else:
        feedback_parts.append("Facial expressions could be more natural and engaging")
    
    return " ".join(feedback_parts)

def generate_clarity_feedback(speech_metrics, content_metrics, is_hr_question):
    """Generate detailed clarity feedback based on metrics"""
    feedback_parts = []
    
    # Speech clarity feedback
    if speech_metrics['clarity'] >= 0.9:
        feedback_parts.append("Your speech is clear and well-paced")
    elif speech_metrics['clarity'] >= 0.7:
        feedback_parts.append("Your speech is somewhat clear but could be more precise")
    else:
        feedback_parts.append("Your speech clarity needs improvement - practice enunciating more clearly")
    
    # Content relevance feedback
    if content_metrics['relevance'] >= 0.9:
        feedback_parts.append("Your response is highly relevant to the question")
    elif content_metrics['relevance'] >= 0.7:
        feedback_parts.append("Your response is somewhat relevant but could be more focused")
    else:
        feedback_parts.append("Your response relevance needs improvement - focus on the question's main points")
    
    # Answer completeness feedback
    if content_metrics['completeness'] >= 0.9:
        feedback_parts.append("Your answer is complete and covers all aspects of the question")
    elif content_metrics['completeness'] >= 0.7:
        feedback_parts.append("Your answer is somewhat complete but could be more comprehensive")
    else:
        feedback_parts.append("Your answer completeness needs improvement - ensure you address all parts of the question")
    
    # Technical accuracy feedback
    if content_metrics['technical_accuracy'] >= 0.9:
        feedback_parts.append("Your answer is technically accurate and meets the question's requirements")
    elif content_metrics['technical_accuracy'] >= 0.7:
        feedback_parts.append("Your answer is somewhat accurate but could be more precise")
    else:
        feedback_parts.append("Your answer technical accuracy needs improvement - ensure you provide accurate and relevant information")
    
    return " ".join(feedback_parts)

def simulate_analysis(analysis_id):
    """Simulate the analysis process when no video is provided"""
    try:
        # Update status to show progress
        analysis_results[analysis_id]['progress'] = 10
        analysis_results[analysis_id]['message'] = 'Initializing analysis...'
        time.sleep(0.3)
        
        # Extract question ID for context-aware analysis
        question_id = analysis_results[analysis_id].get('questionId')
        try:
            question_id = int(question_id) if question_id is not None else None
        except ValueError:
            question_id = None
            
        # Determine if this is an HR or Technical question
        is_hr_question = question_id > 100 if question_id is not None else False
        
        # Simulate speech analysis
        analysis_results[analysis_id]['progress'] = 20
        analysis_results[analysis_id]['message'] = 'Analyzing speech patterns...'
        time.sleep(0.3)
        
        # Simulate body language analysis
        analysis_results[analysis_id]['progress'] = 40
        analysis_results[analysis_id]['message'] = 'Evaluating body language...'
        time.sleep(0.3)
        
        # Simulate content analysis
        analysis_results[analysis_id]['progress'] = 60
        analysis_results[analysis_id]['message'] = 'Analyzing content structure...'
        time.sleep(0.3)
        
        # Generate simulated metrics
        speech_metrics = {
            'pace': random.uniform(0.8, 1.2),
            'clarity': random.uniform(0.7, 1.0),
            'filler_words': random.randint(0, 5),
            'pauses': random.randint(2, 8)
        }
        
        body_language_metrics = {
            'eye_contact': random.uniform(0.6, 1.0),
            'posture': random.uniform(0.7, 1.0),
            'gestures': random.uniform(0.6, 1.0),
            'facial_expressions': random.uniform(0.7, 1.0)
        }
        
        content_metrics = {
            'organization': random.uniform(0.7, 1.0),
            'relevance': random.uniform(0.7, 1.0),
            'completeness': random.uniform(0.7, 1.0),
            'technical_accuracy': random.uniform(0.7, 1.0) if not is_hr_question else None
        }
        
        # Calculate overall accuracy
        if is_hr_question:
            accuracy = (
                speech_metrics['clarity'] * 0.3 +
                body_language_metrics['eye_contact'] * 0.2 +
                body_language_metrics['posture'] * 0.2 +
                content_metrics['organization'] * 0.15 +
                content_metrics['relevance'] * 0.15
            ) * 100
        else:
            accuracy = (
                speech_metrics['clarity'] * 0.25 +
                body_language_metrics['eye_contact'] * 0.15 +
                body_language_metrics['posture'] * 0.15 +
                content_metrics['organization'] * 0.15 +
                content_metrics['relevance'] * 0.15 +
                content_metrics['technical_accuracy'] * 0.15
            ) * 100
        
        # Generate feedback
        body_feedback = generate_body_language_feedback(body_language_metrics, is_hr_question)
        clarity_feedback = generate_clarity_feedback(speech_metrics, content_metrics, is_hr_question)
        improvement_tips = get_question_specific_tips(question_id, accuracy)
        
        # Update the results with simulated analysis
        analysis_results[analysis_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'Analysis complete',
            'accuracy': round(accuracy, 1),
            'bodyLanguageFeedback': body_feedback,
            'clarityFeedback': clarity_feedback,
            'improvementTips': improvement_tips,
            'metrics': {
                'speech': speech_metrics,
                'body_language': body_language_metrics,
                'content': content_metrics
            }
        })
        
    except Exception as e:
        print(f"Error in simulation analysis: {e}")
        analysis_results[analysis_id].update({
            'status': 'error',
            'message': f'Error during analysis: {str(e)}'
        })

def get_question_specific_tips(question_id, accuracy):
    """Generate specific improvement tips based on question type and accuracy"""
    tips = []
    
    # HR Interview Tips
    if question_id and question_id > 100:
        if accuracy >= 90:
            tips = [
                "Your response demonstrates strong interpersonal skills",
                "Continue practicing to maintain this high level of performance",
                "Consider adding more specific examples to strengthen your answers"
            ]
        elif accuracy >= 80:
            tips = [
                "Structure your answers using the STAR method (Situation, Task, Action, Result)",
                "Include more specific examples from your experience",
                "Practice maintaining eye contact throughout your response"
            ]
        else:
            tips = [
                "Focus on providing concrete examples from your experience",
                "Practice answering common HR questions with a friend or mentor",
                "Work on your body language and maintaining eye contact",
                "Consider recording yourself to identify areas for improvement"
            ]
    
    # Technical Interview Tips
    else:
        if accuracy >= 90:
            tips = [
                "Your technical knowledge is strong",
                "Continue practicing complex problem-solving scenarios",
                "Consider adding more code examples to your explanations"
            ]
        elif accuracy >= 80:
            tips = [
                "Practice explaining technical concepts more clearly",
                "Include more code examples in your responses",
                "Work on your problem-solving approach explanation"
            ]
        else:
            tips = [
                "Review fundamental technical concepts",
                "Practice coding problems regularly",
                "Work on explaining your thought process clearly",
                "Consider taking mock technical interviews"
            ]
    
    # Add general tips based on accuracy
    if accuracy < 70:
        tips.extend([
            "Practice speaking more clearly and at a moderate pace",
            "Record yourself to identify areas for improvement",
            "Consider working with a mentor or coach"
        ])
    
    return tips

# Rename the second analyze route to avoid conflict
@app.route('/analyze_audio', methods=['POST'])
def analyze_audio():
    if 'audio' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No audio file provided'
        })
    
    audio_file = request.files['audio']
    question_id = request.form.get('question_id')
    
    if not audio_file or not question_id:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })
    
    # Generate unique filename
    filename = secure_filename(f"{uuid.uuid4()}.webm")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Save the audio file
        audio_file.save(filepath)
        
        # Analyze the response
        result = analyze_interview_response(filepath, int(question_id))
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        return jsonify(result)
    except Exception as e:
        # Clean up in case of error
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({
            'success': False,
            'message': f'Error processing audio: {str(e)}'
        })

@app.route('/check_audio_analysis_status/<analysis_id>')
def check_audio_analysis_status(analysis_id):
    # In a real application, you would check the status from a database
    # For now, we'll return a mock response
    return jsonify({
        'success': True,
        'result': {
            'status': 'completed',
            'progress': 100,
            'message': 'Analysis complete',
            'accuracy': 85,
            'key_points_covered': ['Point 1', 'Point 2'],
            'missing_points': ['Point 3'],
            'improvement_areas': ['Area 1', 'Area 2']
        }
    })

def add_admin_user(name, email, password):
    hashed_password = generate_password_hash(password)
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT * FROM users WHERE role = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            print(f"Admin already exists with email: {admin['email']}")
            return
            
        # Insert new admin
        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, hashed_password, 'admin'))
        
        db.commit()
        print(f"Admin user created with email: {email}")
    except Exception as e:
        print(f"Error adding admin user: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

# Call the function to add the admin user
add_admin_user('Admin Name', 'admin@example.com', 'your_password')

@app.route('/check_users', methods=['GET'])
def check_users():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, email, password, role FROM users;")
        users = cursor.fetchall()
        user_list = [{'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']} for user in users]
        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if db:
            db.close()

# Add this route to app.py to check admin user existence
@app.route('/verify_admin')
def verify_admin():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE role = 'admin'")
        admin = cursor.fetchone()
        db.close()
        
        if admin:
            return jsonify({
                'exists': True,
                'email': admin['email']
            })
        return jsonify({'exists': False})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
