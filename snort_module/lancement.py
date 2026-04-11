import subprocess
import time
import threading
import re
import psycopg2
from datetime import datetime
from data.db_connection import connect_db


class SnortManager:
    def __init__(self, interface="enp0s3"):
        self.snort_running = False
        self.snort_process = None
        self.output_thread = None
        self.interface = interface
        self.db_connection = None
        self.db_cursor = None

        # Initialiser connexion DB
        self.init_database()

    def init_database(self):
        """Initialise la connexion à la base de données"""
        try:
            self.db_connection = connect_db()
            if self.db_connection:
                self.db_cursor = self.db_connection.cursor()
                print("✅ Connexion à la base de données établie")
            else:
                print("⚠️ Base de données non disponible - alertes non sauvegardées")
        except Exception as e:
            print(f"⚠️ Erreur DB: {e}")

    def parse_alert_line(self, line):
        """Extrait les informations d'une ligne d'alerte Snort"""
        alert_data = {
            'timestamp': datetime.now(),
            'source_ip': None,
            'destination_ip': None,
            'source_port': None,
            'destination_port': None,
            'protocol': None,
            'attack_type': 'Unknown',
            'severity': 'medium',
            'details': line[:500],
            'detection_engine': 'Snort'
        }

        # Pattern pour IP:Port
        ip_port_pattern = r'(\d+\.\d+\.\d+\.\d+):(\d+)'
        matches = re.findall(ip_port_pattern, line)

        if len(matches) >= 1:
            alert_data['source_ip'] = matches[0][0]
            alert_data['source_port'] = int(matches[0][1]) if matches[0][1].isdigit() else None
        if len(matches) >= 2:
            alert_data['destination_ip'] = matches[1][0]
            alert_data['destination_port'] = int(matches[1][1]) if matches[1][1].isdigit() else None

        # Détection du protocole
        if 'TCP' in line.upper():
            alert_data['protocol'] = 'TCP'
        elif 'UDP' in line.upper():
            alert_data['protocol'] = 'UDP'
        elif 'ICMP' in line.upper():
            alert_data['protocol'] = 'ICMP'

        # Déterminer le type d'attaque
        attack_patterns = {
            'ICMP_PING': r'ICMP.*PING|ICMP Echo Request',
            'PORT_SCAN': r'scan|portscan|port_scan',
            'DOS_ATTACK': r'(dos|ddos|flood|syn flood)',
            'MALWARE': r'(malware|trojan|worm|virus|exploit)',
            'ARP_SPOOFING': r'arp.*spoof|arp.*poison',
            'BRUTE_FORCE': r'brute.?force|dictionary|login.*fail'
        }

        for attack, pattern in attack_patterns.items():
            if re.search(pattern, line, re.I):
                alert_data['attack_type'] = attack
                break

        # Déterminer la sévérité
        if any(word in line.upper() for word in ['CRITICAL', 'EMERGENCY', 'ALERT']):
            alert_data['severity'] = 'critical'
        elif any(word in line.upper() for word in ['WARNING', 'ATTACK', 'EXPLOIT']):
            alert_data['severity'] = 'high'
        elif any(word in line.upper() for word in ['SUSPICIOUS', 'SCAN']):
            alert_data['severity'] = 'medium'
        else:
            alert_data['severity'] = 'low'

        return alert_data

    def save_alert_to_db(self, alert_data):
        """Sauvegarde une alerte dans la base de données"""
        if not self.db_connection or not self.db_cursor:
            return False

        try:
            self.db_cursor.execute("""
                INSERT INTO alertes 
                (timestamp, source_ip, destination_ip, attack_type, severity, 
                 detection_engine, details, protocol, source_port, destination_port)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert_data['timestamp'],
                alert_data['source_ip'],
                alert_data['destination_ip'],
                alert_data['attack_type'],
                alert_data['severity'],
                alert_data['detection_engine'],
                alert_data['details'],
                alert_data['protocol'],
                alert_data['source_port'],
                alert_data['destination_port']
            ))
            self.db_connection.commit()
            print(f"   💾 Alerte enregistrée: {alert_data['attack_type']} - {alert_data['severity']}")
            return True
        except Exception as e:
            print(f"   ❌ Erreur sauvegarde DB: {e}")
            try:
                self.db_connection.rollback()
            except:
                pass
            return False

    def start_snort(self):
        try:
            print(f"\n{'=' * 80}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU EN TEMPS RÉEL")
            print(f"{'=' * 80}")
            print(f"📡 Interface: {self.interface}")
            print(f"💾 Base de données: {'✅ Activée' if self.db_connection else '❌ Désactivée'}")
            print(f"⏰ Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}\n")

            # Commande Snort
            cmd = f"sudo snort -A console -i {self.interface} -c /etc/snort/snort.conf -k none"

            print(f"🔄 Démarrage de Snort...")
            print(f"📝 Commande: {cmd}\n")
            print("🎯 Surveillance active - Les alertes seront enregistrées en DB\n")

            self.snort_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Thread de lecture
            self.output_thread = threading.Thread(target=self.process_output, daemon=True)
            self.output_thread.start()

            self.snort_running = True
            return True

        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def process_output(self):
        """Traite la sortie de Snort et enregistre les alertes"""
        for line in iter(self.snort_process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line and not line.startswith("=+"):

                    # Détection d'alerte
                    is_alert = "ALERT" in line.upper() or "ATTACK" in line.upper()

                    # Affichage
                    if is_alert:
                        print(f"\n\033[91m🚨 {line}\033[0m")
                        # Enregistrer dans la DB
                        alert_data = self.parse_alert_line(line)
                        self.save_alert_to_db(alert_data)
                    elif "UDP" in line or "TCP" in line:
                        print(f"\033[90m📦 {line}\033[0m")
                    else:
                        print(line)

            if self.snort_process.poll() is not None:
                break

    def stop_snort(self):
        try:
            if self.snort_process:
                self.snort_process.terminate()
                time.sleep(2)
                if self.snort_process.poll() is None:
                    self.snort_process.kill()

            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

            if self.db_connection:
                self.db_cursor.close()
                self.db_connection.close()

            self.snort_running = False
            print("\n" + "=" * 70)
            print("🛑 Snort arrêté")
            print("=" * 70)
            return True
        except Exception as e:
            print(f"❌ Erreur arrêt: {e}")
            return False

    def is_running(self):
        try:
            result = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)
            self.snort_running = result.returncode == 0
            return self.snort_running
        except:
            return False


# Pour exécuter directement
if __name__ == "__main__":
    manager = SnortManager(interface="enp0s3")
    try:
        if manager.start_snort():
            while manager.snort_running:
                time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_snort()