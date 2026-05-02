"""Windows audio ducking — lower other apps' volume during playback.

Uses pycaw to enumerate active audio sessions, save their volumes,
lower them, and restore after playback ends.

Usage:
    duck = AudioDuck()
    duck.duck()        # lower other sessions
    sd.play(audio, sr) # play your audio
    duck.unduck()      # restore when done (or use duck_for_playback for auto)
"""

import os
import sys
import threading
import time

_available: bool | None = None


def _ensure_pycaw():
    global _available
    if _available is not None:
        return _available
    try:
        import pycaw  # noqa: F401
        _available = True
    except ImportError:
        _available = False
    return _available


class AudioDuck:
    """Singleton that ducks all active audio sessions except the current process."""

    _instance = None
    _lock = threading.Lock()

    DUCK_FACTOR = 0.15   # other apps' volume → 15% of original

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._ready = False
                inst._ducked = False
                inst._saved = {}   # id(session) -> (volume, is_muted)
                inst._sessions = []
                cls._instance = inst
            return cls._instance

    def __init__(self):
        if self._ready:
            return
        self._ready = True
        if not _ensure_pycaw():
            return
        try:
            from pycaw.pycaw import AudioUtilities
            self._get_sessions = lambda: AudioUtilities.GetAllSessions()
            self._com_ok = True
        except Exception as e:
            print(f"[AudioDuck] init failed: {e}")
            self._com_ok = False

    @property
    def available(self) -> bool:
        return getattr(self, "_com_ok", False)

    def _own_pid(self) -> int:
        return os.getpid()

    def _is_our_session(self, session) -> bool:
        """Check if session belongs to our process."""
        try:
            return session.Process.pid == self._own_pid()
        except Exception:
            return False

    def duck(self):
        """Lower volume of all active sessions except our own."""
        if not self.available or self._ducked:
            return
        self._saved.clear()
        self._sessions = []
        try:
            for s in self._get_sessions():
                if self._is_our_session(s):
                    continue
                try:
                    vol = s.SimpleAudioVolume
                    level = vol.GetMasterVolume()
                    muted = vol.GetMute()
                    self._saved[id(s)] = (level, muted)
                    if level > 0:
                        vol.SetMasterVolume(level * self.DUCK_FACTOR, None)
                    self._sessions.append(s)
                except Exception:
                    pass
        except Exception:
            pass
        self._ducked = True

    def unduck(self):
        """Restore all ducked sessions to their original volume."""
        if not self.available or not self._ducked:
            return
        self._ducked = False
        for s in self._sessions:
            info = self._saved.get(id(s))
            if info is None:
                continue
            try:
                vol = s.SimpleAudioVolume
                level, muted = info
                vol.SetMasterVolume(level, None)
                vol.SetMute(muted, None)
            except Exception:
                pass
        self._sessions.clear()
        self._saved.clear()

    def duck_for_playback(self):
        """Duck + auto-unduck when sounddevice playback ends.

        Call this right before sd.play(). A background thread monitors
        the stream and calls unduck() automatically.
        """
        if not self.available:
            return
        self.duck()
        threading.Thread(target=self._monitor_playback, daemon=True).start()

    def _monitor_playback(self):
        """Poll sounddevice stream; unduck when it stops."""
        try:
            import sounddevice as sd
        except ImportError:
            return
        # Wait for a stream to appear (sd.play is async)
        for _ in range(25):  # up to 2.5s
            try:
                stream = sd.get_stream()
                if stream.active:
                    break
            except Exception:
                break
            time.sleep(0.1)
        # Monitor until stream stops
        for _ in range(600):  # up to 60s safety
            try:
                stream = sd.get_stream()
                if not stream.active:
                    break
            except Exception:
                break
            time.sleep(0.1)
        time.sleep(0.2)  # small grace period
        self.unduck()

    def __enter__(self):
        self.duck()
        return self

    def __exit__(self, *a):
        time.sleep(0.2)
        self.unduck()
