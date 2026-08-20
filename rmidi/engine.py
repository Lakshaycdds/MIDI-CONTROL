"""MIDI -> action engine. Handles absolute-pot -> infinite-delta conversion."""
import time, threading, mido
from .leds import Leds
from . import targets as targets_mod

IGNORE = {"clock", "start", "stop", "continue", "active_sensing", "songpos", "reset",
          "aftertouch", "polytouch"}
JUMP_GUARD = 30      # raw ticks; bigger jump = bank switch / garbage, not a turn


def ctrl_id(msg):
    if msg.type == "control_change":
        return ("cc", msg.channel + 1, msg.control)
    if msg.type in ("note_on", "note_off"):
        return ("note", msg.channel + 1, msg.note)
    if msg.type == "pitchwheel":
        return ("pitch", msg.channel + 1, 0)
    return None


class Engine:
    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.target = targets_mod.make(cfg.get("target", "resolve"), cfg)
        self.resolve = getattr(self.target, "api", self.target)   # legacy alias
        if hasattr(self.resolve, "node"):
            self.resolve.node = int(cfg.get("default_node", 1))
        if hasattr(self.resolve, "autobackup"):
            self.resolve.autobackup = bool(cfg.get("autobackup", True))
        self.actions = self.target.build_actions(self)
        self.mods = {"fine": False, "shift": False, "clutch": False}
        self._last = {}          # ctrl_id -> last raw value
        self._at_end = {}
        self._vals = {}          # ctrl_id -> set of raw values seen (auto rel/abs)
        self._unbound_cc = {}    # ch -> set of unbound CC numbers (bank auto-learn)
        _banks = cfg.get("knob_cc_banks") or []
        _base = _banks[0] if _banks else None
        self._knob_banks = list(_banks)
        self._knob_base = _base
        self._knob_bindings = [b for b in cfg.get("bindings", [])
                               if b["type"] == "cc" and _base is not None
                               and _base <= b.get("cc", -1) < _base + 8]
        self.leds = Leds(port_sub=cfg.get("led_port", "Launchkey"),
                         channels=cfg.get("led_channels", (0, 1, 2)),
                         enabled=cfg.get("leds", True))
        self._endstop_active = False
        self._shuttle = 0.0
        threading.Thread(target=self._shuttle_loop, daemon=True).start()
        self.bind = {}
        # The Launchkey's Encoder Mode changes which CC bank the knobs transmit on.
        # Alias every knob across all known banks so the mode no longer matters.
        banks = cfg.get("knob_cc_banks") or []
        base = banks[0] if banks else None
        for b in cfg.get("bindings", []):
            num = b.get("cc", b.get("note", 0))
            self.bind[(b["type"], b.get("ch", 1), num)] = b
            if (b["type"] == "cc" and base is not None
                    and b.get("mode") in ("abs", "rel", "auto")
                    and base <= num < base + 8):
                for alt in banks[1:]:
                    self.bind.setdefault(("cc", b.get("ch", 1), alt + (num - base)), b)
            # pads survive Oct- / Oct+ : accept the same pad shifted by whole octaves
            if b["type"] == "note" and cfg.get("pad_octave_tolerant", True):
                for k in (-36, -24, -12, 12, 24, 36):
                    self.bind.setdefault(("note", b.get("ch", 1), num + k), b)

    def _shuttle_loop(self):
        while True:
            time.sleep(0.08)
            v = self._shuttle
            if abs(v) < 0.08:
                continue
            frames = int(v * abs(v) * self.cfg.get("shuttle_max_fps", 25))
            if frames:
                try:
                    self.resolve.jog(frames)
                except Exception:
                    pass

    def set_mod(self, name, on):
        self.mods[name] = on
        self.sync_leds()

    def sync_leds(self):
        try:
            self.leds.refresh(getattr(self.resolve, "node", 1), self.target.node_count(),
                              self.mods, self._endstop_active)
        except Exception:
            pass

    def _scale(self, b):
        s = float(b.get("step", 0.004))
        if self.mods["fine"]:
            s *= float(self.cfg.get("fine_scale", 0.15))
        if self.mods["shift"]:
            s *= float(self.cfg.get("shift_scale", 5.0))
        if b.get("invert"):
            s = -s
        return s

    def handle(self, msg):
        if msg.type in IGNORE:
            return
        cid = ctrl_id(msg)
        if cid is None:
            return
        b = self.bind.get(cid)
        if b is None:
            if cid[0] == "cc" and self._learn_bank(cid):
                b = self.bind.get(cid)
            if b is None:
                if self.verbose:
                    print(f"  unbound {cid} {getattr(msg,'value',getattr(msg,'velocity',''))}",
                          flush=True)
                return
        act = b["action"]
        if self.mods["shift"] and b.get("shift_action"):
            act = b["shift_action"]
        fn = self.actions.get(act)
        if fn is None:
            print(f"  ! unknown action {act}", flush=True)
            return

        kind = b.get("mode", "auto")
        held = b["action"].startswith("mod.")
        if cid[0] == "note":
            down = 1 if (msg.type == "note_on" and msg.velocity > 0) else 0
            if held or down:
                res = fn(down)
                if isinstance(res, int):
                    self.sync_leds()
                if self.verbose and down:
                    extra = (f" -> node {res}/{self.target.node_count()}"
                             if isinstance(res, int) and self.target.node_count() else "")
                    print(f"  {act}{extra}", flush=True)
            return

        if cid[0] == "pitch":
            self._shuttle = msg.pitch / 8192.0
            if self.verbose and abs(self._shuttle) > 0.9:
                print(f"  shuttle {self._shuttle:+.2f}", flush=True)
            return

        val = msg.value
        if kind == "absolute":
            lo, hi = float(b.get("min", 0.0)), float(b.get("max", 2.0))
            out = fn(lo + (hi - lo) * val / 127.0)
            if self.verbose:
                print(f"  {act:<18} = {out}", flush=True)
            return
        if kind in ("button", "toggle"):
            down = 1 if val >= 64 else 0
            if held or down:
                res = fn(down)
                if isinstance(res, int):
                    self.sync_leds()
                if self.verbose and down:
                    extra = (f" -> node {res}/{self.target.node_count()}"
                             if isinstance(res, int) and self.target.node_count() else "")
                    print(f"  {act}{extra}", flush=True)
            return

        # ---- knob paths ----
        if kind == "rel":
            d = self._rel_delta(val)
        elif kind == "abs":
            d = self._abs_delta(cid, val)
        else:                                    # auto-detect rel vs abs
            seen = self._vals.setdefault(cid, set())
            seen.add(val)
            if len(seen) >= 3 and seen <= {1, 63, 65, 127}:
                d = self._rel_delta(val)
            else:
                d = self._abs_delta(cid, val)
        if d == 0:
            return
        if self.mods["clutch"]:
            return                               # knob muted; user re-centres the pot
        out = fn(d * self._scale(b) / 1.0)
        if self.verbose:
            print(f"  {b['action']:<18} {d:+3d} -> {out}")

    def _learn_bank(self, cid):
        """The Launchkey's Encoder Mode moves the knobs to a different CC bank.
        Collect unbound CCs on the knob channel; once eight of them form a
        contiguous run, adopt it as a new bank and map it onto the knob actions."""
        _, ch, cc = cid
        if not self._knob_bindings or ch != self._knob_bindings[0].get("ch", 1):
            return False
        seen = self._unbound_cc.setdefault(ch, set())
        seen.add(cc)
        for start in sorted(seen):
            if all((start + i) in seen for i in range(8)):
                if start in self._knob_banks:
                    return False
                self._knob_banks.append(start)
                for b in self._knob_bindings:
                    self.bind[("cc", ch, start + (b["cc"] - self._knob_base))] = b
                print(f"  [bank] learned knob CC bank {start}-{start+7} on ch {ch} "
                      f"(add to knob_cc_banks to make it permanent)", flush=True)
                for i in range(8):
                    seen.discard(start + i)
                return True
        return False

    @staticmethod
    def _rel_delta(val):
        if val in (1, 65):  return 1
        if val in (127, 63): return -1
        return val - 64 if 0 < val < 128 else 0

    def _abs_delta(self, cid, val):
        last = self._last.get(cid)
        self._last[cid] = val
        if last is None:
            return 0                              # first touch never jumps
        d = val - last
        if abs(d) > JUMP_GUARD:
            return 0
        if val in (0, 127) and d == 0:
            return 0
        if val in (0, 127) and not self._at_end.get(cid):
            self._at_end[cid] = True
            self._endstop_active = True
            self.sync_leds()
            print(f"  [endstop] {cid[2]} at {val} - hold CLUTCH and re-centre the knob", flush=True)
        elif val not in (0, 127):
            if self._at_end.get(cid):
                self._at_end[cid] = False
                self._endstop_active = any(self._at_end.values())
                self.sync_leds()
        return d

    def run_forever(self, port_sub):
        """Daemon mode: survive the controller being unplugged and Resolve being closed."""
        import mido as _m
        backoff = 1
        while True:
            try:
                names = [n for n in _m.get_input_names()
                         if port_sub.lower() in n.lower() and "DAW" not in n]
                if not names:
                    time.sleep(min(backoff, 15)); backoff = min(backoff * 2, 15)
                    continue
                backoff = 1
                self.run(names[0])
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[reconnect] {type(e).__name__}: {e}", flush=True)
                self._last.clear()
                time.sleep(2)

    def run(self, port_name):
        self.sync_leds()
        print(f"listening: {port_name}")
        print(f"resolve:   {self.resolve.status()}")
        for line in self.target.startup_report():
            print(line, flush=True)

        with mido.open_input(port_name) as port:
            for msg in port:
                try:
                    self.handle(msg)
                except Exception as e:
                    print("  ! ", e, flush=True)
