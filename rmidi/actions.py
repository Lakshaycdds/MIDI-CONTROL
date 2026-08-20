import os
"""Action registry: name -> callable(engine, value/delta)."""

CDL_PARAMS = {
    # friendly name        param     channel (-1 = master/all)
    "gain":        ("slope",  -1), "gain.r":  ("slope", 0), "gain.g":  ("slope", 1), "gain.b":  ("slope", 2),
    "lift":        ("offset", -1), "lift.r":  ("offset", 0), "lift.g":  ("offset", 1), "lift.b":  ("offset", 2),
    "gamma":       ("power",  -1), "gamma.r": ("power", 0), "gamma.g": ("power", 1), "gamma.b": ("power", 2),
    "sat":         ("sat",    -1),
}

# Resolve default keyboard shortcuts (macOS) for things the scripting API cannot reach.
KEY_ACTIONS = {
    "node.add_serial":      "opt+s",
    "node.add_parallel":    "opt+p",
    "node.add_layer":       "opt+l",
    "node.add_outside":     "opt+o",
    "node.delete":          "delete",
    "clip.next":            "down",
    "clip.prev":            "up",
    "play":                 "space",
    "play.reverse":         "j",
    "play.stop":            "k",
    "play.forward":         "l",
    "wipe.still":           "cmd+w",
    "grade.copy_prev":      "=",
    "grade.copy_next":      "-",
    "qualifier.pick":       "a",
    "window.circle":        "shift+q",
    "viewer.bypass":        "shift+d",
    "viewer.fullscreen":    "cmd+f",
    "undo":                 "cmd+z",
    "redo":                 "cmd+shift+z",
}


def build(engine):
    r = engine.resolve
    from . import keys

    a = {}
    for name, (param, ch) in CDL_PARAMS.items():
        a[f"cdl.{name}"] = (lambda p, c: lambda d: r.nudge(p, c, d))(param, ch)

    for name, (param, ch) in CDL_PARAMS.items():
        a[f"abs.{name}"] = (lambda p, c: lambda v: r.set_abs(p, c, v))(param, ch)

    a.update({
        "node.select.1": lambda d: r.select_node(1),
        "node.select.2": lambda d: r.select_node(2),
        "node.select.3": lambda d: r.select_node(3),
        "node.select.4": lambda d: r.select_node(4),
        "node.next":     lambda d: r.node_step(1),
        "node.prev":     lambda d: r.node_step(-1),
        "node.toggle":   lambda d: r.toggle_node(),
        "grade.reset_node": lambda d: r.reset_node(),
        "grade.reset_all":  lambda d: r.reset_all_grades(),
        "still.grab":    lambda d: r.grab_still(),
        "version.add":   lambda d: r.add_version(),
        "version.next":  lambda d: r.version_step(1),
        "version.prev":  lambda d: r.version_step(-1),
        "page.color":    lambda d: r.page("color"),
        "page.edit":     lambda d: r.page("edit"),
        "page.cut":      lambda d: r.page("cut"),
        "page.deliver":  lambda d: r.page("deliver"),
        "jog.fwd":       lambda d: r.jog(int(d) if d else 1),
        "jog.back":      lambda d: r.jog(-(int(d) if d else 1)),
        "shuttle":       lambda d: None,   # engine drives this from the pitch strip
        "mod.fine":      lambda d: engine.set_mod("fine", d > 0),
        "mod.shift":     lambda d: engine.set_mod("shift", d > 0),
        "mod.clutch":    lambda d: engine.set_mod("clutch", d > 0),
    })
    a["grade.cst_stack"] = lambda d: r.build_cst_stack(False)
    a["grade.cst_stack.force"] = lambda d: r.build_cst_stack(True)

    for slot in range(1, 9):
        a[f"grade.master.{slot}"] = (lambda n: lambda d: r.copy_from_master(n))(slot)
        a[f"grade.master.set.{slot}"] = (lambda n: lambda d: r.set_master(n))(slot)

    for slot, path in (engine.cfg.get("drx_slots") or {}).items():
        full = os.path.expanduser(path)
        if not os.path.isabs(full):
            full = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), full)
        a[f"grade.drx.{slot}"] = (lambda pth: lambda d: r.apply_drx(pth))(full)

    for name, combo in KEY_ACTIONS.items():
        a[name] = (lambda c: lambda d: keys.send(c))(combo)
    return a
