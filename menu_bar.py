import os
import signal
import sys

from AppKit import NSApplicationActivationPolicyAccessory
from AppKit import NSApplication
import rumps
import subprocess

LOG_PATH = os.path.expanduser("~/Library/Logs/com.CtrlMix.log")
sub_process: subprocess.Popen | None = None


class MenuBar(rumps.App):
    def __init__(self):
        super().__init__("CtrlMix", quit_button=None)

    @rumps.clicked("Restart")
    def restart(self, _):
        stop_core()
        start_core()

    @rumps.clicked("Show Logs")
    def logs(self, _):
        subprocess.Popen(["open", LOG_PATH])

    @rumps.clicked("Clear logs")
    def clear_logs(self, _):
        open(LOG_PATH, "w")

    @rumps.clicked('Quit')
    def quit(self, _): shutdown()


def start_core():
    global sub_process

    if sub_process is None:
        sub_process = subprocess.Popen(
            [sys.executable, "ctrl_mix/app.py"],
            stdout=open(LOG_PATH, "a"),
            stderr=subprocess.STDOUT,
        )


def stop_core():
    global sub_process

    if sub_process is not None:
        sub_process.terminate()
        sub_process.wait(timeout=1)
        sub_process = None


def shutdown(*_):
    stop_core()
    rumps.quit_application()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    nsapp = NSApplication.sharedApplication()
    nsapp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    start_core()
    app = MenuBar()
    app.run()

    rumps.quit_application()
