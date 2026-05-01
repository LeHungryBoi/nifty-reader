"""Hot-reload runner for Voice Fusion Tool.

Uses jurigged for in-process code reloading — GUI state is fully preserved
when .py files change, no process restart needed.
"""

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    # Install jurigged if not present
    try:
        import jurigged
    except ImportError:
        import subprocess
        print("Installing jurigged...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "jurigged"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import jurigged

    # Start jurigged watcher on the tool directory (exclusive)
    jurigged.watch(str(ROOT), poll=False)

    # Now run the GUI in the same process
    # We import gui here so jurigged can track all subsequently imported modules
    from gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
