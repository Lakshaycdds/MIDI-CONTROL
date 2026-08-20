"""Write one profile per target using the verified Launchkey Mini MK4 device map."""
import os, sys
HEAD = """# {label} — Novation Launchkey Mini MK4 25
# device map verified from hardware: knobs CC 21-28 ch9, pads notes ch2
# (drum-rack order  TOP 40 41 42 43 48 49 50 51 / BOT 36 37 38 39 44 45 46 47)
target: {target}
device: Launchkey Mini MK4 25 MIDI Out
push_hz: 40
fine_scale: 0.15
shift_scale: 5.0
leds: true
led_channels: [0, 1, 2]
pad_octave_tolerant: true
{extra}
bindings:
"""
KNOBS = [21, 22, 23, 24, 25, 26, 27, 28]
TOP = [40, 41, 42, 43, 48, 49, 50, 51]
BOT = [36, 37, 38, 39, 44, 45, 46, 47]


def emit(path, label, target, knobs, top, bot, strips=None, extra="", keys=None):
    L = [HEAD.format(label=label, target=target, extra=extra)]
    L.append("  # knobs\n")
    for cc, (act, step) in zip(KNOBS, knobs):
        L.append(f"  - {{type: cc, ch: 9, cc: {cc}, mode: abs, action: {act}, step: {step}}}\n")
    L.append("\n  # pads - top row\n")
    for n, act in zip(TOP, top):
        L.append(f"  - {{type: note, ch: 2, note: {n}, action: {act}}}\n")
    L.append("\n  # pads - bottom row\n")
    for n, act in zip(BOT, bot):
        L.append(f"  - {{type: note, ch: 2, note: {n}, action: {act}}}\n")
    L.append("\n  # transport buttons\n")
    L.append(f"  - {{type: cc, ch: 16, cc: 102, mode: button, action: {top[0]}}}\n")
    L.append(f"  - {{type: cc, ch: 16, cc: 103, mode: button, action: {top[1]}}}\n")
    if strips:
        L.append("\n  # touch strips\n")
        L.append(f"  - {{type: pitch, ch: 1, action: {strips[0]}}}\n")
        L.append(f"  - {{type: cc, ch: 1, cc: 1, mode: absolute, action: {strips[1]}, "
                 f"min: {strips[2]}, max: {strips[3]}}}\n")
    for line in (keys or []):
        L.append(line)
    open(path, "w").write("".join(L))
    print("wrote", os.path.basename(path))


d = sys.argv[1] if len(sys.argv) > 1 else "rmidi/profiles"

emit(os.path.join(d, "launchkey-aftereffects.yaml"), "After Effects", "aftereffects",
     [("ae.opacity", 0.5), ("ae.rotation", 0.5), ("ae.scale.x", 0.5), ("ae.scale.y", 0.5),
      ("ae.pos.x", 0.5), ("ae.pos.y", 0.5), ("ae.anchor.x", 0.5), ("ae.anchor.y", 0.5)],
     ["ae.prev_frame", "ae.next_frame", "ae.new_solid", "ae.new_null",
      "ae.duplicate", "ae.precompose", "ae.split_layer", "ae.delete"],
     ["mod.fine", "mod.clutch", "mod.shift", "ae.keyframe",
      "ae.work_area_start", "ae.work_area_end", "ae.ram_preview", "ae.save"],
     strips=("shuttle", "ae.opacity", 0, 100))

emit(os.path.join(d, "launchkey-premiere.yaml"), "Premiere Pro", "premiere",
     [("pr.scrub", 1.0), ("pr.param", 1.0), ("pr.scrub", 1.0), ("pr.param", 1.0),
      ("pr.scrub", 1.0), ("pr.param", 1.0), ("pr.scrub", 1.0), ("pr.param", 1.0)],
     ["pr.prev_edit", "pr.next_edit", "pr.in", "pr.out",
      "pr.cut", "pr.ripple_delete", "pr.insert", "pr.overwrite"],
     ["mod.fine", "mod.clutch", "mod.shift", "pr.mark_clip",
      "pr.prev_frame", "pr.next_frame", "pr.lumetri", "pr.save"],
     strips=("shuttle", "pr.param", 0, 100))

emit(os.path.join(d, "launchkey-logic.yaml"), "Logic Pro", "logic",
     [("lg.scrub", 1.0)] * 8,
     ["lg.prev_bar", "lg.next_bar", "lg.record", "lg.cycle",
      "lg.split", "lg.join", "lg.loop", "lg.quantize"],
     ["mod.fine", "mod.clutch", "mod.shift", "lg.metronome",
      "lg.mute", "lg.solo", "lg.mixer", "lg.save"],
     strips=("shuttle", "lg.scrub", 0, 100))

emit(os.path.join(d, "launchkey-macos.yaml"), "macOS", "macos",
     [("mac.mouse.x", 1.0), ("mac.mouse.y", 1.0), ("mac.scroll.v", 1.0), ("mac.scroll.h", 1.0),
      ("mac.mouse.x", 0.25), ("mac.mouse.y", 0.25), ("mac.scroll.v", 0.3), ("mac.scroll.h", 0.3)],
     ["mac.click", "mac.click.double", "mac.click.right", "mac.app.switch",
      "mac.spotlight", "mac.mission", "mac.space.prev", "mac.space.next"],
     ["mod.fine", "mod.clutch", "mod.shift", "mac.esc",
      "mac.vol.down", "mac.vol.up", "mac.play", "mac.screenshot"],
     strips=("shuttle", "mac.scroll.v", -20, 20),
     extra="pointer_speed: 12.0")
