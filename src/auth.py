import bcrypt
import mariadb
from src.database import get_connection

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, email, password, role='user'):
    conn = get_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (username, email, hash_password(password), role)
        )
        conn.commit()
        return True
    except mariadb.Error:
        return False
    finally:
        conn.close()

def get_user(email):
    conn = get_connection()
    if not conn:
        return None
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_connection()
    if not conn:
        return []
    
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role, created_at FROM users")
    users = cur.fetchall()
    conn.close()
    return users