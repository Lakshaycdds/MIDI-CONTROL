"""Adobe After Effects — ExtendScript over AppleScript (DoScript), plus shortcuts.

DoScript gives real numeric control of the selected layer's properties, so knobs
are precise rather than repeated keypresses.
"""
import subprocess
from .keystroke_base import KeystrokeTarget

APP = "Adobe After Effects 2026"

# ExtendScript: nudge a transform property on every selected layer by `d`.
JSX_NUDGE = """
(function(){
  var c = app.project.activeItem;
  if (!(c && c instanceof CompItem)) return "no comp";
  var ls = c.selectedLayers; if (!ls.length) return "no layer";
  app.beginUndoGroup("rmidi %(prop)s");
  for (var i=0;i<ls.length;i++){
    var p = ls[i].property("ADBE Transform Group").property("%(prop)s");
    if (!p) continue;
    var v = p.value;
    if (v instanceof Array) { var n=[]; for (var k=0;k<v.length;k++) n[k]=v[k]; n[%(idx)d]+=%(d)f; p.setValue(n); }
    else p.setValue(v + %(d)f);
  }
  app.endUndoGroup();
  return "ok";
})()
"""

PROPS = {
    "ae.opacity":   ("ADBE Opacity",   0, 1.0),
    "ae.rotation":  ("ADBE Rotate Z",  0, 1.0),
    "ae.scale.x":   ("ADBE Scale",     0, 1.0),
    "ae.scale.y":   ("ADBE Scale",     1, 1.0),
    "ae.pos.x":     ("ADBE Position",  0, 4.0),
    "ae.pos.y":     ("ADBE Position",  1, 4.0),
    "ae.anchor.x":  ("ADBE Anchor Point", 0, 4.0),
    "ae.anchor.y":  ("ADBE Anchor Point", 1, 4.0),
}


class AfterEffectsTarget(KeystrokeTarget):
    name = "aftereffects"
    label = "After Effects"
    bundle_id = "com.adobe.AfterEffects.application"
    app_hint = "After Effects"

    KEYS = {
        "ae.play":            "space",
        "ae.ram_preview":     "0",
        "ae.next_frame":      "right",
        "ae.prev_frame":      "left",
        "ae.work_area_start": "b",
        "ae.work_area_end":   "n",
        "ae.new_solid":       "cmd+y",
        "ae.new_null":        "cmd+opt+shift+y",
        "ae.precompose":      "cmd+shift+c",
        "ae.duplicate":       "cmd+d",
        "ae.delete":          "delete",
        "ae.split_layer":     "cmd+shift+d",
        "ae.toggle_solo":     "s",
        "ae.keyframe":        "u",
        "ae.fit_comp":        "shift+/",
        "ae.snapshot":        "f5",
        "ae.undo":            "cmd+z",
        "ae.redo":            "cmd+shift+z",
        "ae.save":            "cmd+s",
        "ae.add_to_queue":    "cmd+m",
    }
    DESCRIPTIONS = {
        "ae.opacity": "Opacity of selected layers", "ae.rotation": "Rotation",
        "ae.scale.x": "Scale X", "ae.scale.y": "Scale Y",
        "ae.pos.x": "Position X", "ae.pos.y": "Position Y",
        "ae.anchor.x": "Anchor X", "ae.anchor.y": "Anchor Y",
        "ae.play": "Play / pause", "ae.ram_preview": "RAM preview",
        "ae.next_frame": "Next frame", "ae.prev_frame": "Previous frame",
        "ae.work_area_start": "Work area start", "ae.work_area_end": "Work area end",
        "ae.new_solid": "New solid", "ae.new_null": "New null",
        "ae.precompose": "Pre-compose", "ae.duplicate": "Duplicate layer",
        "ae.delete": "Delete layer", "ae.split_layer": "Split layer",
        "ae.toggle_solo": "Show scale property", "ae.keyframe": "Show keyframed properties",
        "ae.fit_comp": "Fit comp to window", "ae.snapshot": "Snapshot",
        "ae.undo": "Undo", "ae.redo": "Redo", "ae.save": "Save",
        "ae.add_to_queue": "Add to render queue",
    }

    def jsx(self, script):
        try:
            out = subprocess.run(
                ["osascript", "-e", f'tell application "{APP}" to DoScript {_q(script)}'],
                capture_output=True, text=True, timeout=6)
            return (out.stdout or out.stderr).strip()
        except Exception as e:
            return f"jsx error: {e}"

    @property
    def connected(self):
        return self._pid() is not None

    def status(self):
        if not self.connected:
            return "After Effects not running"
        r = self.jsx('(function(){var c=app.project.activeItem;'
                     'return (c&&c instanceof CompItem)?(c.name+" | "+c.selectedLayers.length+" sel"):"no comp";})()')
        return r or "After Effects"

    def prop_nudge(self, action, d):
        prop, idx, scale = PROPS[action]
        return self.jsx(JSX_NUDGE % {"prop": prop, "idx": idx, "d": d * scale})

    def build_actions(self, engine):
        a = super().build_actions(engine)
        for name in PROPS:
            a[name] = (lambda n: lambda d: self.prop_nudge(n, d))(name)
        return a

    def describe_actions(self):
        return [(n, self.DESCRIPTIONS.get(n, n)) for n in PROPS] + super().describe_actions()


def _q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


TARGET = AfterEffectsTarget
