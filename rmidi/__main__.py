import sys, argparse, time, collections, json
import mido
from . import config


def pick_port(sub):
    names = mido.get_input_names()
    hits = [n for n in names if sub.lower() in n.lower() and "DAW" not in n] or \
           [n for n in names if sub.lower() in n.lower()]
    if not hits:
        raise SystemExit(f"no MIDI input matching {sub!r}. have: {names}")
    return hits[0]


def cmd_list(a):
    print("MIDI inputs:")
    for n in mido.get_input_names():
        print("  ", n)
    print("profiles:")
    for p in config.list_profiles():
        print("  ", p)


def cmd_monitor(a):
    port = pick_port(a.port)
    print(f"monitoring {port}  (ctrl-c to stop)")
    ign = {"clock", "active_sensing", "start", "stop", "continue", "songpos"}
    with mido.open_input(port) as p:
        for m in p:
            if m.type in ign:
                continue
            print(m)


def cmd_learn(a):
    """Watch the controller, classify every control, emit a profile skeleton."""
    port = pick_port(a.port)
    ign = {"clock", "active_sensing", "start", "stop", "continue", "songpos"}
    seen = collections.OrderedDict()
    print(f"LEARN on {port} for {a.seconds}s")
    print("Turn every knob end to end, press every pad and button, play a few keys.")
    t0 = time.time()
    with mido.open_input(port) as p:
        while time.time() - t0 < a.seconds:
            for m in p.iter_pending():
                if m.type in ign:
                    continue
                if m.type == "control_change":
                    k = ("cc", m.channel + 1, m.control)
                    v = m.value
                elif m.type in ("note_on", "note_off"):
                    k = ("note", m.channel + 1, m.note)
                    v = m.velocity
                else:
                    continue
                d = seen.setdefault(k, {"n": 0, "vals": set()})
                d["n"] += 1
                d["vals"].add(v)
                if d["n"] == 1:
                    print(f"  new {k[0]} ch{k[1]} #{k[2]}")
            time.sleep(0.002)

    bindings = []
    for (kind, ch, num), d in seen.items():
        vals = d["vals"]
        if kind == "note":
            btype, mode = "note", "button"
        elif vals <= {0, 127} or (len(vals) <= 2 and d["n"] < 6):
            btype, mode = "cc", "button"
        elif vals <= {1, 63, 65, 127}:
            btype, mode = "cc", "rel"
        else:
            btype, mode = "cc", "abs"
        bindings.append({"type": btype, "ch": ch,
                         ("cc" if btype == "cc" else "note"): num,
                         "mode": mode, "action": "TODO",
                         **({"step": 0.004} if mode in ("abs", "rel") else {})})
    cfg = {"device": port, "push_hz": 40, "fine_scale": 0.15, "shift_scale": 5.0,
           "bindings": bindings}
    out = config.save(cfg, a.out)
    print(f"\nwrote {out}  ({len(bindings)} controls). Fill in the TODO actions.")
    print("actions:", " ".join(sorted(available_actions())))


def available_actions():
    from .actions import CDL_PARAMS, KEY_ACTIONS
    names = [f"cdl.{k}" for k in CDL_PARAMS]
    names += list(KEY_ACTIONS)
    names += ["node.select.1", "node.select.2", "node.select.3", "node.select.4",
              "node.next", "node.prev", "node.toggle", "grade.reset_node",
              "grade.reset_all", "still.grab", "version.add", "version.next",
              "version.prev", "page.color", "page.edit", "page.cut", "page.deliver",
              "jog.fwd", "jog.back", "mod.fine", "mod.shift", "mod.clutch", "shuttle"]
    names += [f"grade.master.{i}" for i in range(1, 9)]
    names += [f"grade.drx.{i}" for i in range(1, 5)]
    names += [f"abs.{k}" for k in CDL_PARAMS]
    return names


def cmd_actions(a):
    for n in sorted(available_actions()):
        print(" ", n)


def cmd_set_master(a):
    """Remember the current clip's node stack as a one-key grade preset."""
    from .resolve import Resolve
    r = Resolve()
    if r.r is None:
        raise SystemExit("Resolve not reachable - open it with the clip on the Color page")
    g = r.graph()
    print(f"current clip: {r.status()}")
    for i in range(1, (g.GetNumNodes() if g else 0) + 1):
        print(f"  node {i}: {', '.join(g.GetToolsInNode(i) or []) or 'empty'}")
    ref = r.set_master(a.slot)
    if not ref:
        raise SystemExit("no clip under the playhead")
    print(f"\nslot {a.slot} = {ref['clip']} ({ref['nodes']} nodes) in {ref['timeline']!r}")
    print(f"bind it with action  grade.master.{a.slot}")


def cmd_save_drx(a):
    """Snapshot the current clip's node graph to a .drx preset slot."""
    from .resolve import Resolve
    import os
    cfg = config.load(a.profile)
    slots = cfg.get("drx_slots") or {}
    path = os.path.expanduser(slots.get(str(a.slot), f"presets/slot{a.slot}.drx"))
    r = Resolve()
    if r.r is None:
        raise SystemExit("Resolve not reachable - open it with a clip on the Color page")
    g = r.graph()
    print(f"current clip: {r.status()}")
    for i in range(1, (g.GetNumNodes() if g else 0) + 1):
        print(f"  node {i}: {', '.join(g.GetToolsInNode(i) or []) or 'empty'}")
    ok = r.save_drx(path)
    print(("saved -> " + path) if ok else "FAILED to export .drx")
    if ok:
        print(f"bind it with action  grade.drx.{a.slot}")


def cmd_run(a):
    from .engine import Engine
    cfg = config.load(a.profile)
    port = pick_port(a.port or cfg.get("device", "Launchkey"))
    eng = Engine(cfg, verbose=not a.quiet)
    if eng.resolve.r is None:
        print("!! Resolve not reachable yet - will connect when you open it.")
    try:
        if a.daemon:
            eng.run_forever(a.port or cfg.get("device", "Launchkey"))
        else:
            eng.run(port)
    except KeyboardInterrupt:
        eng.resolve.flush()
        print("\nbye")


def main():
    ap = argparse.ArgumentParser("rmidi", description="MIDI control surface for DaVinci Resolve")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("list", help="show MIDI ports and profiles"); p.set_defaults(f=cmd_list)
    p = sp.add_parser("monitor", help="print raw MIDI"); p.add_argument("--port", default="Launchkey"); p.set_defaults(f=cmd_monitor)
    p = sp.add_parser("learn", help="auto-map every control to a profile skeleton")
    p.add_argument("--port", default="Launchkey"); p.add_argument("--seconds", type=int, default=45)
    p.add_argument("--out", default="learned.yaml"); p.set_defaults(f=cmd_learn)
    p = sp.add_parser("actions", help="list action names"); p.set_defaults(f=cmd_actions)
    p = sp.add_parser("set-master", help="remember current clip's grade as a one-key preset")
    p.add_argument("--slot", type=int, default=1)
    p.set_defaults(f=cmd_set_master)
    p = sp.add_parser("save-drx", help="snapshot current clip's grade to a .drx slot")
    p.add_argument("--slot", type=int, default=1)
    p.add_argument("--profile", default="launchkey-mini-mk4")
    p.set_defaults(f=cmd_save_drx)
    p = sp.add_parser("run", help="run the control surface")
    p.add_argument("profile", nargs="?", default="launchkey-mini-mk4")
    p.add_argument("--port", default=None); p.add_argument("--quiet", action="store_true")
    p.add_argument("--daemon", action="store_true",
                   help="keep running across controller unplug / Resolve restarts")
    p.set_defaults(f=cmd_run)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
