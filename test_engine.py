"""Offline test: drive the engine with synthetic MIDI against a stub Resolve."""
import sys, types, mido
import rmidi.resolve as R

log = []
class StubResolve:
    def __init__(self, **kw):
        self.r = "stub"; self.node = 1
        self.state = {k: list(v) for k, v in R.DEFAULTS.items()}
    def nudge(self, param, ch, d):
        lo, hi = R.LIMITS[param]
        idx = [0,1,2] if (ch < 0 or param=="sat") else [ch]
        for i in idx:
            if i < len(self.state[param]):
                self.state[param][i] = max(lo, min(hi, self.state[param][i] + d))
        return [round(v,4) for v in self.state[param]]
    def set_abs(self, param, ch, value):
        lo, hi = R.LIMITS[param]
        value = max(lo, min(hi, value))
        idx = [0,1,2] if (ch < 0 or param=="sat") else [ch]
        for i in idx:
            if i >= len(self.state[param]): continue
            self.state[param][i] = value
        return value
    def status(self): return "stub clip | node 1/3"
    def select_node(self, n): self.node = n; log.append(f"node{n}"); return n
    def node_step(self, d): return self.select_node(self.node+d)
    def toggle_node(self): log.append("toggle")
    def reset_node(self): log.append("reset"); self.__init__()
    def reset_all_grades(self): log.append("resetall")
    def grab_still(self): log.append("still")
    def add_version(self): log.append("ver+")
    def version_step(self, d): log.append(f"ver{d:+d}")
    def page(self, n): log.append(f"page:{n}")
    def jog(self, f): log.append(f"jog{f:+d}")
    def flush(self): pass

R.Resolve = StubResolve
import rmidi.keys as K
K.send = lambda c: log.append(f"key:{c}") or True

from rmidi.engine import Engine
from rmidi import config

cfg = config.load("launchkey-mini-mk4")
e = Engine(cfg, verbose=False)
cc = lambda n, v, ch=8: mido.Message('control_change', channel=ch, control=n, value=v)
non = lambda n, ch=1, v=100: mido.Message('note_on', channel=ch, note=n, velocity=v)
nof = lambda n, ch=1: mido.Message('note_off', channel=ch, note=n, velocity=0)

ok = True
def chk(label, got, want):
    global ok
    good = got == want
    ok &= good
    print(f"{'PASS' if good else 'FAIL'}  {label}: got {got} want {want}")

# --- knob: first touch must NOT jump ---
e.handle(cc(23, 100))                       # gain knob, first message
chk("first touch is inert", e.resolve.state["slope"], [1.0,1.0,1.0])

# --- knob delta, step 0.0060 ---
for v in range(101, 111): e.handle(cc(23, v))   # +10 ticks
chk("gain +10 ticks", [round(x,4) for x in e.resolve.state["slope"]], [1.06,1.06,1.06])
for v in range(109, 99, -1): e.handle(cc(23, v))  # back down
chk("gain returns", [round(x,4) for x in e.resolve.state["slope"]], [1.0,1.0,1.0])

# --- fine modifier ---
e.handle(non(36))                            # FINE pad down
for v in range(101, 111): e.handle(cc(23, v))
chk("fine = 0.15x", [round(x,4) for x in e.resolve.state["slope"]], [1.009,1.009,1.009])
e.handle(nof(36))

# --- clutch mutes knobs ---
e.resolve.__init__(); e._last.clear()
e.handle(cc(23, 100))
e.handle(non(37))                            # CLUTCH down
for v in range(101, 121): e.handle(cc(23, v))
chk("clutch mutes", e.resolve.state["slope"], [1.0,1.0,1.0])
e.handle(nof(37))

# --- jump guard (bank switch) ---
e.resolve.__init__(); e._last.clear(); e.handle(cc(23, 10)); e.handle(cc(23, 120))
chk("jump guard", e.resolve.state["slope"], [1.0,1.0,1.0])

# --- per channel ---
e.resolve.__init__(); e._last.clear(); e.handle(cc(25, 50))
for v in range(51, 61): e.handle(cc(25, v))
chk("gain.R only", [round(x,4) for x in e.resolve.state["slope"]], [1.04,1.0,1.0])

# --- limits clamp: 400 clean upward sweeps (clutch-style re-centre between) ---
e.resolve.__init__(); e._last.clear()
for _ in range(400):
    e._last.clear()                       # simulates holding CLUTCH and re-centring
    for v in range(1, 128): e.handle(cc(21, v))
chk("lift clamps at +0.5", round(e.resolve.state["offset"][0], 3), 0.5)

# --- endstop detection fires ---
e.resolve.__init__(); e._last.clear(); e._at_end.clear()
for v in range(120, 128): e.handle(cc(21, v))
chk("endstop flagged at 127", e._at_end.get(("cc", 9, 21)), True)

# --- one-shot pad fires once, not twice ---
log.clear(); e.handle(non(39)); e.handle(nof(39))
chk("still.grab fires once", log, ["still"])

# --- keystroke action ---
log.clear(); e.handle(non(42)); e.handle(nof(42))
chk("node.add_serial -> key", log, ["key:opt+s"])

# --- unbound is ignored ---
log.clear(); e.handle(cc(99, 60)); e.handle(cc(99, 61))
chk("unbound ignored", log, [])

# --- absolute mode on a single-value param must not IndexError (mod strip -> sat) ---
e.resolve.__init__(); e._last.clear()
try:
    e.handle(cc(1, 127, ch=0))        # mod strip, absolute -> abs.sat
    e.handle(cc(1, 0, ch=0))
    chk("abs.sat via mod strip", True, True)
except Exception as ex:
    chk(f"abs.sat via mod strip ({type(ex).__name__})", False, True)

print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
