import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class MySQLClient:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.database = os.getenv("DB_NAME", "wealth_management")

    def get_connection(self, use_db=True):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database if use_db else None
        )

    def execute_query(self, sql):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            conn.commit()
            return results, None
        except Exception as e:
            return None, str(e)
        finally:
            cursor.close()
            conn.close()

    def get_schema_metadata(self):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        metadata = {}
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            column_details = [f"{col['Field']} ({col['Type']})" for col in columns]
            metadata[table] = {
                "summary": f"Table: {table}. Columns: {', '.join(column_details)}",
                "columns": [col['Field'] for col in columns]
            }
        cursor.close()
        conn.close()
        return metadata
