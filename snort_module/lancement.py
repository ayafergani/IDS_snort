import subprocess

class SnortManager:
    def __init__(self):
        self.process = None

    def start_snort(self):
        try:
            cmd = [
                "sudo", "-n", "snort",
                "-A", "fast",
                "-i", "eth0",  # ⚠️ vérifier interface
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort"
            ]

            self.snort_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 🔥 attendre 1 seconde pour vérifier si Snort crash
            import time
            time.sleep(1)

            if self.snort_process.poll() is not None:
                err = self.snort_process.stderr.read()
                print("❌ Snort FAILED TO START")
                print(err)
                return

            print("✅ Snort started successfully")

        except Exception as e:
            print("❌ Error:", e)

    def stop_snort(self):
        if self.process:
            self.process.terminate()
            self.process = None
            print("Snort stopped")