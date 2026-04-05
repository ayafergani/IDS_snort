import re
from data.db_connection import connect_db

def parser_et_inserer_alertes(fichier):
    conn = connect_db()
    cursor = conn.cursor()

    with open(fichier, "r") as f:
        lines = f.readlines()

    for line in lines:
        # ignorer header et lignes vides
        if "|" not in line or "Timestamp" in line:
            continue

        parts = [p.strip() for p in line.split("|")]

        if len(parts) < 12:
            continue

        try:
            timestamp = parts[0]
            sid_full = parts[1]
            src_ip = parts[2]
            dst_ip = parts[3]
            attack_raw = parts[4]
            severity = int(parts[5])
            protocol = parts[6]
            src_port = int(parts[7])
            dst_port = int(parts[8])
            loss = parts[9]
            traffic = parts[10]
            services = parts[11]

            # 🔹 detection_engine
            sid_parts = sid_full.split(":")
            detection_engine = sid_parts[0] if len(sid_parts) > 0 else None

            # 🔹 nettoyer attack type
            attack_clean = re.sub(r'^\d{2}/\d{2}-[\d:.]+\s+', '', attack_raw)

            details = attack_raw

            cursor.execute("""
                INSERT INTO alertes (
                    timestamp, source_ip, destination_ip,
                    attack_type, severity, detection_engine,
                    details, protocol, source_port,
                    destination_port, loss, volume, service
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timestamp, src_ip, dst_ip,
                attack_clean, severity, detection_engine,
                details, protocol, src_port,
                dst_port, loss, traffic, services
            ))

        except Exception as e:
            print("⚠️ Ligne ignorée :", line)
            print("Erreur :", e)
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()


# 🔥 MAIN
if __name__ == "__main__":
    fichier = "alertes.txt"  # adapte le chemin
    parser_et_inserer_alertes(fichier)
    print("✅ Import terminé")