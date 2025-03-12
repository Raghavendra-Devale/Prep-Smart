import sqlite3

def test_progress():
    try:
        conn = sqlite3.connect('placement_preparation.db')
        cursor = conn.cursor()
        
        # First, let's check what's in student_answers
        print("Current student_answers:")
        cursor.execute("SELECT * FROM student_answers WHERE student_id = 6")
        print(cursor.fetchall())
        
        # Now let's try to complete question 2 for the same student
        cursor.execute("""
            INSERT INTO student_answers 
            (student_id, question_id, topic_id, given_answer, is_correct) 
            VALUES (6, 2, 1, '', 1)
        """)
        
        # Update or insert into student_progress
        cursor.execute("""
            INSERT OR REPLACE INTO student_progress 
            (student_id, topic_id, completed_questions, total_questions, is_completed) 
            VALUES (6, 1, 2, 15, 0)
        """)
        
        conn.commit()
        print("\nProgress updated!")
        
        # Verify both tables
        print("\nUpdated student_answers:")
        cursor.execute("SELECT * FROM student_answers WHERE student_id = 6")
        print(cursor.fetchall())
        
        print("\nUpdated student_progress:")
        cursor.execute("SELECT * FROM student_progress WHERE student_id = 6")
        print(cursor.fetchall())
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_progress() 