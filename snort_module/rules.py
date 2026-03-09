import psycopg2
import re
import GUI.configuration
from GUI.configuration import InterfaceParametresIDS


def fetch_rules_from_db(interface):
    conn = psycopg2.connect(
        dbname="ids_db",
        user="aya",
        password="aya",
        host="192.168.1.2",
        port=5432
    )
    cursor = conn.cursor()
    cursor.execute("SELECT rule FROM regles")  # ta table de règles
    rules = cursor.fetchall()

    for r in rules:
        interface.add_rule_to_table(r[0])  # ajoute directement dans le QTableWidget

    conn.close()
