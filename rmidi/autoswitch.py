"""Follow the frontmost application and swap profile/target to match."""
import threading, time, subprocess

# frontmost bundle id -> profile name
DEFAULT_MAP = {
    "com.blackmagic-design.DaVinciResolve": "launchkey-mini-mk4",
    "com.adobe.AfterEffects.application":   "launchkey-aftereffects",
    "com.adobe.PremierePro.26":             "launchkey-premiere",
    "com.apple.logic10":                    "launchkey-logic",
    "com.apple.mobilelogic":                "launchkey-logic",
}
FALLBACK = "launchkey-macos"


def frontmost_bundle():
    try:
        out = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to return bundle identifier of '
             'first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3)
        return out.stdout.strip()
    except Exception:
        return ""


class AutoSwitcher:
    """Polls the frontmost app; calls on_change(profile_name) when it should switch."""

    def __init__(self, on_change, mapping=None, fallback=FALLBACK, interval=1.0):
        self.on_change = on_change
        self.map = dict(mapping or DEFAULT_MAP)
        self.fallback = fallback
        self.interval = interval
        self.enabled = False
        self.current = None
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def wanted_profile(self):
        return self.map.get(frontmost_bundle(), self.fallback)

    def _loop(self):
        while not self._stop.is_set():
            time.sleep(self.interval)
            if not self.enabled:
                continue
            try:
                want = self.wanted_profile()
                if want and want != self.current:
                    self.current = want
                    self.on_change(want)
            except Exception:
                pass

    def stop(self):
        self._stop.set()
