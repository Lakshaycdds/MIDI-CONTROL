"""DaVinci Resolve Studio target."""
import os
from .base import Target
from ..resolve import Resolve
from .. import actions as _actions

DESCRIPTIONS = [
    ("cdl.lift",            "Lift - shadows, all channels"),
    ("cdl.gamma",           "Gamma - midtones"),
    ("cdl.gain",            "Gain - highlights"),
    ("cdl.sat",             "Saturation"),
    ("cdl.lift.r",          "Lift Red"), ("cdl.lift.g", "Lift Green"), ("cdl.lift.b", "Lift Blue"),
    ("cdl.gamma.r",         "Gamma Red"), ("cdl.gamma.g", "Gamma Green"), ("cdl.gamma.b", "Gamma Blue"),
    ("cdl.gain.r",          "Gain Red"), ("cdl.gain.g", "Gain Green"), ("cdl.gain.b", "Gain Blue"),
    ("abs.sat",             "Saturation - absolute (for faders/strips)"),
    ("node.prev",           "Select previous node"),
    ("node.next",           "Select next node"),
    ("node.select.1",       "Select node 1"), ("node.select.2", "Select node 2"),
    ("node.select.3",       "Select node 3"), ("node.select.4", "Select node 4"),
    ("node.add_serial",     "Add serial node"),
    ("node.add_parallel",   "Add parallel node"),
    ("node.add_layer",      "Add layer node"),
    ("node.delete",         "Delete node"),
    ("node.toggle",         "Enable / disable node"),
    ("grade.reset_node",    "Reset this node's grade"),
    ("grade.reset_all",     "Reset every grade on the clip"),
    ("grade.cst_stack",     "Build S-Log3 -> DWG/DI -> Rec.709 2.4 node stack"),
    ("grade.master.1",      "Apply saved grade preset 1"),
    ("grade.master.set.1",  "Save current clip as grade preset 1"),
    ("still.grab",          "Grab still to gallery"),
    ("wipe.still",          "Wipe against the gallery still"),
    ("version.add",         "Add colour version"),
    ("version.next",        "Next colour version"),
    ("version.prev",        "Previous colour version"),
    ("clip.next",           "Next clip"),
    ("clip.prev",           "Previous clip"),
    ("viewer.bypass",       "Before / after"),
    ("page.color",          "Go to Color page"),
    ("page.edit",           "Go to Edit page"),
    ("page.cut",            "Go to Cut page"),
    ("page.deliver",        "Go to Deliver page"),
    ("play",                "Play / pause"),
    ("shuttle",             "Shuttle scrub (pitch strip)"),
    ("jog.fwd",             "Jog forward"), ("jog.back", "Jog back"),
    ("undo",                "Undo"), ("redo", "Redo"),
    ("mod.fine",            "HOLD - fine adjust"),
    ("mod.shift",           "HOLD - coarse adjust"),
    ("mod.clutch",          "HOLD - mute knobs to re-centre a pot"),
]


class ResolveTarget(Target):
    name = "resolve"
    label = "DaVinci Resolve Studio"
    app_hint = "DaVinci Resolve"

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.api = Resolve(push_hz=(cfg or {}).get("push_hz", 40))

    def connect(self):
        return self.api.connect()

    @property
    def connected(self):
        return self.api.r is not None

    def status(self):
        return self.api.status()

    def flush(self):
        self.api.flush()

    def startup_report(self):
        out = []
        nodes = self.api.inspect_nodes()
        for n in nodes:
            risky = " [OFX/LUT present]" if (
                any("OFX" in t for t in n["tools"]) or n["lut"]) else ""
            mark = "  <-- target" if n["i"] == self.api.node else ""
            out.append(f"  node {n['i']}: {', '.join(n['tools']) or 'empty'}{risky}{mark}")
        cur = next((n["tools"] for n in nodes if n["i"] == self.api.node), [])
        if any("OFX" in t for t in cur):
            out.append("  ! target node contains an OFX - CDL lands BEFORE it in that node")
        return out

    def node_count(self):
        return self.api.num_nodes()

    def build_actions(self, engine):
        return _actions.build(engine)

    def describe_actions(self):
        return list(DESCRIPTIONS)


TARGET = ResolveTarget
