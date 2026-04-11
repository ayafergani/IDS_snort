#!/usr/bin/env python3
import subprocess
import time
import threading
import re
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db_connection import connect_db


class SnortManager:
    def __init__(self, interface="enp0s3", log_dir="./snort_log"):
        self.interface = interface
        self.log_dir = log_dir
        self.alert_file = os.path.join(log_dir, "alert")
        self.snort_process = None
        self.snort_running = False
        self.alert_count = 0
        self.db_connection = None
        self.db_cursor = None
        self.db_insert_count = 0

        os.makedirs(log_dir, exist_ok=True)

        if os.path.exists(self.alert_file):
            os.remove(self.alert_file)

        self.init_database()

    def init_database(self):
        try:
            self.db_connection = connect_db()
            if self.db_connection:
                self.db_cursor = self.db_connection.cursor()
                print("✅ Connexion à PostgreSQL établie")
        except Exception as e:
            print(f"⚠️ Base de données non disponible: {e}")

    def convert_timestamp(self, timestamp_str):
        try:
            date_part, time_part = timestamp_str.split('-')
            month, day = date_part.split('/')
            year = datetime.now().year
            return f"{year}-{month}-{day} {time_part}"
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def convert_severity(self, severity_value):
        if severity_value == 0 or severity_value == 1:
            return 'élevée'
        elif severity_value == 2:
            return 'moyenne'
        elif severity_value == 3:
            return 'basse'
        return 'inconnue'

    def parse_alert(self, header_line, ip_line):
        timestamp = ""
        ts_match = re.search(r'(\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)', ip_line)
        if ts_match:
            timestamp = ts_match.group(1)
        else:
            timestamp = datetime.now().strftime("%m/%d-%H:%M:%S")

        sid = ""
        sid_match = re.search(r'\[(\d+:\d+:\d+)\]', header_line)
        if sid_match:
            sid = sid_match.group(1)

        msg = ""
        msg_match = re.search(r'\[\*\*\] \[[0-9:]+\] (.*) \[\*\*\]', header_line)
        if msg_match:
            msg = msg_match.group(1).strip()

        priority = 0
        prio_match = re.search(r'Priority: (\d+)', header_line)
        if prio_match:
            priority = int(prio_match.group(1))

        proto = ""
        proto_match = re.search(r'\{([^}]+)\}', ip_line)
        if proto_match:
            proto = proto_match.group(1)

        ip_ports = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', ip_line)

        src_ip = None
        src_port = None
        dst_ip = None
        dst_port = None

        if len(ip_ports) >= 1:
            src_ip = ip_ports[0][0]
            src_port = int(ip_ports[0][1]) if ip_ports[0][1].isdigit() else None
        if len(ip_ports) >= 2:
            dst_ip = ip_ports[1][0]
            dst_port = int(ip_ports[1][1]) if ip_ports[1][1].isdigit() else None

        return {
            'timestamp_raw': timestamp,
            'timestamp': self.convert_timestamp(timestamp),
            'sid': sid,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'attack_type': msg,
            'severity': priority,
            'protocol': proto,
            'src_port': src_port,
            'dst_port': dst_port,
            'detection_engine': sid.split(':')[0] if sid else 'Snort'
        }

    def save_to_db(self, alert):
        if not self.db_connection:
            return False

        try:
            severity_text = self.convert_severity(alert['severity'])

            attack_type = alert['attack_type']
            if attack_type and len(attack_type) > 200:
                attack_type = attack_type[:200]

            details = alert['attack_type']
            if details and len(details) > 500:
                details = details[:500]

            self.db_cursor.execute("""
                INSERT INTO alertes (
                    timestamp, source_ip, destination_ip,
                    attack_type, severity, detection_engine,
                    details, protocol, source_port, destination_port
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert['timestamp'],
                alert['src_ip'],
                alert['dst_ip'],
                attack_type,
                severity_text,
                alert['detection_engine'],
                details,
                alert['protocol'],
                alert['src_port'],
                alert['dst_port']
            ))
            self.db_connection.commit()
            self.db_insert_count += 1
            return True
        except Exception as e:
            print(f"   ❌ Erreur DB: {e}")
            try:
                self.db_connection.rollback()
            except:
                pass
            return False

    def start_snort(self):
        try:
            cmd = f"sudo snort -A fast -c /etc/snort/snort.conf -i {self.interface} -l {self.log_dir}"

            print(f"\n{'=' * 80}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU")
            print(f"{'=' * 80}")
            print(f"📡 Interface: {self.interface}")
            print(f"💾 Base de données: {'✅ Activée' if self.db_connection else '❌ Désactivée'}")
            print(f"{'=' * 80}\n")

            self.snort_process = subprocess.Popen(cmd, shell=True)
            self.snort_running = True

            thread = threading.Thread(target=self._tail_alerts, daemon=True)
            thread.start()

            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def _tail_alerts(self):
        time.sleep(2)

        while self.snort_running and self.snort_process and self.snort_process.poll() is None:
            if os.path.exists(self.alert_file):
                try:
                    with open(self.alert_file, 'r') as f:
                        f.seek(0, os.SEEK_END)
                        while self.snort_running:
                            line = f.readline()
                            if not line:
                                time.sleep(0.1)
                                continue

                            line = line.strip()
                            if not line:
                                continue

                            if "[**]" in line:
                                header_line = line
                                next_line = f.readline().strip()
                                if next_line:
                                    self.alert_count += 1
                                    alert = self.parse_alert(header_line, next_line)
                                    severity_text = self.convert_severity(alert['severity'])
                                    print(f"\n\033[91m🚨 {alert['attack_type']} [{severity_text}]\033[0m")
                                    if self.db_connection:
                                        self.save_to_db(alert)
                except:
                    pass
            else:
                time.sleep(1)

    # ============================================================
    # ⚡ SEULE MODIFICATION : L'ARRÊT (rapide et non-bloquant)
    # ============================================================
    def stop_snort(self):
        """Arrête Snort - rapide, non-bloquant, ne ferme pas l'app"""
        try:
            subprocess.run(["sudo", "pkill", "-f", "snort"],
                           capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            subprocess.run(["sudo", "pkill", "-9", "-f", "snort"],
                           capture_output=True)
        except:
            pass

        self.snort_running = False
        self.snort_process = None
        print("\n🛑 Snort arrêté")

    def is_running(self):
        return self.snort_running


_snort_manager = None


def start_snort(interface="enp0s3"):
    global _snort_manager
    if _snort_manager is None:
        _snort_manager = SnortManager(interface=interface)
    return _snort_manager.start_snort()


def stop_snort():
    global _snort_manager
    if _snort_manager:
        _snort_manager.stop_snort()
        _snort_manager = None


if __name__ == "__main__":
    manager = SnortManager(interface="enp0s3")
    try:
        manager.start_snort()
        while manager.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_snort()