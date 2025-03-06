import sqlite3

conn = sqlite3.connect("placement_preparation.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM students;")
students = cursor.fetchall()

if not students:
    print("No students found in the database!")
else:
    for student in students:
        print(student)

conn.close()
