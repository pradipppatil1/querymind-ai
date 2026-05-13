import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.database.mysql_client import MySQLClient

# Load config from env
SECRET_KEY = os.getenv("JWT_SECRET", "secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.db = MySQLClient()

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store in DB
        self._store_refresh_token(data["sub"], token, expire)
        return token

    def _store_refresh_token(self, username: str, token: str, expires_at: datetime):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            # Delete old tokens for this user (or keep multiple, but for now we'll limit)
            cursor.execute("DELETE FROM refresh_tokens WHERE user_id = %s", (user["id"],))
            cursor.execute(
                "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user["id"], token, expires_at)
            )
        conn.commit()
        cursor.close()
        conn.close()

    def verify_refresh_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                return None
            
            # Check DB
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM refresh_tokens WHERE token = %s", (token,))
            stored_token = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not stored_token or stored_token["expires_at"] < datetime.utcnow():
                return None
                
            return payload
        except JWTError:
            return None

    def get_user_by_username(self, username: str):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user

    def update_last_login(self, username: str):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE username = %s",
            (datetime.utcnow(), username)
        )
        conn.commit()
        cursor.close()
        conn.close()
