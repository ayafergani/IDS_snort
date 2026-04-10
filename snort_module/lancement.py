import subprocess

class SnortManager:
    def __init__(self):
        self.process = None

    def start_snort(self):
        try:
            cmd = [
                "sudo", "-n", "snort",
                "-A", "fast",
                "-i", "ens33",  # ⚠️ adapte
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort"
            ]

            # 🔥 éviter double lancement
            if hasattr(self, "snort_process") and self.snort_process and self.snort_process.poll() is None:
                print("⚠️ Snort déjà en cours")
                return

            self.snort_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            import time
            time.sleep(2)

            # ❗ Vérification propre
            if self.snort_process.poll() is None:
                print("✅ Snort RUNNING")
                self.start_btn.setText("🟢 RUNNING")
            else:
                err = self.snort_process.stderr.read().decode()
                print("❌ Snort FAILED TO START")
                print(err)

        except Exception as e:
            print("❌ Exception:", e)

    def stop_snort(self):
        if self.process:
            self.process.terminate()
            self.process = None
            print("Snort stopped")