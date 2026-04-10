import subprocess
import time
import os
import sys


class SnortManager:
    def __init__(self):
        self.snort_running = False
        self.snort_pid = None
        self.snort_process = None  # Pour garder le processus

    def start_snort(self):
        try:
            interface = "enp0s3"

            print(f"🚀 Lancement de Snort sur l'interface {interface}...")
            print("📡 Snort va afficher les alertes en temps réel dans le terminal")
            print("-" * 60)

            # Commande SANS -D (pas de mode daemon) pour voir la sortie
            cmd = [
                "sudo", "snort",
                "-A", "console",  # Mode console pour voir les alertes
                "-i", interface,
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort",
                "-v"  # Mode verbeux pour voir tout le trafic
            ]

            # Lancer Snort et capturer la sortie en temps réel
            self.snort_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Attendre que Snort démarre
            time.sleep(2)

            # Vérifier si le processus tourne
            if self.snort_process.poll() is None:
                self.snort_running = True
                print("✅ Snort démarré avec succès - Surveillance active")
                print("-" * 60)

                # Lire et afficher la sortie en temps réel
                self.read_output()
                return True
            else:
                print("❌ Snort n'a pas démarré")
                return False

        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

    def read_output(self):
        """Lit et affiche la sortie de Snort en temps réel"""
        try:
            for line in iter(self.snort_process.stdout.readline, ''):
                if line:
                    # Colorer les alertes en rouge
                    if "ALERT" in line or "ATTACK" in line or "WARNING" in line:
                        print(f"\033[91m{line.strip()}\033[0m")  # Rouge
                    elif "Normal" in line or "OK" in line:
                        print(f"\033[92m{line.strip()}\033[0m")  # Vert
                    else:
                        print(line.strip())
                if self.snort_process.poll() is not None:
                    break
        except Exception as e:
            print(f"Erreur lecture: {e}")

    def start_snort_daemon(self):
        """Version daemon (silencieuse) - alternative"""
        try:
            interface = "enp0s3"

            cmd = [
                "sudo", "snort",
                "-A", "fast",
                "-i", interface,
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort",
                "-D"
            ]

            subprocess.Popen(cmd)
            time.sleep(2)

            check = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)
            if check.returncode == 0:
                self.snort_running = True
                print("✅ Snort démarré en mode daemon (silencieux)")
                return True
            return False
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

    def stop_snort(self):
        try:
            # Arrêter le processus si on l'a lancé en mode console
            if self.snort_process and self.snort_process.poll() is None:
                self.snort_process.terminate()
                time.sleep(2)
                if self.snort_process.poll() is None:
                    self.snort_process.kill()
                self.snort_process = None

            # Tuer tous les processus Snort
            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

            self.snort_running = False
            print("\n" + "-" * 60)
            print("🛑 Snort arrêté")
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