"""Auto-restart runner for Fusion Studio.

Watches .py files in the tool directory. When any file changes,
the GUI subprocess is killed and relaunched — guaranteeing all
code changes take effect.
"""

import sys
import subprocess
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent
GUI_ENTRY = "gui"


def get_mtime_map(directory: Path, extensions: list[str] = (".py",)) -> dict[str, float]:
    """Return {file_path: mtime} for all matching files under *directory*."""
    result = {}
    for p in directory.rglob("*"):
        if p.suffix.lower() in extensions:
            result[str(p)] = p.stat().st_mtime
    return result


def main():
    # Ensure UTF-8 mode on Windows
    if sys.flags.utf8_mode == 0 and os.environ.get("VOICE_FUSION_UTF8_REEXEC") != "1":
        env = os.environ.copy()
        env["VOICE_FUSION_UTF8_REEXEC"] = "1"
        cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve())]
        raise SystemExit(subprocess.call(cmd, env=env, cwd=str(ROOT)))

    print("[run] Watching for changes — press Ctrl+C to stop.")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    proc = None

    # initial snapshot
    prev = get_mtime_map(ROOT)

    try:
        while True:
            # Start subprocess if not running
            if proc is None or proc.poll() is not None:
                if proc is not None:
                    code = proc.poll()
                    if code != 0:
                        print(f"[run] Process exited with code {code}, restarting in 1s...")
                        time.sleep(1)
                print("[run] Starting GUI...")
                proc = subprocess.Popen(
                    [sys.executable, "-X", "utf8", "-c",
                     f"import sys; sys.path.insert(0, {str(ROOT)!r}); "
                     f"from {GUI_ENTRY} import main; main()"],
                    env=env, cwd=str(ROOT),
                )

            # Check for file changes
            time.sleep(1.0)
            curr = get_mtime_map(ROOT)
            changed = [f for f in curr if curr[f] != prev.get(f)]
            if changed:
                print(f"[run] Detected changes in {len(changed)} file(s):")
                for f in changed:
                    print(f"       {f}")
                prev = curr
                # Kill and let loop restart it
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                proc = None
                time.sleep(0.5)  # brief pause so file system settles
    except KeyboardInterrupt:
        print("\n[run] Stopped.")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
