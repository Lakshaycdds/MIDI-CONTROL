"""Every profile must construct an Engine AND survive the startup path that run() takes.
This is the check that would have caught the MacTarget.inspect_nodes crash."""
import sys, io, traceback
sys.path.insert(0, '.')
from rmidi import config
from rmidi.engine import Engine

ok = True
for prof in config.list_profiles():
    name = prof.replace(".yaml", "")
    try:
        cfg = config.load(name)
        e = Engine(cfg, verbose=False)
        # exactly what run() does before opening the MIDI port
        e.target.status()
        lines = e.target.startup_report()
        assert isinstance(lines, list)
        e.target.node_count()
        e.sync_leds()
        missing = [b["action"] for b in cfg["bindings"] if b["action"] not in e.actions]
        missing += [b["shift_action"] for b in cfg["bindings"]
                    if b.get("shift_action") and b["shift_action"] not in e.actions]
        # fire every bound action with a harmless zero delta, catching only real crashes
        crashed = []
        for b in cfg["bindings"]:
            fn = e.actions.get(b["action"])
            act = b["action"]
            inert = act.startswith(("cdl.", "abs.", "mod.")) or act in (
                "node.select.1", "node.select.2", "node.select.3", "node.select.4",
                "node.prev", "node.next", "shuttle")
            if fn is None or not inert:
                continue          # never drive the host app from a test
            try:
                fn(0)
            except Exception as ex:
                crashed.append(f"{b['action']}: {type(ex).__name__}")
        status = "OK" if not missing and not crashed else f"MISSING={missing} CRASH={crashed}"
        ok &= (status == "OK")
        print(f"  {name:<26} target={cfg.get('target'):<13} {status}")
    except Exception:
        ok = False
        print(f"  {name:<26} FAILED")
        traceback.print_exc()
print("\nRESULT:", "ALL TARGETS START CLEANLY" if ok else "FAILURES")
sys.exit(0 if ok else 1)
