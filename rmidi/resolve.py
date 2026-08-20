"""Resolve API bridge. Precise numeric grading via SetCDL + native color actions."""
import os, sys, time, threading

API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"

# CDL parameter model.  Resolve applies: out = (in * Slope + Offset) ^ Power, then Saturation.
#   Slope  -> Gain    (default 1.0)
#   Offset -> Lift    (default 0.0)
#   Power  -> Gamma   (default 1.0)
DEFAULTS = {"slope": [1.0, 1.0, 1.0], "offset": [0.0, 0.0, 0.0],
            "power": [1.0, 1.0, 1.0], "sat": [1.0]}
LIMITS = {"slope": (0.0, 4.0), "offset": (-0.5, 0.5),
          "power": (0.05, 4.0), "sat": (0.0, 4.0)}


class Resolve:
    def __init__(self, push_hz=40):
        os.environ["RESOLVE_SCRIPT_API"] = API
        os.environ["RESOLVE_SCRIPT_LIB"] = LIB
        sys.path.append(os.path.join(API, "Modules"))
        import DaVinciResolveScript as dvr
        self._dvr = dvr
        self.r = None
        self.node = 1
        self._grades = {}           # clip_key -> {node -> cdl dict}
        self._backed_up = False
        self.autobackup = True
        self._touched = set()       # (clip_key, node) actually modified by the user
        self._dirty = False
        self._backed_up = False
        self.autobackup = True
        self._touched = set()       # (clip_key, node) actually modified by the user
        self._lock = threading.Lock()
        self._period = 1.0 / push_hz
        self.connect()
        threading.Thread(target=self._push_loop, daemon=True).start()

    # ---------- connection ----------
    def connect(self):
        self.r = self._dvr.scriptapp("Resolve")
        return self.r is not None

    def _proj(self):
        if self.r is None and not self.connect():
            return None
        try:
            return self.r.GetProjectManager().GetCurrentProject()
        except Exception:
            self.r = None
            return None

    def timeline(self):
        p = self._proj()
        return p.GetCurrentTimeline() if p else None

    def clip(self):
        t = self.timeline()
        return t.GetCurrentVideoItem() if t else None

    def graph(self):
        c = self.clip()
        return c.GetNodeGraph() if c else None

    def status(self):
        c = self.clip()
        if not c:
            return "no clip"
        return f"{c.GetName()} | node {self.node}/{self.num_nodes()}"

    def num_nodes(self):
        g = self.graph()
        try:
            return g.GetNumNodes() if g else 0
        except Exception:
            return 0

    def live_graph(self, settle=1.2):
        """GetCurrentVideoItem() can hand back a stale graph right after the playhead
        moves - it reports 0 nodes for a clip that has several. Re-read until it
        settles, then fall back to finding the item on the track by start frame."""
        import time as _t
        deadline = _t.time() + settle
        while _t.time() < deadline:
            g = self.graph()
            if g and g.GetNumNodes() > 0:
                return g
            _t.sleep(0.15)
        c, t = self.clip(), self.timeline()
        if c and t:
            for ti in range(1, t.GetTrackCount("video") + 1):
                for it in (t.GetItemListInTrack("video", ti) or []):
                    if it.GetName() == c.GetName() and it.GetStart() == c.GetStart():
                        return it.GetNodeGraph()
        return self.graph()

    # ---------- grade state ----------
    def _key(self):
        c = self.clip()
        if not c:
            return None
        return (c.GetName(), c.GetStart())

    def _cdl(self, key=None):
        key = key or self._key()
        if key is None:
            return None
        per_node = self._grades.setdefault(key, {})
        return per_node.setdefault(self.node, {k: list(v) for k, v in DEFAULTS.items()})

    def nudge(self, param, channel, delta):
        """param in slope/offset/power/sat; channel 0..2 or -1 for master."""
        with self._lock:
            cdl = self._cdl()
            if cdl is None:
                return None
            lo, hi = LIMITS[param]
            idx = [0, 1, 2] if (channel < 0 or param == "sat") else [channel]
            for i in idx:
                if i >= len(cdl[param]):
                    continue
                cdl[param][i] = max(lo, min(hi, cdl[param][i] + delta))
            self._dirty = True
            self._touched.add((self._key(), self.node))
            return [round(v, 4) for v in cdl[param]]

    def set_abs(self, param, channel, value):
        with self._lock:
            cdl = self._cdl()
            if cdl is None:
                return None
            lo, hi = LIMITS[param]
            value = max(lo, min(hi, value))
            idx = [0, 1, 2] if (channel < 0 or param == "sat") else [channel]
            for i in idx:
                if i >= len(cdl[param]):      # "sat" is a single value, not RGB
                    continue
                cdl[param][i] = value
            self._dirty = True
            self._touched.add((self._key(), self.node))
            return value

    def reset_node(self):
        with self._lock:
            key = self._key()
            if key is None:
                return
            self._grades.setdefault(key, {})[self.node] = {k: list(v) for k, v in DEFAULTS.items()}
            self._dirty = True
            self._touched.add((key, self.node))

    def _push_loop(self):
        while True:
            time.sleep(self._period)
            if not self._dirty:
                continue
            with self._lock:
                self._dirty = False
                key = self._key()
                cdl = self._cdl(key)
                node = self.node
            if cdl is None or (key, node) not in self._touched:
                continue
            self._apply(node, cdl)

    def inspect_nodes(self):
        g = self.graph()
        if not g:
            return []
        out = []
        for i in range(1, g.GetNumNodes() + 1):
            out.append({"i": i, "label": g.GetNodeLabel(i),
                        "tools": g.GetToolsInNode(i) or [], "lut": g.GetLUT(i) or ""})
        return out

    def backup_grade(self):
        """SetCDL has no getter, so grab a gallery still before the first write.
        Restore later by right-clicking the still -> Apply Grade."""
        if self._backed_up or not self.autobackup:
            return None
        t = self.timeline()
        if not t:
            return None
        self._backed_up = True
        still = t.GrabStill()
        if still:
            print("  [backup] gallery still grabbed - right-click it -> Apply Grade to restore")
        return still

    def _apply(self, node, cdl):
        c = self.clip()
        if not c:
            return
        self.backup_grade()
        f = lambda v: " ".join(f"{x:.5f}" for x in v)
        try:
            c.SetCDL({"NodeIndex": str(node), "Slope": f(cdl["slope"]),
                      "Offset": f(cdl["offset"]), "Power": f(cdl["power"]),
                      "Saturation": f"{cdl['sat'][0]:.5f}"})
        except Exception:
            self.r = None

    def flush(self):
        with self._lock:
            key, node = self._key(), self.node
            if (key, node) not in self._touched:
                return                       # nothing was touched: leave the node alone
            cdl = self._cdl(key)
        if cdl:
            self._apply(node, cdl)

    # ---------- native actions ----------
    def select_node(self, n):
        self.node = max(1, min(n, max(1, self.num_nodes())))
        return self.node

    def node_step(self, d):
        return self.select_node(self.node + d)

    def toggle_node(self):
        g = self.graph()
        if not g:
            return
        st = getattr(self, "_nodestate", {})
        cur = st.get(self.node, True)
        g.SetNodeEnabled(self.node, not cur)
        st[self.node] = not cur
        self._nodestate = st

    def reset_all_grades(self):
        g = self.graph()
        if g:
            g.ResetAllGrades()
        key = self._key()
        if key in self._grades:
            del self._grades[key]

    # ---------- one-key colour-space stack ----------
    CST_LUTS = ("rmidi/slog3_to_dwg_di.cube", "rmidi/dwg_di_to_rec709_g24.cube")

    def refresh_luts(self):
        p = self._proj()
        if p:
            p.RefreshLUTList()

    def build_cst_stack(self, force=False):
        """Node 1: S-Log3/S-Gamut3.Cine -> DaVinci WG/Intermediate.
           Node 2: DaVinci WG/Intermediate -> Rec.709 Gamma 2.4.
        Nodes are created with Resolve's Add-Serial shortcut (no API exists for that),
        then each gets its transform via SetLUT."""
        import time as _t
        from . import keys
        self.page("color")                       # Add-Serial only works on the Color page
        _t.sleep(0.3)
        g = self.live_graph()
        if g is None:
            print("  ! no clip under the playhead", flush=True)
            return False
        n = g.GetNumNodes()
        busy = [i for i in range(1, n + 1) if g.GetToolsInNode(i)]
        if busy and not force:
            print(f"  ! clip already graded ({n} nodes, {len(busy)} with tools)."
                  f" Hold SHIFT + key to overwrite anyway.", flush=True)
            return False
        self.backup_grade()
        self.refresh_luts()
        for attempt in range(6):                 # grow to two nodes
            g = self.graph()
            if g and g.GetNumNodes() >= 2:
                break
            keys.send("opt+s")
            _t.sleep(0.6)
        g = self.graph()
        if g.GetNumNodes() < 2:
            print(f"  ! could not create 2 nodes (have {g.GetNumNodes()})", flush=True)
            return False
        ok1 = g.SetLUT(1, self.CST_LUTS[0])
        ok2 = g.SetLUT(2, self.CST_LUTS[1])
        print(f"  [cst] node1 S-Log3->DWG/DI {'OK' if ok1 else 'FAIL'} | "
              f"node2 DWG/DI->Rec709 2.4 {'OK' if ok2 else 'FAIL'} | "
              f"{g.GetNumNodes()} nodes", flush=True)
        return ok1 and ok2

    # ---------- master-clip grade presets ----------
    MASTER_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "presets", "masters.json")

    def _load_masters(self):
        import json
        try:
            with open(self.MASTER_DB) as f:
                return json.load(f)
        except Exception:
            return {}

    def set_master(self, slot):
        """Remember the current clip as the grade source for `slot`."""
        import json
        c, t = self.clip(), self.timeline()
        if not (c and t):
            return None
        n = self.num_nodes()
        if n < 1:
            print(f"  ! {c.GetName()} has {n} nodes - refusing to save an empty master.\n"
                  f"    Park the playhead on the clip that HAS the nodes, then rerun.",
                  flush=True)
            return None
        m = self._load_masters()
        m[str(slot)] = {"timeline": t.GetName(), "clip": c.GetName(),
                        "start": c.GetStart(), "nodes": self.num_nodes()}
        os.makedirs(os.path.dirname(self.MASTER_DB), exist_ok=True)
        with open(self.MASTER_DB, "w") as f:
            json.dump(m, f, indent=2)
        return m[str(slot)]

    def _find_item(self, ref):
        """Locate the master clip anywhere in the project, preferring its own timeline."""
        p = self._proj()
        if not p:
            return None
        timelines = []
        for i in range(1, p.GetTimelineCount() + 1):
            tl = p.GetTimelineByIndex(i)
            if tl:
                timelines.append(tl)
        timelines.sort(key=lambda tl: tl.GetName() != ref.get("timeline"))
        for tl in timelines:
            for ti in range(1, tl.GetTrackCount("video") + 1):
                for it in (tl.GetItemListInTrack("video", ti) or []):
                    if it.GetName() == ref.get("clip") and it.GetStart() == ref.get("start"):
                        return it
        for tl in timelines:                       # fall back to name only
            for ti in range(1, tl.GetTrackCount("video") + 1):
                for it in (tl.GetItemListInTrack("video", ti) or []):
                    if it.GetName() == ref.get("clip"):
                        return it
        return None

    def copy_from_master(self, slot):
        """Rebuild the master's whole node stack (OFX + settings) onto the current clip."""
        ref = self._load_masters().get(str(slot))
        if not ref:
            print(f"  ! no master in slot {slot} - set one: ./rmidi.sh set-master --slot {slot}",
                  flush=True)
            return False
        cur = self.clip()
        if not cur:
            return False
        if ref.get("nodes", 0) < 1:
            print(f"  ! master slot {slot} holds an EMPTY grade ({ref['clip']}, 0 nodes)."
                  f" Re-run set-master on the graded clip.", flush=True)
            return False
        src = self._find_item(ref)
        if src is None:
            print(f"  ! master clip {ref['clip']!r} not found in this project", flush=True)
            return False
        if src.GetName() == cur.GetName() and src.GetStart() == cur.GetStart():
            print("  ! current clip IS the master - nothing to do", flush=True)
            return False
        sg = src.GetNodeGraph()
        live_nodes = sg.GetNumNodes() if sg else 0
        if live_nodes < 1:
            print(f"  ! master {ref['clip']} now has 0 nodes - refusing to wipe this clip",
                  flush=True)
            return False
        self.backup_grade()
        ok = src.CopyGrades([cur])
        key = self._key()
        self._grades.pop(key, None)
        self._touched = {t for t in self._touched if t[0] != key}
        print(f"  [master {slot}] {'applied' if ok else 'FAILED'} {ref['clip']}"
              f" -> {self.num_nodes()} nodes", flush=True)
        return ok

    # ---------- .drx grade presets ----------
    def apply_drx(self, path, mode=0):
        """Replace this clip's whole node graph with a saved .drx (nodes + OFX + settings)."""
        g = self.graph()
        if not g:
            return False
        if not os.path.exists(path):
            print(f"  ! no drx at {path} - capture one first: ./rmidi.sh save-drx", flush=True)
            return False
        self.backup_grade()
        ok = g.ApplyGradeFromDRX(path, mode)
        key = self._key()
        self._grades.pop(key, None)                     # our CDL state is stale now
        self._touched = {t for t in self._touched if t[0] != key}
        print(f"  [drx] {'applied' if ok else 'FAILED'} {os.path.basename(path)}"
              f" -> {self.num_nodes()} nodes", flush=True)
        return ok

    def save_drx(self, path):
        """Snapshot the current clip's grade to a .drx file."""
        t, p = self.timeline(), self._proj()
        if not (t and p):
            return False
        still = t.GrabStill()
        if not still:
            return False
        album = p.GetGallery().GetCurrentStillAlbum()
        folder = os.path.dirname(os.path.abspath(path)) or "."
        prefix = os.path.splitext(os.path.basename(path))[0]
        os.makedirs(folder, exist_ok=True)
        ok = album.ExportStills([still], folder, prefix, "drx")
        p.GetGallery().GetCurrentStillAlbum().DeleteStills([still])
        return ok

    def grab_still(self):
        t = self.timeline()
        return t.GrabStill() if t else None

    def add_version(self, name=None):
        c = self.clip()
        if not c:
            return
        n = name or f"v{len(c.GetVersionNameList(0)) + 1}"
        c.AddVersion(n, 0)

    def version_step(self, d):
        c = self.clip()
        if not c:
            return
        names = c.GetVersionNameList(0)
        if not names:
            return
        cur = c.GetCurrentVersion().get("versionName", "")
        i = names.index(cur) if cur in names else 0
        c.LoadVersionByName(names[(i + d) % len(names)], 0)

    def page(self, name):
        if self.r:
            self.r.OpenPage(name)

    def jog(self, frames):
        t = self.timeline()
        if not t:
            return
        tc = t.GetCurrentTimecode()
        try:
            h, m, s, f = [int(x) for x in tc.replace(";", ":").split(":")]
        except Exception:
            return
        fps = float(self.timeline().GetSetting("timelineFrameRate") or 24)
        total = int(round(((h * 3600 + m * 60 + s) * fps))) + f + frames
        total = max(0, total)
        fps_i = int(round(fps))
        nf = total % fps_i
        secs = total // fps_i
        t.SetCurrentTimecode(f"{secs//3600:02d}:{(secs//60)%60:02d}:{secs%60:02d}:{nf:02d}")
