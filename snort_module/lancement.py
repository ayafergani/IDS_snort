#!/usr/bin/env python3
import subprocess
import time
import threading
import re
import os
import signal
import sys
from datetime import datetime

# Ajouter le chemin pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db_connection import connect_db


class SnortManager:
    def __init__(self, interface="enp0s8", log_dir="./snort_log"):
        self.interface = interface
        self.log_dir = log_dir
        self.alert_file = os.path.join(log_dir, "alert")
        self.snort_process = None
        self.snort_running = False
        self.connection = None
        self.cursor = None
        self.alert_count = 0
        self.db_count = 0

        # Créer le dossier de logs
        os.makedirs(log_dir, exist_ok=True)

        # Vider l'ancien fichier d'alertes
        if os.path.exists(self.alert_file):
            os.remove(self.alert_file)

        # Initialiser la base de données
        self.init_db()

    def init_db(self):
        """Initialise la connexion à PostgreSQL"""
        try:
            self.connection = connect_db()
            if self.connection:
                self.cursor = self.connection.cursor()
                print("✅ Connexion à PostgreSQL établie")
        except Exception as e:
            print(f"⚠️ Base de données non disponible: {e}")

    def get_network_metrics(self):
        """Récupère les métriques réseau (loss, traffic, services)"""
        loss_rate = "0"
        try:
            result = subprocess.run(
                ["ping", "-c", "2", "-q", "8.8.8.8"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r'(\d+)% packet loss', result.stdout)
            if match:
                loss_rate = match.group(1)
        except:
            pass

        # Trafic réseau
        rx_traffic = "0"
        tx_traffic = "0"
        try:
            with open(f"/sys/class/net/{self.interface}/statistics/rx_bytes", 'r') as f:
                rx_bytes = int(f.read().strip())
            with open(f"/sys/class/net/{self.interface}/statistics/tx_bytes", 'r') as f:
                tx_bytes = int(f.read().strip())
            rx_traffic = f"{rx_bytes / 1024 / 1024:.2f}"
            tx_traffic = f"{tx_bytes / 1024 / 1024:.2f}"
        except:
            pass

        # Services actifs
        active_services = ""
        try:
            result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
            ports = re.findall(r':(\d+)', result.stdout)
            active_services = ','.join(sorted(set(ports))[:10])
        except:
            pass

        return loss_rate, f"RX:{rx_traffic}MB TX:{tx_traffic}MB", active_services

    def parse_alert(self, header_line, ip_line):
        """Parse une alerte Snort (identique au script bash)"""
        alert = {
            'timestamp': None,
            'sid': None,
            'source_ip': None,
            'destination_ip': None,
            'source_port': None,
            'destination_port': None,
            'attack_type': None,
            'severity': 0,
            'protocol': None,
            'loss': None,
            'traffic': None,
            'services': None,
            'raw_header': header_line,
            'raw_ip': ip_line
        }

        # Timestamp
        ts_match = re.search(r'(\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)', ip_line)
        if ts_match:
            alert['timestamp'] = ts_match.group(1)

        # SID
        sid_match = re.search(r'\[(\d+:\d+:\d+)\]', header_line)
        if sid_match:
            alert['sid'] = sid_match.group(1)

        # Attack type (message)
        msg_match = re.search(r'\[\*\*\] \[[0-9:]+\] (.*) \[\*\*\]', header_line)
        if msg_match:
            alert['attack_type'] = msg_match.group(1).strip()

        # Severity (priority)
        prio_match = re.search(r'Priority: (\d+)', header_line)
        if prio_match:
            alert['severity'] = int(prio_match.group(1))

        # Protocole
        proto_match = re.search(r'\{([^}]+)\}', ip_line)
        if proto_match:
            alert['protocol'] = proto_match.group(1)

        # IPs et ports
        ip_ports = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', ip_line)
        if len(ip_ports) >= 1:
            alert['source_ip'] = ip_ports[0][0]
            alert['source_port'] = int(ip_ports[0][1])
        if len(ip_ports) >= 2:
            alert['destination_ip'] = ip_ports[1][0]
            alert['destination_port'] = int(ip_ports[1][1])

        # Métriques réseau
        loss_rate, traffic, services = self.get_network_metrics()
        alert['loss'] = loss_rate
        alert['traffic'] = traffic
        alert['services'] = services

        return alert

    def save_to_db(self, alert):
        """Sauvegarde l'alerte dans PostgreSQL"""
        if not self.connection:
            return False

        try:
            # Convertir le timestamp
            timestamp = datetime.now()
            if alert['timestamp']:
                try:
                    ts = datetime.strptime(alert['timestamp'], "%m/%d-%H:%M:%S.%f")
                    timestamp = ts.replace(year=datetime.now().year)
                except:
                    pass

            self.cursor.execute("""
                INSERT INTO alertes 
                (timestamp, source_ip, destination_ip, attack_type, severity, 
                 protocol, source_port, destination_port, loss, volume, service, 
                 detection_engine, sid, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timestamp,
                alert['source_ip'],
                alert['destination_ip'],
                alert['attack_type'],
                alert['severity'],
                alert['protocol'],
                alert['source_port'],
                alert['destination_port'],
                alert['loss'],
                alert['traffic'],
                alert['services'],
                'Snort',
                alert['sid'],
                alert['raw_header'][:500]
            ))
            self.connection.commit()
            self.db_count += 1
            return True
        except Exception as e:
            print(f"❌ Erreur insertion DB: {e}")
            return False

    def display_alert(self, alert):
        """Affiche l'alerte formatée"""
        print(f"\n\033[91m{'=' * 80}\033[0m")
        print(f"\033[91m🚨 ALERTE #{self.alert_count}\033[0m")
        print(f"\033[91m{'=' * 80}\033[0m")
        print(f"📅 Timestamp: {alert['timestamp']}")
        print(f"🆔 SID: {alert['sid']}")
        print(f"📍 Source: {alert['source_ip']}:{alert['source_port']}")
        print(f"🎯 Destination: {alert['destination_ip']}:{alert['destination_port']}")
        print(f"📡 Protocole: {alert['protocol']}")
        print(f"⚠️ Type: {alert['attack_type']}")
        print(f"🔴 Sévérité: {alert['severity']}")
        print(f"📊 Loss: {alert['loss']}% | Traffic: {alert['traffic']}")
        print(f"🔧 Services: {alert['services']}")
        print(f"\033[91m{'=' * 80}\033[0m")

    def start(self):
        """Démarre Snort"""
        try:
            cmd = [
                "sudo", "snort",
                "-A", "fast",
                "-c", "/etc/snort/snort.conf",
                "-i", self.interface,
                "-l", self.log_dir
            ]

            print(f"\n{'=' * 80}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU")
            print(f"{'=' * 80}")
            print(f"📡 Interface: {self.interface}")
            print(f"📁 Logs: {self.log_dir}/alert")
            print(f"💾 Base de données: {'✅ Activée' if self.connection else '❌ Désactivée'}")
            print(f"{'=' * 80}\n")

            print("🚀 Démarrage de Snort...")
            print("🎯 Surveillance active - Lance ton attaque !\n")

            self.snort_process = subprocess.Popen(cmd)
            self.snort_running = True

            # Démarrer le thread de lecture des alertes
            thread = threading.Thread(target=self._tail_alerts, daemon=True)
            thread.start()

            return True
        except Exception as e:
            print(f"❌ Erreur démarrage Snort: {e}")
            return False

    def _tail_alerts(self):
        """Lit le fichier alert en temps réel (comme tail -F)"""
        time.sleep(2)  # Attendre que Snort crée le fichier

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

                            # Si c'est une alerte (format Snort fast)
                            if "[**]" in line:
                                header_line = line
                                next_line = f.readline().strip()
                                if next_line:
                                    self.alert_count += 1
                                    alert = self.parse_alert(header_line, next_line)
                                    self.display_alert(alert)

                                    if self.connection:
                                        if self.save_to_db(alert):
                                            print(f"   💾 Sauvegardé en DB (total: {self.db_count})")
                except Exception as e:
                    print(f"Erreur lecture fichier alert: {e}")
            else:
                time.sleep(1)

    def stop(self):
        """Arrête Snort"""
        if self.snort_process:
            self.snort_process.terminate()
            time.sleep(2)
            if self.snort_process.poll() is None:
                self.snort_process.kill()

        subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

        if self.connection:
            self.cursor.close()
            self.connection.close()

        self.snort_running = False

        print(f"\n{'=' * 80}")
        print(f"📋 RAPPORT FINAL")
        print(f"{'=' * 80}")
        print(f"🚨 Alertes détectées: {self.alert_count}")
        print(f"💾 Alertes en DB: {self.db_count}")
        print(f"{'=' * 80}")

    def is_running(self):
        return self.snort_running


def main():
    """Fonction principale"""
    manager = SnortManager(interface="enp0s8")  # Change l'interface si besoin

    # Gestion de l'arrêt propre
    def signal_handler(sig, frame):
        print("\n\n🛑 Arrêt demandé...")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if manager.start():
        try:
            while manager.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop()


if __name__ == "__main__":
    main()