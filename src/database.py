import mariadb
import os
from dotenv import load_dotenv
import sys

load_dotenv()

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'heatfarm_db')
}

def get_connection():
    """MariaDB 연결 반환"""
    try:
        conn = mariadb.connect(**DB_CONFIG)
        print("DB 연결 성공!")
        return conn
    except mariadb.Error as e:
        print(f"DB 연결 실패: {e}")
        print(f"DB_CONFIG: {DB_CONFIG}")  
        return None

def init_db():
    """users 테이블 생성"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("users 테이블 생성/확인 완료!")
        conn.close()
        return True
    except mariadb.Error as e:
        print(f"테이블 생성 에러: {e}")
        conn.close()
        return False

def test_connection():
    """연결 테스트용"""
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"연결 테스트 성공: {result}")
        conn.close()
        return True
    return False

if __name__ == "__main__":
    print("=== DB 테스트 ===")
    test_connection()
    init_db()
