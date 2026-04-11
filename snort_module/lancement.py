import subprocess
import time
import threading
import re
from datetime import datetime
import os


class SnortManager:
    def __init__(self, interface="enp0s3", log_dir="./snort_log"):
        self.interface = interface
        self.log_dir = log_dir
        self.alert_file = os.path.join(log_dir, "alert")
        self.snort_process = None
        self.snort_running = False
        self.alert_callback = None
        self.alert_count = 0

        # Créer le dossier de logs
        os.makedirs(log_dir, exist_ok=True)

        # Vider l'ancien fichier d'alertes
        if os.path.exists(self.alert_file):
            os.remove(self.alert_file)

    def set_alert_callback(self, callback):
        """Définit une fonction à appeler pour chaque alerte (pour l'interface)"""
        self.alert_callback = callback

    def start_snort(self):
        """Démarre Snort avec lecture des alertes en temps réel"""
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
            print(f"📁 Fichier alertes: {self.alert_file}")
            print(f"⏰ Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}\n")

            print("🚀 Snort actif... Lance ton attaque !\n")

            self.snort_process = subprocess.Popen(cmd)
            self.snort_running = True

            # Démarrer le thread de lecture des alertes
            thread = threading.Thread(target=self._watch_alerts, daemon=True)
            thread.start()

            return True
        except Exception as e:
            print(f"❌ Erreur démarrage Snort: {e}")
            return False

    def _watch_alerts(self):
        """Surveille le fichier d'alertes en temps réel (tail -F)"""
        time.sleep(2)  # Attendre que Snort crée le fichier

        while self.snort_running and self.snort_process and self.snort_process.poll() is None:
            if os.path.exists(self.alert_file):
                try:
                    with open(self.alert_file, 'r') as f:
                        # Aller à la fin du fichier
                        f.seek(0, os.SEEK_END)

                        while self.snort_running:
                            line = f.readline()
                            if not line:
                                time.sleep(0.1)
                                continue

                            line = line.strip()
                            if not line:
                                continue

                            # Format Snort fast alert:
                            # [**] [1:1000001:1] Attack message [**]
                            if "[**]" in line:
                                header_line = line
                                next_line = f.readline().strip()

                                if next_line:
                                    self.alert_count += 1
                                    alert_data = self._parse_alert(header_line, next_line)

                                    # Afficher dans le terminal
                                    self._display_alert(alert_data)

                                    # Appeler le callback si défini (pour l'interface)
                                    if self.alert_callback:
                                        self.alert_callback(alert_data)
                except Exception as e:
                    print(f"Erreur lecture fichier: {e}")
            else:
                time.sleep(1)

    def _parse_alert(self, header_line, ip_line):
        """Parse une alerte Snort"""
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
            'raw_header': header_line,
            'raw_ip': ip_line
        }

        # Timestamp (ex: 03/26-23:34:30.947840)
        ts_match = re.search(r'(\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)', ip_line)
        if ts_match:
            alert['timestamp'] = ts_match.group(1)

        # SID (ex: 1:3000040:1)
        sid_match = re.search(r'\[(\d+:\d+:\d+)\]', header_line)
        if sid_match:
            alert['sid'] = sid_match.group(1)

        # Message d'attaque
        msg_match = re.search(r'\[\*\*\] \[[0-9:]+\] (.*) \[\*\*\]', header_line)
        if msg_match:
            alert['attack_type'] = msg_match.group(1).strip()

        # Priorité (sévérité)
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

        return alert

    def _display_alert(self, alert):
        """Affiche l'alerte dans le terminal"""
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
        print(f"\033[91m{'=' * 80}\033[0m")

    def stop_snort(self):
        """Arrête Snort"""
        if self.snort_process:
            self.snort_process.terminate()
            time.sleep(2)
            if self.snort_process.poll() is None:
                self.snort_process.kill()

        subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)
        self.snort_running = False

        print(f"\n{'=' * 80}")
        print(f"📋 RAPPORT FINAL")
        print(f"{'=' * 80}")
        print(f"🚨 Alertes détectées: {self.alert_count}")
        print(f"{'=' * 80}")

    def is_running(self):
        return self.snort_running


# ============================================================
# Fonctions pour l'intégration avec dashboard.py
# ============================================================

_snort_manager = None


def get_snort_manager(interface="enp0s8"):
    """Retourne l'instance unique du SnortManager"""
    global _snort_manager
    if _snort_manager is None:
        _snort_manager = SnortManager(interface=interface)
    return _snort_manager


def start_snort(interface="enp0s8"):
    """Démarre Snort (appelé depuis dashboard.py)"""
    manager = get_snort_manager(interface)
    return manager.start_snort()


def stop_snort():
    """Arrête Snort (appelé depuis dashboard.py)"""
    global _snort_manager
    if _snort_manager:
        _snort_manager.stop_snort()
        _snort_manager = None


if __name__ == "__main__":
    # Mode standalone
    manager = SnortManager(interface="enp0s8")
    try:
        if manager.start_snort():
            while manager.is_running():
                time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_snort()