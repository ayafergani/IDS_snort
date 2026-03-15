import psycopg2
import re
from data.db_connection import connect_db

conn =connect_db()

cursor = conn.cursor()

def afficher_db():
    cursor.execute(
        """
        SELECT sid,rule FROM regles;
        """
    )
    rows=cursor.fetchall()
    return rows

def ajouter_regle(line):
    action = line.split()[0]
    protocol = line.split()[1]
    src_ip = line.split()[2]
    src_port = line.split()[3]
    dst_ip = line.split()[5]
    dst_port = line.split()[6]

    msg = re.search(r'msg:"(.*?)"', line)
    sid = re.search(r'sid:(\d+)', line)

    message = msg.group(1) if msg else ""
    sid = sid.group(1) if sid else None

    cursor.execute(
        """
        INSERT INTO regles
        (sid,message,protocol,src_ip,src_port,dst_ip,dst_port,action,rule)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (sid) DO NOTHING
        """,
        (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line)
    )
    conn.commit()
