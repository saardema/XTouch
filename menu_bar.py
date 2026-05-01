import os
import signal

import rumps
import subprocess

LOG_PATH = "/tmp/ctrl_mix.log"


class MenuBar(rumps.App):
    def __init__(self):
        super().__init__("CtrlMix")
        self.process = None

        self.start(None)
        self.open_mixer(None)

    @rumps.clicked("Mixer")
    def open_mixer(self, _):
        subprocess.Popen(["open", "-a", "Mixer"])

    def start(self, _):
        if self.process is None:
            self.process = subprocess.Popen(
                "python ctrl_mix/app.py",
                shell=True,
                stdout=open(LOG_PATH, "a"),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )

    @rumps.clicked("Start")
    def stop_start(self, _):
        self.stop(None)
        self.start(None)

    @rumps.clicked("Stop")
    def stop(self, _):
        if self.process:
            pid = os.getpgid(self.process.pid)
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                print(f"Process already terminated. PID {pid}")
            self.process = None

    @rumps.clicked("Show Logs")
    def logs(self, _):
        subprocess.Popen(["open", LOG_PATH])

    @rumps.clicked("Clear logs")
    def clear_logs(self, _):
        subprocess.Popen(["truncate", "-s", "0", LOG_PATH])


if __name__ == "__main__":
    MenuBar().run()
