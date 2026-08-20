"""Pad LED feedback on the Launchkey. Colours are Novation palette velocities."""
import mido

OFF, DIM, WHITE, RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA = (
    0, 1, 3, 5, 9, 13, 21, 37, 45, 53)

# physical grid (Ableton drum-rack order)
TOP = [40, 41, 42, 43, 48, 49, 50, 51]
BOT = [36, 37, 38, 39, 44, 45, 46, 47]

# static colour for each pad that is not state-driven
STATIC = {
    TOP[0]: BLUE,   TOP[1]: BLUE,     # node select < >
    TOP[2]: GREEN,  TOP[3]: GREEN,    # add serial / parallel
    TOP[4]: RED,    TOP[5]: ORANGE,   # delete / enable-disable
    TOP[6]: RED,    TOP[7]: MAGENTA,  # reset node / before-after
    BOT[3]: CYAN,                     # grab still
    BOT[4]: BLUE,   BOT[5]: BLUE,     # prev / next clip
    BOT[6]: YELLOW, BOT[7]: WHITE,    # add version / colour page
}
ACTIVE_NODE = WHITE
IDLE_NODE = OFF        # off, not dim - the lit pad must be unmistakable
MOD_PADS = {"fine": BOT[0], "clutch": BOT[1], "shift": BOT[2]}
MOD_IDLE = DIM
MOD_ON = WHITE


class Leds:
    def __init__(self, port_sub="Launchkey", channels=(0, 1, 2), enabled=True):
        self.channels = tuple(channels)
        self.port = None
        self._cache = {}
        if not enabled:
            return
        try:
            names = [p for p in mido.get_output_names()
                     if port_sub.lower() in p.lower() and "DAW" not in p]
            if names:
                self.port = mido.open_output(names[0])
                # MK3/MK4 DAW-mode handshake so the pads accept LED messages
                self.port.send(mido.Message('note_on', channel=15, note=12, velocity=127))
        except Exception as e:
            print(f"  [leds] unavailable: {e}", flush=True)

    def set(self, note, colour):
        if self.port is None or self._cache.get(note) == colour:
            return
        self._cache[note] = colour
        for ch in self.channels:
            try:
                self.port.send(mido.Message('note_on', channel=ch, note=note, velocity=colour))
            except Exception:
                self.port = None
                return

    def refresh(self, node, num_nodes, mods, endstop=False):
        """node = active grade node; mods = dict of held modifiers."""
        for n, c in STATIC.items():
            self.set(n, c)
        for name, pad in MOD_PADS.items():
            on = mods.get(name)
            if name == "clutch" and endstop and not on:
                self.set(pad, RED)          # a knob is pinned: re-centre it
            else:
                self.set(pad, MOD_ON if on else MOD_IDLE)

    def blackout(self):
        for n in TOP + BOT:
            self.set(n, OFF)

    def close(self):
        if self.port:
            self.blackout()
            try:
                self.port.close()
            except Exception:
                pass
