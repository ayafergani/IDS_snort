import subprocess

class SnortManager:
    def __init__(self):
        self.process = None

    def start_snort(self):
        if self.process is None:
            cmd = [
                "sudo",
                "-n",  # ⚠️ important (no password prompt)
                "snort",
                "-A", "fast",
                "-i", "enp0s3",
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort"
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            print("Snort started")

    def stop_snort(self):
        if self.process:
            self.process.terminate()
            self.process = None
            print("Snort stopped")