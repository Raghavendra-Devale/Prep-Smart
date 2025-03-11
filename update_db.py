import sqlite3

def update_database():
    try:
        conn = sqlite3.connect('placement_preparation.db')
        cursor = conn.cursor()

        # Drop existing table if it exists
        cursor.execute("DROP TABLE IF EXISTS student_progress")

        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE student_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                is_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, question_id, topic_id)
            )
        """)

        conn.commit()
        print("Database updated successfully!")

    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == "__main__":
    update_database() 