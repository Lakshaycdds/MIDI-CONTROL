"""Adobe Premiere Pro — keyboard shortcuts only.

Premiere exposes no ExtendScript-over-AppleScript bridge, so numeric Lumetri values
are not reachable. Knobs drive Lumetri sliders by repeated keypresses on the
parameter you have focused, which is coarse; buttons cover editing properly.
"""
from .keystroke_base import KeystrokeTarget


class PremiereTarget(KeystrokeTarget):
    name = "premiere"
    label = "Premiere Pro"
    bundle_id = "com.adobe.PremierePro.26"
    app_hint = "Premiere"

    KEYS = {
        "pr.play":          "space",
        "pr.next_frame":    "right",
        "pr.prev_frame":    "left",
        "pr.next_edit":     "down",
        "pr.prev_edit":     "up",
        "pr.in":            "i",
        "pr.out":           "o",
        "pr.cut":           "cmd+k",
        "pr.cut_all":       "cmd+shift+k",
        "pr.ripple_delete": "shift+delete",
        "pr.delete":        "delete",
        "pr.insert":        ",",
        "pr.overwrite":     ".",
        "pr.mark_clip":     "x",
        "pr.zoom_in":       "=",
        "pr.zoom_out":      "-",
        "pr.zoom_fit":      "\\",
        "pr.undo":          "cmd+z",
        "pr.redo":          "cmd+shift+z",
        "pr.save":          "cmd+s",
        "pr.export":        "cmd+m",
        "pr.lumetri":       "shift+5",
        "pr.effect_controls": "shift+5",
        "pr.link":          "cmd+l",
        "pr.group":         "cmd+g",
        "pr.nest":          "opt+cmd+n",
        "pr.speed":         "cmd+r",
        "pr.razor_tool":    "c",
        "pr.select_tool":   "v",
        "pr.hand_tool":     "h",
    }
    # coarse: repeated arrow presses on whatever slider has focus
    NUDGE = {
        "pr.param":  ("left", "right", 1.0),
        "pr.scrub":  ("left", "right", 1.0),
    }
    DESCRIPTIONS = {
        "pr.play": "Play / pause", "pr.next_frame": "Next frame", "pr.prev_frame": "Previous frame",
        "pr.next_edit": "Next edit point", "pr.prev_edit": "Previous edit point",
        "pr.in": "Mark in", "pr.out": "Mark out", "pr.cut": "Cut at playhead",
        "pr.cut_all": "Cut all tracks", "pr.ripple_delete": "Ripple delete",
        "pr.delete": "Delete", "pr.insert": "Insert", "pr.overwrite": "Overwrite",
        "pr.mark_clip": "Mark clip", "pr.zoom_in": "Zoom in", "pr.zoom_out": "Zoom out",
        "pr.zoom_fit": "Zoom to fit", "pr.undo": "Undo", "pr.redo": "Redo",
        "pr.save": "Save", "pr.export": "Export media", "pr.lumetri": "Lumetri / Effect Controls",
        "pr.link": "Link / unlink", "pr.group": "Group", "pr.nest": "Nest",
        "pr.speed": "Speed / duration", "pr.razor_tool": "Razor tool",
        "pr.select_tool": "Selection tool", "pr.hand_tool": "Hand tool",
        "pr.param": "Nudge the focused parameter (coarse)",
        "pr.scrub": "Scrub the timeline",
    }


TARGET = PremiereTarget
