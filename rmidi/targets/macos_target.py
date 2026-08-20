"""Control macOS itself: pointer, scrolling, volume, media, windows, spaces.

Knobs move the pointer and scroll; pads click, switch apps and drive the system.
Nothing here needs a specific application to be running.
"""
import subprocess
import Quartz
from .base import Target

# Apple HID keys for media / volume
NX_SOUND_UP, NX_SOUND_DOWN, NX_MUTE = 0, 1, 7
NX_PLAY, NX_NEXT, NX_PREV = 16, 17, 18
NX_BRIGHT_UP, NX_BRIGHT_DOWN = 2, 3


def _hid(key, down=True):
    ev = Quartz.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
        14, (0, 0), 0xa00 if down else 0xb00, 0, 0, None, 8,
        (key << 16) | ((0xa if down else 0xb) << 8), -1)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev.CGEvent())


def media(key):
    _hid(key, True); _hid(key, False)


def mouse_pos():
    return Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))


def _desktop_bounds():
    """Union of every active display, so the pointer is not trapped on one screen."""
    err, ids, n = Quartz.CGGetActiveDisplayList(16, None, None)
    if err or not n:
        b = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
        return b.origin.x, b.origin.y, b.origin.x + b.size.width, b.origin.y + b.size.height
    x0 = y0 = float("inf"); x1 = y1 = float("-inf")
    for d in ids[:n]:
        b = Quartz.CGDisplayBounds(d)
        x0 = min(x0, b.origin.x); y0 = min(y0, b.origin.y)
        x1 = max(x1, b.origin.x + b.size.width)
        y1 = max(y1, b.origin.y + b.size.height)
    return x0, y0, x1, y1


def mouse_move(dx, dy):
    p = mouse_pos()
    x0, y0, x1, y1 = _desktop_bounds()
    x = max(x0, min(p.x + dx, x1 - 1))
    y = max(y0, min(p.y + dy, y1 - 1))
    ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, (x, y), 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    return f"{int(x)},{int(y)}"


def click(button="left", double=False):
    p = mouse_pos()
    if button == "left":
        d, u, b = Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft
    else:
        d, u, b = Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight
    for i in range(2 if double else 1):
        for kind in (d, u):
            ev = Quartz.CGEventCreateMouseEvent(None, kind, p, b)
            if double:
                Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, i + 1)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    return button + (" x2" if double else "")


def scroll(dy=0, dx=0):
    ev = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitPixel, 2,
                                              int(dy), int(dx))
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def osa(script):
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=4)
    except Exception:
        pass


class MacTarget(Target):
    name = "macos"
    label = "macOS (mouse & system)"
    app_hint = ""

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self._acc = {}
        self.speed = float((cfg or {}).get("pointer_speed", 12.0))

    def connect(self):
        return True

    @property
    def connected(self):
        return True

    def status(self):
        p = mouse_pos()
        return f"pointer {int(p.x)},{int(p.y)}"

    def _accum(self, key, delta, scale):
        acc = self._acc.get(key, 0.0) + delta * scale
        n = int(acc)
        self._acc[key] = acc - n
        return n

    def build_actions(self, engine):
        from .. import keys as k
        a = {
            "mac.mouse.x":   lambda d: mouse_move(d * self.speed, 0),
            "mac.mouse.y":   lambda d: mouse_move(0, -d * self.speed),
            "mac.scroll.v":  lambda d: scroll(dy=d * self.speed),
            "mac.scroll.h":  lambda d: scroll(dx=d * self.speed),
            "mac.click":            lambda d: click("left"),
            "mac.click.double":     lambda d: click("left", True),
            "mac.click.right":      lambda d: click("right"),
            "mac.vol.up":    lambda d: media(NX_SOUND_UP),
            "mac.vol.down":  lambda d: media(NX_SOUND_DOWN),
            "mac.vol.mute":  lambda d: media(NX_MUTE),
            "mac.play":      lambda d: media(NX_PLAY),
            "mac.track.next": lambda d: media(NX_NEXT),
            "mac.track.prev": lambda d: media(NX_PREV),
            "mac.bright.up":  lambda d: media(NX_BRIGHT_UP),
            "mac.bright.down": lambda d: media(NX_BRIGHT_DOWN),
            "mac.app.switch": lambda d: k.send("cmd+tab"),
            "mac.spotlight":  lambda d: k.send("cmd+space"),
            "mac.mission":    lambda d: osa('tell application "Mission Control" to launch'),
            "mac.space.next": lambda d: k.send("ctrl+right"),
            "mac.space.prev": lambda d: k.send("ctrl+left"),
            "mac.window.close": lambda d: k.send("cmd+w"),
            "mac.window.min":   lambda d: k.send("cmd+m"),
            "mac.fullscreen":   lambda d: k.send("ctrl+cmd+f"),
            "mac.copy":  lambda d: k.send("cmd+c"),
            "mac.paste": lambda d: k.send("cmd+v"),
            "mac.cut":   lambda d: k.send("cmd+x"),
            "mac.undo":  lambda d: k.send("cmd+z"),
            "mac.redo":  lambda d: k.send("cmd+shift+z"),
            "mac.save":  lambda d: k.send("cmd+s"),
            "mac.tab":   lambda d: k.send("tab"),
            "mac.enter": lambda d: k.send("return"),
            "mac.esc":   lambda d: k.send("escape"),
            "mac.delete": lambda d: k.send("delete"),
            "mac.arrow.up":    lambda d: k.send("up"),
            "mac.arrow.down":  lambda d: k.send("down"),
            "mac.arrow.left":  lambda d: k.send("left"),
            "mac.arrow.right": lambda d: k.send("right"),
            "mac.screenshot":  lambda d: k.send("cmd+shift+4"),
            "mac.lock":        lambda d: k.send("ctrl+cmd+q"),
            "mod.fine":   lambda d: engine.set_mod("fine", d > 0),
            "mod.shift":  lambda d: engine.set_mod("shift", d > 0),
            "mod.clutch": lambda d: engine.set_mod("clutch", d > 0),
            "shuttle":    lambda d: None,
        }
        return a

    def describe_actions(self):
        return [
            ("mac.mouse.x", "Move pointer horizontally"),
            ("mac.mouse.y", "Move pointer vertically"),
            ("mac.scroll.v", "Scroll up / down"),
            ("mac.scroll.h", "Scroll left / right"),
            ("mac.click", "Left click"), ("mac.click.double", "Double click"),
            ("mac.click.right", "Right click"),
            ("mac.vol.up", "Volume up"), ("mac.vol.down", "Volume down"),
            ("mac.vol.mute", "Mute"), ("mac.play", "Play / pause media"),
            ("mac.track.next", "Next track"), ("mac.track.prev", "Previous track"),
            ("mac.bright.up", "Brightness up"), ("mac.bright.down", "Brightness down"),
            ("mac.app.switch", "Switch app (cmd-tab)"), ("mac.spotlight", "Spotlight"),
            ("mac.mission", "Mission Control"),
            ("mac.space.next", "Next desktop"), ("mac.space.prev", "Previous desktop"),
            ("mac.window.close", "Close window"), ("mac.window.min", "Minimise"),
            ("mac.fullscreen", "Full screen"),
            ("mac.copy", "Copy"), ("mac.paste", "Paste"), ("mac.cut", "Cut"),
            ("mac.undo", "Undo"), ("mac.redo", "Redo"), ("mac.save", "Save"),
            ("mac.tab", "Tab"), ("mac.enter", "Return"), ("mac.esc", "Escape"),
            ("mac.delete", "Delete"),
            ("mac.arrow.up", "Arrow up"), ("mac.arrow.down", "Arrow down"),
            ("mac.arrow.left", "Arrow left"), ("mac.arrow.right", "Arrow right"),
            ("mac.screenshot", "Screenshot selection"), ("mac.lock", "Lock screen"),
            ("mod.fine", "HOLD - fine / slow pointer"),
            ("mod.shift", "HOLD - fast pointer"),
            ("mod.clutch", "HOLD - mute knobs"),
        ]


TARGET = MacTarget
