# data/db_connection.py
import psycopg2

def connect_db():
    conn = psycopg2.connect(
        host="localhost",  # ← Changer de 192.168.1.2 à localhost
        database="ids_db",
        user="aya",
        password="aya",
        port="5432"
    )
    return conn