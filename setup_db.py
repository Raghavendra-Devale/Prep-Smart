import sqlite3

def create_tables():
    conn = sqlite3.connect("placement_preparation.db")
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'company', 'admin'))
    );
    """)
    
    # Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        department TEXT,
        graduation_year INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    
    # Companies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        industry TEXT,
        location TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    
    # Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        job_title TEXT NOT NULL,
        description TEXT,
        requirements TEXT,
        salary TEXT,
        location TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    );
    """)
    
    # Applications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        job_id INTEGER,
        status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'rejected')),
        application_date TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );
    """)
    
    # Interviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        interview_date TEXT NOT NULL,
        feedback TEXT,
        interviewer TEXT,
        interview_mode TEXT,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    );
    """)
    
    # Job Offers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        offer_status TEXT NOT NULL CHECK(offer_status IN ('offered', 'declined')),
        salary TEXT,
        joining_date TEXT,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    );
    """)
    
    # Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        topic TEXT,
        difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard'))
    );
    """)
    
    # Student Answers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        question_id INTEGER,
        student_answer TEXT NOT NULL,
        is_correct BOOLEAN,
        attempt_date TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    );
    """)
    
    # Student Progress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_progress (
        progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        is_completed INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, question_id, topic_id)
    );
    """)
    
    # Aptitude Progress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aptitude_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL,
        is_completed BOOLEAN DEFAULT 0,
        completion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        UNIQUE(student_id, problem_id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("Database and tables created successfully!")

if __name__ == "__main__":
    create_tables()
