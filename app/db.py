import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'motorush'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Conexión exitosa a la base de datos.")
            return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None
