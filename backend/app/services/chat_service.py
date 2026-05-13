import uuid
from datetime import datetime
from app.database.mysql_client import MySQLClient

class ChatService:
    def __init__(self):
        self.db = MySQLClient()

    def create_session(self, user_id: int, title: str) -> str:
        session_id = str(uuid.uuid4())
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (%s, %s, %s)",
            (session_id, user_id, title)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return session_id

    def get_user_sessions(self, user_id: int):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM chat_sessions WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        return sessions

    def delete_session(self, session_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Hard delete session (Cascade will handle messages if DB is set up correctly)
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()
        conn.close()

    def save_message(self, session_id: str, role: str, content: str, data: dict = None):
        import json
        from decimal import Decimal
        from datetime import date, datetime

        # Helper to handle non-serializable types like Decimal, Date, Datetime
        def serialize_helper(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, data) VALUES (%s, %s, %s, %s)",
            (session_id, role, content, json.dumps(data, default=serialize_helper) if data else None)
        )
        # Also update the updated_at time of the session
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = %s WHERE id = %s",
            (datetime.utcnow(), session_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def get_session_messages(self, session_id: str):
        import json
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT role, content, data, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        messages = cursor.fetchall()
        for msg in messages:
            if msg["data"]:
                msg["data"] = json.loads(msg["data"])
        cursor.close()
        conn.close()
        return messages
    
    def get_session(self, session_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM chat_sessions WHERE id = %s", (session_id,))
        session = cursor.fetchone()
        cursor.close()
        conn.close()
        return session
