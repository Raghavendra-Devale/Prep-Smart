import sqlite3

def update_database():
    try:
        # Connect to database
        conn = sqlite3.connect('placement_preparation.db')
        cursor = conn.cursor()

        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS student_answers")
        cursor.execute("DROP TABLE IF EXISTS student_progress")
        cursor.execute("DROP TABLE IF EXISTS progress_topics")
        cursor.execute("DROP TABLE IF EXISTS dsa_overall_progress")

        # Create progress_topics table with parent_topic field
        cursor.execute("""
            CREATE TABLE progress_topics (
                topic_id INTEGER PRIMARY KEY,
                topic_name TEXT NOT NULL,
                total_questions INTEGER DEFAULT 0,
                parent_topic TEXT DEFAULT NULL
            )
        """)

        # Insert default topics with DSA as parent topic for DSA-related topics
        topics = [
            (1, 'Basic Programming', 15, 'DSA'),
            (2, 'Arrays and Strings', 12, 'DSA'),
            (3, 'Linked Lists', 10, 'DSA'),
            (4, 'Stacks and Queues', 8, 'DSA'),
            (5, 'Trees and Graphs', 10, 'DSA'),
            (6, 'Searching and Sorting', 8, 'DSA'),
            (7, 'Dynamic Programming', 8, 'DSA'),
            (8, 'Recursion and Backtracking', 8, 'DSA'),
            (9, 'Greedy Algorithms', 8, 'DSA'),
            (10, 'Bit Manipulation', 8, 'DSA')
        ]
        
        cursor.executemany("""
            INSERT INTO progress_topics (topic_id, topic_name, total_questions, parent_topic)
            VALUES (?, ?, ?, ?)
        """, topics)

        # Create student_answers table
        cursor.execute("""
            CREATE TABLE student_answers (
                answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                given_answer TEXT,
                is_correct BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, question_id, topic_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (topic_id) REFERENCES progress_topics(topic_id)
            )
        """)

        # Create student_progress table for individual topic progress
        cursor.execute("""
            CREATE TABLE student_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, topic_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (topic_id) REFERENCES progress_topics(topic_id)
            )
        """)

        # Create dsa_overall_progress table to track overall DSA progress
        cursor.execute("""
            CREATE TABLE dsa_overall_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                completed_questions INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)

        # Calculate total DSA questions
        cursor.execute("""
            SELECT SUM(total_questions) 
            FROM progress_topics 
            WHERE parent_topic = 'DSA'
        """)
        total_dsa_questions = cursor.fetchone()[0]
        print(f"Total DSA questions across all topics: {total_dsa_questions}")

        # Commit changes
        conn.commit()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_database() 