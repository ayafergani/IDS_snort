import subprocess

class SnortManager:
    def __init__(self):
        self.process = None
        self.snort_running = False
        self.snort_process = None

    def start_snort(self):
        try:
            cmd = [
                "sudo", "-n", "snort",
                "-A", "fast",
                "-i", "enp0s3",
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort"
            ]

            if self.snort_process and self.snort_process.poll() is None:
                print("⚠️ Snort déjà en cours")
                self.snort_running = True
                return

            self.snort_process = subprocess.Popen(cmd)

            import time
            time.sleep(2)

            if self.snort_process.poll() is None:
                self.snort_running = True
                print("✅ Snort started successfully")
            else:
                self.snort_running = False
                print("❌ Snort FAILED")

        except Exception as e:
            self.snort_running = False
            print("❌ Exception:", e)

    def stop_snort(self):
        if self.process:
            self.process.terminate()
            self.process = None
            print("Snort stopped")