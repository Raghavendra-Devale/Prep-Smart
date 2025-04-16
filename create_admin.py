from app import get_db_connection, generate_password_hash

def ensure_admin_exists():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Admin users data
        admin_users = [
                        {
                'name': 'Aravind',
                'email': 'aravindtv@admin.com',
                'password': 'admin123',
                'role': 'admin'
            }
        ]
        
        for admin_data in admin_users:
            # Check if admin exists
            cursor.execute("SELECT * FROM users WHERE email = ?", (admin_data['email'],))
            admin = cursor.fetchone()
            
            if not admin:
                # Create admin user
                cursor.execute("""
                    INSERT INTO users (name, email, password, role)
                    VALUES (?, ?, ?, ?)
                """, (
                    admin_data['name'],
                    admin_data['email'],
                    generate_password_hash(admin_data['password']),
                    admin_data['role']
                ))
                
                db.commit()
                print(f"Admin created with email: {admin_data['email']}")
                print(f"Password: {admin_data['password']}")
            else:
                print(f"Admin already exists with email: {admin_data['email']}")
            
    except Exception as e:
        print(f"Error: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

if __name__ == "__main__": 
    ensure_admin_exists()