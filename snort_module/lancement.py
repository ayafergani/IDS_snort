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

        # Créer le dossier de logs
        os.makedirs(log_dir, exist_ok=True)

        # Vider l'ancien fichier d'alertes
        if os.path.exists(self.alert_file):
            os.remove(self.alert_file)

        # Initialiser la connexion DB
        self.init_database()

    def init_database(self):
        """Initialise la connexion à PostgreSQL"""
        try:
            self.db_connection = connect_db()
            if self.db_connection:
                self.db_cursor = self.db_connection.cursor()
                print("✅ Connexion à PostgreSQL établie")
                return True
        except Exception as e:
            print(f"⚠️ Base de données non disponible: {e}")
        return False

    def ensure_db_connection(self):
        """Vérifie et rétablit la connexion DB si nécessaire"""
        try:
            if not self.db_connection or self.db_connection.closed:
                print("⚠️ Connexion DB perdue, reconnexion...")
                return self.init_database()

            # Tester la connexion
            self.db_cursor.execute("SELECT 1")
            self.db_cursor.fetchone()
            return True
        except Exception:
            print("⚠️ Connexion DB perdue, reconnexion...")
            try:
                self.db_connection.close()
            except:
                pass
            return self.init_database()

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
        # Extraire le timestamp
        timestamp = ""
        ts_match = re.search(r'(\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)', ip_line)
        if ts_match:
            timestamp = ts_match.group(1)
        else:
            timestamp = datetime.now().strftime("%m/%d-%H:%M:%S")

        # Extraire le SID
        sid = ""
        sid_match = re.search(r'\[(\d+:\d+:\d+)\]', header_line)
        if sid_match:
            sid = sid_match.group(1)

        # Extraire le message (attack type)
        msg = ""
        msg_match = re.search(r'\[\*\*\] \[[0-9:]+\] (.*) \[\*\*\]', header_line)
        if msg_match:
            msg = msg_match.group(1).strip()

        # Extraire la priorité (severity)
        priority = 0
        prio_match = re.search(r'Priority: (\d+)', header_line)
        if prio_match:
            priority = int(prio_match.group(1))

        # Extraire le protocole
        proto = ""
        proto_match = re.search(r'\{([^}]+)\}', ip_line)
        if proto_match:
            proto = proto_match.group(1)

        # Extraire les IP et ports
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

        # Récupérer les métriques réseau
        loss_rate, traffic, services = self.get_network_metrics()

        return {
            'timestamp': timestamp,
            'sid': sid,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'attack_type': msg,
            'severity': priority,
            'protocol': proto,
            'src_port': src_port,
            'dst_port': dst_port,
            'loss': loss_rate,
            'traffic': traffic,
            'services': services,
            'detection_engine': sid.split(':')[0] if sid else 'Snort'
        }

    def save_to_db(self, alert):
        """Insère l'alerte dans la base avec gestion des erreurs"""
        if not self.ensure_db_connection():
            print("   ⚠️ Pas de connexion DB, alerte non sauvegardée")
            return False

        try:
            # Nettoyer les valeurs
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
                    details, protocol, source_port,
                    destination_port, loss, volume, service
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert['timestamp'],
                alert['src_ip'],
                alert['dst_ip'],
                attack_type,
                alert['severity'],
                alert['detection_engine'],
                details,
                alert['protocol'],
                alert['src_port'],
                alert['dst_port'],
                alert['loss'],
                alert['traffic'],
                alert['services']
            ))
            self.db_connection.commit()
            self.db_insert_count += 1
            return True

        except Exception as e:
            print(f"   ❌ Erreur insertion DB: {e}")
            # 🔥 CRUCIAL: Annuler la transaction pour pouvoir continuer
            try:
                self.db_connection.rollback()
            except Exception as rollback_err:
                print(f"   ↳ Erreur rollback: {rollback_err}")
            return False

    def start_snort(self):
        """Démarre Snort et lit les alertes"""
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
            print(f"💾 Base de données: {'✅ Activée' if self.db_connection else '❌ Désactivée'}")
            print(f"{'=' * 80}\n")

            print("🚀 Snort actif... Lance ton attaque !\n")

            self.snort_process = subprocess.Popen(cmd)
            self.snort_running = True

            # Démarrer le thread de lecture (comme tail -F)
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

                            # Format Snort fast alert: [**] ... [**]
                            if "[**]" in line:
                                header_line = line
                                next_line = f.readline().strip()

                                if next_line:
                                    self.alert_count += 1
                                    alert = self.parse_alert(header_line, next_line)

                                    # Afficher l'alerte
                                    self._display_alert(alert)

                                    # Sauvegarder en DB
                                    if self.db_connection:
                                        if self.save_to_db(alert):
                                            print(f"   💾 [DB] Alerte #{self.db_insert_count} enregistrée")
                except Exception as e:
                    print(f"Erreur lecture fichier: {e}")
            else:
                time.sleep(1)

    def _display_alert(self, alert):
        """Affiche l'alerte formatée"""
        print(f"\n\033[91m{'=' * 80}\033[0m")
        print(f"\033[91m🚨 ALERTE #{self.alert_count}\033[0m")
        print(f"\033[91m{'=' * 80}\033[0m")
        print(f"📅 Timestamp: {alert['timestamp']}")
        print(f"🆔 SID: {alert['sid']}")
        print(f"📍 Source: {alert['src_ip']}:{alert['src_port']}")
        print(f"🎯 Destination: {alert['dst_ip']}:{alert['dst_port']}")
        print(f"📡 Protocole: {alert['protocol']}")
        print(f"⚠️ Type: {alert['attack_type']}")
        print(f"🔴 Sévérité: {alert['severity']}")
        print(f"📊 Loss: {alert['loss']}% | Traffic: {alert['traffic']}")
        print(f"🔧 Services: {alert['services']}")
        print(f"\033[91m{'=' * 80}\033[0m")

    def stop_snort(self):
        """Arrête Snort"""
        if self.snort_process:
            self.snort_process.terminate()
            time.sleep(2)
            if self.snort_process.poll() is None:
                self.snort_process.kill()

        subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

        if self.db_connection:
            try:
                self.db_cursor.close()
                self.db_connection.close()
            except:
                pass

        self.snort_running = False

        print(f"\n{'=' * 80}")
        print(f"📋 RAPPORT FINAL")
        print(f"{'=' * 80}")
        print(f"🚨 Alertes détectées: {self.alert_count}")
        print(f"💾 Alertes enregistrées en DB: {self.db_insert_count}")
        print(f"{'=' * 80}")

    def is_running(self):
        return self.snort_running


# ============================================================
# Fonctions pour l'intégration avec dashboard.py
# ============================================================

_snort_manager = None


def start_snort(interface="enp0s3"):
    """Démarre Snort (appelé depuis dashboard.py)"""
    global _snort_manager
    if _snort_manager is None:
        _snort_manager = SnortManager(interface=interface)
    return _snort_manager.start_snort()


def stop_snort():
    """Arrête Snort (appelé depuis dashboard.py)"""
    global _snort_manager
    if _snort_manager:
        _snort_manager.stop_snort()
        _snort_manager = None


# ============================================================
# MAIN - Mode standalone
# ============================================================

if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("\n\n🛑 Arrêt demandé...")
        if '_snort_manager' in globals() and _snort_manager:
            _snort_manager.stop_snort()
        sys.exit(0)


    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager = SnortManager(interface="enp0s3")
    try:
        if manager.start_snort():
            while manager.is_running():
                time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_snort()