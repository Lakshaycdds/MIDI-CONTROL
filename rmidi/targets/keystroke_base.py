"""Base for applications driven by keyboard shortcuts.

Subclasses declare KEYS (action -> shortcut) and optionally NUDGE
(action -> (key_down, key_up, units_per_step)) so a knob can drive a value by
sending repeated keypresses proportional to how far it was turned.
"""
import subprocess
from .base import Target
from .. import keys as keysmod


class KeystrokeTarget(Target):
    bundle_id = ""
    KEYS = {}
    NUDGE = {}
    DESCRIPTIONS = {}

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self._accum = {}

    # --- lifecycle -------------------------------------------------------
    def connect(self):
        return self.connected

    @property
    def connected(self):
        return self._pid() is not None

    def _pid(self):
        try:
            out = subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to return unix id of '
                 f'(first process whose bundle identifier is "{self.bundle_id}")'],
                capture_output=True, text=True, timeout=3)
            return int(out.stdout.strip()) if out.stdout.strip() else None
        except Exception:
            return None

    def status(self):
        return f"{self.label} running" if self.connected else f"{self.label} not running"

    def send(self, combo):
        return keysmod.send(combo, bundle_id=self.bundle_id)

    # --- knob -> repeated keypresses -------------------------------------
    def nudge(self, action, delta):
        down, up, per = self.NUDGE[action]
        acc = self._accum.get(action, 0.0) + delta * per
        n = int(acc)
        self._accum[action] = acc - n
        if n == 0:
            return None
        combo = up if n > 0 else down
        for _ in range(min(abs(n), 40)):
            self.send(combo)
        return f"{action} {n:+d}"

    # --- actions ---------------------------------------------------------
    def build_actions(self, engine):
        a = {}
        for name, combo in self.KEYS.items():
            a[name] = (lambda c: lambda d: self.send(c))(combo)
        for name in self.NUDGE:
            a[name] = (lambda n: lambda d: self.nudge(n, d))(name)
        a["mod.fine"] = lambda d: engine.set_mod("fine", d > 0)
        a["mod.shift"] = lambda d: engine.set_mod("shift", d > 0)
        a["mod.clutch"] = lambda d: engine.set_mod("clutch", d > 0)
        a["shuttle"] = lambda d: None
        return a

    def describe_actions(self):
        out = []
        for name in list(self.NUDGE) + list(self.KEYS):
            out.append((name, self.DESCRIPTIONS.get(name, name.replace(".", " "))))
        out += [("mod.fine", "HOLD - fine adjust"), ("mod.shift", "HOLD - coarse adjust"),
                ("mod.clutch", "HOLD - mute knobs to re-centre a pot")]
        return out
