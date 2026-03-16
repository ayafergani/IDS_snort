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

def modifier_regle(first_sid,line):
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
           UPDATE regles
           SET sid = %s, message = %s, protocol = %s,
               src_ip = %s, src_port = %s, dst_ip = %s,
               dst_port = %s, action = %s, rule = %s
           WHERE sid = %s
           """,
        (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line, first_sid)
    )
    conn.commit()

def supprimer_regle(sid):
    cursor.execute(
        """
           DELETE FROM regles
           WHERE sid = %s
           """,
        (sid,)
    )
    conn.commit()

def reset_db():
    cursor.execute(
        """
           TRUNCATE TABLE regles;
        """
    )
    conn.commit()