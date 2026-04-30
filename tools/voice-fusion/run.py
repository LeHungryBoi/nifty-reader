"""Hot-reload runner for Voice Fusion Tool.

Watches for .py file changes and restarts gui.py automatically.
Exits when the GUI window is closed.
"""

import subprocess
import sys
import threading
from pathlib import Path

from watchfiles import watch

ROOT = Path(__file__).parent


def main():
    state = {"proc": None, "restart": False}

    def watch_loop():
        try:
            for _changes in watch(str(ROOT)):
                proc = state["proc"]
                if proc is None or proc.poll() is not None:
                    continue
                proc.terminate()
                proc.wait()
                state["restart"] = True
        except Exception:
            pass

    watcher = threading.Thread(target=watch_loop, daemon=True)
    watcher.start()

    while True:
        state["proc"] = subprocess.Popen([sys.executable, "gui.py"], cwd=str(ROOT))
        state["restart"] = False
        state["proc"].wait()
        if not state["restart"]:
            break  # user closed the GUI

    sys.exit(0)


if __name__ == "__main__":
    main()
