import subprocess
import time
import threading


class SnortManager:
    def __init__(self):
        self.snort_running = False
        self.snort_process = None
        self.output_thread = None

    def start_snort(self):
        try:
            interface = "enp0s3"

            print(f"\n{'=' * 70}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU")
            print(f"{'=' * 70}")
            print(f"Interface: {interface}")
            print(f"Mode: Alertes uniquement (moins de bruit)")
            print(f"{'=' * 70}\n")

            # Option 1: Alertes seulement (recommandé)
            cmd = f"sudo snort -A console -i {interface} -c /etc/snort/snort.conf"

            # Option 2: Pour voir plus de détails sur les alertes:
            # cmd = f"sudo snort -A full -i {interface} -c /etc/snort/snort.conf"

            # Option 3: Pour tout voir (comme avant):
            # cmd = f"sudo snort -v -i {interface} -A console"

            self.snort_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Démarrer un thread pour lire la sortie
            self.output_thread = threading.Thread(target=self.read_output, daemon=True)
            self.output_thread.start()

            self.snort_running = True
            return True

        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def read_output(self):
        """Affiche les alertes en temps réel avec mise en forme"""
        for line in iter(self.snort_process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line and not line.startswith("=+"):
                    # Mettre en évidence les alertes importantes
                    if "ALERT" in line or "ATTACK" in line:
                        print(f"\033[91m🚨 {line}\033[0m")  # Rouge
                    elif "UDP" in line or "TCP" in line:
                        # Afficher les paquets en gris clair
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

            # Tuer tous les processus Snort
            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

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