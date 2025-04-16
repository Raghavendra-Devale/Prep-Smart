from werkzeug.security import generate_password_hash
from app import get_db_connection

def add_admin_user(name, email, password):
    hashed_password = generate_password_hash(password)
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if the email already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"User with email {email} already exists. Updating role to admin.")
            # Update the existing user's role to admin
            cursor.execute("""
                UPDATE users 
                SET role = ? 
                WHERE email = ?
            """, ('admin', email))
        else:
            # Insert new admin user
            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (name, email, hashed_password, 'admin'))
        
        db.commit()
    except Exception as e:
        print(f"Error adding admin user: {e}")
        db.rollback()
    finally:
        if 'db' in locals():
            db.close()

# Call the function to add the admin user
add_admin_user('Admin Name', 'admindev@gmail.com', '123456')
