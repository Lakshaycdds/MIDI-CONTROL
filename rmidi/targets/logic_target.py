"""Logic Pro — keyboard shortcuts."""
from .keystroke_base import KeystrokeTarget


class LogicTarget(KeystrokeTarget):
    name = "logic"
    label = "Logic Pro"
    bundle_id = "com.apple.logic10"
    app_hint = "Logic Pro"

    KEYS = {
        "lg.play":         "space",
        "lg.record":       "r",
        "lg.stop":         "return",
        "lg.cycle":        "c",
        "lg.metronome":    "k",
        "lg.next_marker":  "opt+.",
        "lg.prev_marker":  "opt+,",
        "lg.next_bar":     "right",
        "lg.prev_bar":     "left",
        "lg.mute":         "m",
        "lg.solo":         "s",
        "lg.new_track":    "cmd+opt+n",
        "lg.duplicate":    "cmd+d",
        "lg.delete":       "delete",
        "lg.split":        "cmd+t",
        "lg.join":         "cmd+j",
        "lg.loop":         "l",
        "lg.quantize":     "q",
        "lg.mixer":        "x",
        "lg.editor":       "e",
        "lg.piano_roll":   "p",
        "lg.library":      "y",
        "lg.smart_controls": "b",
        "lg.zoom_in":      "cmd+right",
        "lg.zoom_out":     "cmd+left",
        "lg.undo":         "cmd+z",
        "lg.redo":         "cmd+shift+z",
        "lg.save":         "cmd+s",
        "lg.bounce":       "cmd+b",
    }
    NUDGE = {"lg.scrub": ("left", "right", 1.0)}
    DESCRIPTIONS = {
        "lg.play": "Play / pause", "lg.record": "Record", "lg.stop": "Stop / return to start",
        "lg.cycle": "Cycle mode", "lg.metronome": "Metronome",
        "lg.next_marker": "Next marker", "lg.prev_marker": "Previous marker",
        "lg.next_bar": "Forward", "lg.prev_bar": "Rewind",
        "lg.mute": "Mute", "lg.solo": "Solo", "lg.new_track": "New track",
        "lg.duplicate": "Duplicate", "lg.delete": "Delete", "lg.split": "Split at playhead",
        "lg.join": "Join regions", "lg.loop": "Loop region", "lg.quantize": "Quantize",
        "lg.mixer": "Mixer", "lg.editor": "Editor", "lg.piano_roll": "Piano roll",
        "lg.library": "Library", "lg.smart_controls": "Smart controls",
        "lg.zoom_in": "Zoom in", "lg.zoom_out": "Zoom out",
        "lg.undo": "Undo", "lg.redo": "Redo", "lg.save": "Save", "lg.bounce": "Bounce",
        "lg.scrub": "Scrub the playhead",
    }


TARGET = LogicTarget
