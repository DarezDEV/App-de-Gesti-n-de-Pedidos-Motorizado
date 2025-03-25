from .db import get_db_connection

class User:
    @staticmethod
    def get_user_by_email(gmail):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE gmail = %s", (gmail,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
