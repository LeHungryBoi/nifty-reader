"""Hot-reload runner for Voice Fusion Tool.

Watches for .py file changes and restarts gui.py automatically.
Exits when the GUI window is closed.
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

from watchfiles import watch, Change

ROOT = Path(__file__).parent

# Only restart on .py changes (ignore .pyc, .json, etc.)
_WATCH_EXTENSIONS = {".py"}


def _should_restart(changes):
    """Only trigger restart for .py file modifications."""
    for change_type, path_str in changes:
        if change_type in (Change.added, Change.modified, Change.deleted):
            p = Path(path_str)
            if p.suffix in _WATCH_EXTENSIONS and p.name != "run.py":
                return True
    return False


def main():
    state = {"proc": None, "restart": False, "cooldown_until": 0.0}

    def watch_loop():
        try:
            for changes in watch(str(ROOT), stop_event=None):
                now = time.monotonic()
                if now < state["cooldown_until"]:
                    continue  # skip events during cooldown

                if not _should_restart(changes):
                    continue

                proc = state["proc"]
                if proc is None or proc.poll() is not None:
                    continue
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                state["restart"] = True
        except Exception:
            pass

    watcher = threading.Thread(target=watch_loop, daemon=True)
    watcher.start()

    while True:
        state["proc"] = subprocess.Popen(
            [sys.executable, "gui.py"], cwd=str(ROOT),
        )
        state["restart"] = False
        state["proc"].wait()
        if not state["restart"]:
            break  # user closed the GUI
        # Cooldown: ignore file changes for 2s after restart to avoid rapid loops
        state["cooldown_until"] = time.monotonic() + 2.0

    sys.exit(0)


if __name__ == "__main__":
    main()
