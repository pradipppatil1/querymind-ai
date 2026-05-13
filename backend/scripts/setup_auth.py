import mysql.connector
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "hospital_billing")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def setup_database():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()

    print("Setting up authentication and chat tables...")

    # Update Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE,
        hashed_password VARCHAR(255) NOT NULL,
        role ENUM('ADMIN', 'USER') DEFAULT 'USER',
        last_login DATETIME,
        password_reset_required BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Check if columns exist (for migration)
    cursor.execute("SHOW COLUMNS FROM users LIKE 'email'")
    if not cursor.fetchone():
        print("Adding email column to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(100) UNIQUE AFTER username")
    
    cursor.execute("SHOW COLUMNS FROM users LIKE 'password_reset_required'")
    if not cursor.fetchone():
        print("Adding password_reset_required column to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN password_reset_required BOOLEAN DEFAULT FALSE AFTER last_login")

    cursor.execute("SHOW COLUMNS FROM users LIKE 'created_at'")
    if not cursor.fetchone():
        print("Adding created_at column to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")

    # Refresh Tokens table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        token VARCHAR(512) NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Chat Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id VARCHAR(36) PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        is_deleted BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Chat Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(36) NOT NULL,
        role ENUM('user', 'assistant') NOT NULL,
        content TEXT NOT NULL,
        data JSON,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )
    """)

    # Ensure CASCADE DELETE is active (in case table existed without it)
    try:
        cursor.execute("ALTER TABLE chat_messages DROP FOREIGN KEY chat_messages_ibfk_1")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE chat_messages ADD CONSTRAINT chat_messages_session_fk FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE")
    except:
        pass

    # Seeding users
    users_to_seed = [
        ("john", "john@example.com", "User@123", "USER"),
        ("emma", "emma@example.com", "User@456", "USER"),
        ("raj", "raj@example.com", "User@789", "USER"),
        ("mike", "mike@example.com", "Admin@123", "ADMIN"),
        ("shiv", "shiv@example.com", "Admin@456", "ADMIN")
    ]

    print("Seeding users...")
    for username, email, password, role in users_to_seed:
        hashed = pwd_context.hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, hashed_password, role) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE email=%s, hashed_password=%s, role=%s",
                (username, email, hashed, role, email, hashed, role)
            )
            print(f"  Processed user: {username} ({role})")
        except Exception as e:
            print(f"  Error seeding {username}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()
