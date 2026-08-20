"""Native macOS GUI for rmidi (AppKit via PyObjC).

Window: target picker, MIDI device picker, profile picker, connection lights,
Start/Stop, live log, and the full mapping table for the loaded profile.
Also installs a menu-bar item so it stays reachable.
"""
import os, sys, threading, traceback, queue
import objc
from AppKit import (NSApplication, NSWindow, NSView, NSTextField, NSButton, NSPopUpButton,
                    NSScrollView, NSTextView, NSColor, NSFont, NSMakeRect, NSApp,
                    NSTableView, NSTableColumn, NSStatusBar, NSMenu, NSMenuItem,
                    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
                    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
                    NSBackingStoreBuffered, NSViewWidthSizable, NSViewHeightSizable,
                    NSBezelStyleRounded, NSApplicationActivationPolicyRegular,
                    NSVariableStatusItemLength, NSScrollerStyleOverlay)
from Foundation import NSObject, NSMakeSize, NSAttributedString, NSTimer

from . import config as cfgmod
from . import targets as targets_mod
from .autoswitch import AutoSwitcher, frontmost_bundle
from . import perms
from . import license as lic
from .license_ui import LicenseWindow

DARK_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.09, 0.10, 0.13, 1.0)
PANEL_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.13, 0.14, 0.18, 1.0)
TEXT = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.88, 0.90, 0.94, 1.0)
DIM = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.55, 0.58, 0.64, 1.0)
OK_C = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.82, 0.45, 1.0)
BAD_C = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.85, 0.35, 0.35, 1.0)


def label(text, x, y, w, h, size=12, color=None, bold=False):
    f = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    f.setStringValue_(text)
    f.setBezeled_(False); f.setDrawsBackground_(False)
    f.setEditable_(False); f.setSelectable_(False)
    f.setTextColor_(color or TEXT)
    f.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
    return f


class MappingSource(NSObject):
    """Table data source for the profile's bindings."""
    def initWithRows_(self, rows):
        self = objc.super(MappingSource, self).init()
        self.rows = rows
        return self

    def numberOfRowsInTableView_(self, tv):
        return len(self.rows)

    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        return self.rows[row].get(str(col.identifier()), "")


class Controller(NSObject):
    # ------------------------------------------------------------------ setup
    def init(self):
        self = objc.super(Controller, self).init()
        self.engine = None
        self.thread = None
        self.logq = queue.Queue()
        self.running = False
        self.lic = lic.check()
        self.licwin = None
        self.build_window()
        self.build_statusbar()
        self.auto = AutoSwitcher(self.autoSwitchTo)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5, self, b"tick:", None, True)
        return self

    @objc.python_method
    def build_window(self):
        rect = NSMakeRect(0, 0, 880, 660)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, NSBackingStoreBuffered, False)
        self.win.setTitle_("rmidi — MIDI control surface")
        self.win.setBackgroundColor_(DARK_BG)
        self.win.center()
        v = self.win.contentView()

        y = 600
        v.addSubview_(label("rmidi", 24, y + 8, 200, 28, 22, TEXT, True))
        v.addSubview_(label("MIDI control surface for creative apps", 24, y - 12, 420, 18, 12, DIM))
        self.path_lbl = label(perms.app_path(), 24, y - 30, 620, 16, 10, DIM)
        v.addSubview_(self.path_lbl)

        self.lic_lbl = label("", 640, y + 14, 214, 18, 11, DIM, True)
        self.lic_lbl.setAlignment_(2)          # right
        v.addSubview_(self.lic_lbl)
        lic_btn = NSButton.alloc().initWithFrame_(NSMakeRect(724, y - 14, 130, 26))
        lic_btn.setTitle_("Licence…"); lic_btn.setBezelStyle_(NSBezelStyleRounded)
        lic_btn.setTarget_(self); lic_btn.setAction_(b"showLicence:")
        v.addSubview_(lic_btn)
        self.refresh_licence()

        # --- pickers ---
        y = 540
        v.addSubview_(label("APPLICATION", 24, y, 160, 16, 10, DIM, True))
        self.target_pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(24, y - 30, 260, 26), False)
        for name, lab in targets_mod.available():
            self.target_pop.addItemWithTitle_(lab)
            self.target_pop.lastItem().setRepresentedObject_(name)
        v.addSubview_(self.target_pop)

        v.addSubview_(label("MIDI DEVICE", 304, y, 160, 16, 10, DIM, True))
        self.dev_pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(304, y - 30, 300, 26), False)
        v.addSubview_(self.dev_pop)

        v.addSubview_(label("PROFILE", 624, y, 160, 16, 10, DIM, True))
        self.prof_pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(624, y - 30, 230, 26), False)
        self.prof_pop.setTarget_(self); self.prof_pop.setAction_(b"profileChanged:")
        v.addSubview_(self.prof_pop)

        # --- status + start ---
        y = 470
        self.dot_midi = label("●  MIDI", 24, y, 130, 20, 13, BAD_C, True)
        self.dot_app = label("●  App", 150, y, 140, 20, 13, BAD_C, True)
        v.addSubview_(self.dot_midi); v.addSubview_(self.dot_app)
        self.dot_perm = label("●  Accessibility", 300, y, 200, 20, 13, BAD_C, True)
        v.addSubview_(self.dot_perm)
        self.status_lbl = label("stopped", 300, y - 20, 420, 18, 11, DIM)
        v.addSubview_(self.status_lbl)

        self.auto_btn = NSButton.alloc().initWithFrame_(NSMakeRect(560, y - 4, 170, 26))
        self.auto_btn.setButtonType_(3)          # NSSwitchButton
        self.auto_btn.setTitle_("Follow active app")
        self.auto_btn.setTarget_(self); self.auto_btn.setAction_(b"toggleAuto:")
        v.addSubview_(self.auto_btn)

        self.start_btn = NSButton.alloc().initWithFrame_(NSMakeRect(730, y - 6, 124, 32))
        self.start_btn.setTitle_("Start"); self.start_btn.setBezelStyle_(NSBezelStyleRounded)
        self.start_btn.setTarget_(self); self.start_btn.setAction_(b"toggleRun:")
        v.addSubview_(self.start_btn)

        # --- mapping table ---
        y = 200
        v.addSubview_(label("MAPPING", 24, 436, 200, 16, 10, DIM, True))
        sv = NSScrollView.alloc().initWithFrame_(NSMakeRect(24, y, 830, 232))
        sv.setHasVerticalScroller_(True); sv.setDrawsBackground_(True)
        sv.setBackgroundColor_(PANEL_BG)
        sv.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.table = NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, 830, 232))
        self.table.setBackgroundColor_(PANEL_BG)
        self.table.setGridColor_(NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.06))
        self.table.setRowHeight_(20)
        for ident, title, w in (("control", "Control", 210), ("kind", "Type", 90),
                                ("action", "Action", 230), ("desc", "Does", 290)):
            c = NSTableColumn.alloc().initWithIdentifier_(ident)
            c.setWidth_(w); c.headerCell().setStringValue_(title)
            c.dataCell().setTextColor_(TEXT)
            c.dataCell().setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
            self.table.addTableColumn_(c)
        sv.setDocumentView_(self.table)
        v.addSubview_(sv)

        # --- log ---
        v.addSubview_(label("LIVE LOG", 24, 168, 200, 16, 10, DIM, True))
        lsv = NSScrollView.alloc().initWithFrame_(NSMakeRect(24, 24, 830, 140))
        lsv.setHasVerticalScroller_(True); lsv.setDrawsBackground_(True)
        lsv.setBackgroundColor_(PANEL_BG)
        lsv.setAutoresizingMask_(NSViewWidthSizable)
        self.logview = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 830, 140))
        self.logview.setBackgroundColor_(PANEL_BG)
        self.logview.setTextColor_(TEXT)
        self.logview.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
        self.logview.setEditable_(False)
        lsv.setDocumentView_(self.logview)
        v.addSubview_(lsv)

        self.refresh_devices()
        self.refresh_profiles()
        self.win.makeKeyAndOrderFront_(None)

    @objc.python_method
    def build_statusbar(self):
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)
        self.item.button().setTitle_("◉")
        m = NSMenu.alloc().init()
        for title, sel in (("Show Window", b"showWindow:"), ("Start / Stop", b"toggleRun:"),
                           ("Quit", b"quitApp:")):
            mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, sel, "")
            mi.setTarget_(self); m.addItem_(mi)
        self.item.setMenu_(m)

    # ------------------------------------------------------------- populate
    @objc.python_method
    def refresh_devices(self):
        import mido
        self.dev_pop.removeAllItems()
        names = [n for n in mido.get_input_names() if "DAW" not in n]
        if not names:
            self.dev_pop.addItemWithTitle_("— no MIDI device —")
        for n in names:
            self.dev_pop.addItemWithTitle_(n)

    @objc.python_method
    def refresh_profiles(self):
        self.prof_pop.removeAllItems()
        for p in cfgmod.list_profiles():
            self.prof_pop.addItemWithTitle_(p.replace(".yaml", ""))
        self.load_mapping()

    @objc.python_method
    def load_mapping(self):
        try:
            name = self.prof_pop.titleOfSelectedItem()
            cfg = cfgmod.load(name)
        except Exception as e:
            self.log(f"profile load failed: {e}")
            return
        self.cfg = cfg
        desc = dict(targets_mod.get_class(cfg.get("target", "resolve"))(cfg).describe_actions()) \
            if False else dict(_safe_descriptions(cfg))
        rows = []
        for b in cfg.get("bindings", []):
            t = b["type"]
            if t == "cc":
                ctrl = f"CC {b.get('cc')}  ch {b.get('ch')}"
            elif t == "note":
                ctrl = f"note {b.get('note')}  ch {b.get('ch')}"
            else:
                ctrl = f"{t}  ch {b.get('ch')}"
            act = b["action"]
            rows.append({"control": ctrl, "kind": b.get("mode", "button" if t == "note" else "auto"),
                         "action": act, "desc": desc.get(act, "")})
            if b.get("shift_action"):
                rows.append({"control": "   + SHIFT", "kind": "", "action": b["shift_action"],
                             "desc": desc.get(b["shift_action"], "")})
        self.src = MappingSource.alloc().initWithRows_(rows)
        self.table.setDataSource_(self.src)
        self.table.reloadData()

    # --------------------------------------------------------------- actions
    def toggleAuto_(self, sender):
        self.auto.enabled = bool(self.auto_btn.state())
        if self.auto.enabled:
            self.auto.current = None          # force an immediate switch
            self.log("follow active app: ON")
        else:
            self.log("follow active app: off")

    @objc.python_method
    def autoSwitchTo(self, profile):
        """Called from the watcher thread when the frontmost app changes."""
        try:
            names = [self.prof_pop.itemTitleAtIndex_(i)
                     for i in range(self.prof_pop.numberOfItems())]
            if profile not in names:
                self.log(f"follow: no profile '{profile}' - staying put")
                return
            was = self.running
            if was:
                self.stop()
            self.prof_pop.selectItemWithTitle_(profile)
            self.load_mapping()
            self.log(f"follow: switched to {profile}")
            if was:
                self.start()
        except Exception:
            import traceback
            self.log(traceback.format_exc())

    def profileChanged_(self, sender):
        self.load_mapping()
        try:
            cfg = cfgmod.load(self.prof_pop.titleOfSelectedItem())
            t = cfg.get("target", "resolve")
            for i in range(self.target_pop.numberOfItems()):
                it = self.target_pop.itemAtIndex_(i)
                if it.representedObject() and str(it.representedObject()) == t:
                    self.target_pop.selectItemAtIndex_(i)
        except Exception:
            pass

    @objc.python_method
    def refresh_licence(self):
        st = self.lic
        self.lic_lbl.setStringValue_(st.short)
        if st.mode == 'licensed':
            self.lic_lbl.setTextColor_(OK_C)
        elif st.mode == 'trial':
            self.lic_lbl.setTextColor_(TEXT if st.days_left > 2 else BAD_C)
        else:
            self.lic_lbl.setTextColor_(BAD_C)

    @objc.python_method
    def licenceActivated(self, st):
        self.lic = st
        self.refresh_licence()
        self.log('licence activated — thank you')

    def showLicence_(self, sender):
        if self.licwin is None:
            self.licwin = LicenseWindow.alloc().initWithCallback_(self.licenceActivated)
        self.licwin.show(self.lic)

    def showWindow_(self, sender):
        self.win.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    def quitApp_(self, sender):
        self.stop()
        NSApp.terminate_(self)

    def toggleRun_(self, sender):
        self.stop() if self.running else self.start()

    @objc.python_method
    def start(self):
        if not self.lic.ok:
            self.lic = lic.check()
            self.refresh_licence()
        if not self.lic.ok:
            self._redirect_stdout()
            self.log(f'!! {self.lic.message}')
            self.log('!! Enter a licence key to start the engine.')
            self.showLicence_(None)
            return
        try:
            from .engine import Engine
            name = self.prof_pop.titleOfSelectedItem()
            cfg = cfgmod.load(name)
            dev = self.dev_pop.titleOfSelectedItem()
            sel = self.target_pop.selectedItem()
            if sel is not None and sel.representedObject():
                cfg["target"] = str(sel.representedObject())
            self._redirect_stdout()
            if not perms.can_post_events():
                perms.request()
                self.log("!! ACCESSIBILITY PERMISSION MISSING")
                self.log("!! macOS is silently dropping every pointer and key event.")
                self.log(f"!! Add this app:  {perms.app_path()}")
                self.log("!! System Settings > Privacy & Security > Accessibility,")
                self.log("!! then REMOVE any old 'rmidi' entry and add it again.")
                perms.open_settings()
            # another rmidi holding the port swallows every message - catch it early
            try:
                import mido as _m
                _probe = _m.open_input(dev)
                _probe.close()
            except Exception as e:
                self.log(f"!! cannot open {dev}: {e}")
                self.log("!! another rmidi (or DAW) already has this port. "
                         "Quit it, or run:  pkill -f 'rmidi run'")
                return
            self.engine = Engine(cfg, verbose=True)
            if not self.engine.target.connected:
                self.log(f"!! {self.engine.target.label} not reachable - "
                         f"open it, then press Stop and Start again")
            self.running = True
            self.thread = threading.Thread(
                target=self._run, args=(dev,), daemon=True)
            self.thread.start()
            self.start_btn.setTitle_("Stop")
            self.log(f"started — {dev}")
        except Exception:
            self.log(traceback.format_exc())

    @objc.python_method
    def _run(self, dev):
        try:
            self.engine.run_forever(dev)
        except Exception:
            self.log(traceback.format_exc())

    @objc.python_method
    def stop(self):
        self.running = False
        if self.engine:
            try:
                self.engine.target.flush()
            except Exception:
                pass
            try:
                self.engine.leds.close()
            except Exception:
                pass
        self.engine = None
        self.start_btn.setTitle_("Start")
        self.log("stopped")

    # ------------------------------------------------------------------ log
    @objc.python_method
    def _redirect_stdout(self):
        gui = self

        class Tee:
            def write(self, s):
                if s.strip():
                    gui.logq.put(s.rstrip())
            def flush(self):
                pass
        sys.stdout = Tee()
        sys.stderr = Tee()

    @objc.python_method
    def log(self, msg):
        self.logq.put(str(msg))

    def tick_(self, timer):
        drained = []
        while not self.logq.empty() and len(drained) < 60:
            drained.append(self.logq.get())
        if drained:
            ts = self.logview.textStorage()
            ts.beginEditing()
            ts.appendAttributedString_(NSAttributedString.alloc().initWithString_(
                "\n".join(drained) + "\n"))
            ts.endEditing()
            self.logview.setTextColor_(TEXT)
            self.logview.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
            self.logview.scrollRangeToVisible_((ts.length(), 0))
        # status lights
        midi_ok = self.running
        app_ok = bool(self.engine and self.engine.target.connected)
        perm_ok = perms.can_post_events()
        self.dot_perm.setTextColor_(OK_C if perm_ok else BAD_C)
        if not perm_ok:
            self.path_lbl.setStringValue_("GRANT ACCESSIBILITY TO THIS EXACT APP:  "
                                          + perms.app_path())
            self.path_lbl.setTextColor_(BAD_C)
        else:
            self.path_lbl.setStringValue_(perms.app_path())
            self.path_lbl.setTextColor_(DIM)
        self.dot_perm.setStringValue_("●  Accessibility" if perm_ok
                                      else "●  Accessibility MISSING")
        self.dot_midi.setTextColor_(OK_C if midi_ok else BAD_C)
        self.dot_app.setTextColor_(OK_C if app_ok else BAD_C)
        self.dot_app.setStringValue_("●  " + (self.engine.target.label.split()[0]
                                              if self.engine else "App"))
        if self.engine:
            try:
                self.status_lbl.setStringValue_(self.engine.target.status())
            except Exception:
                pass
        else:
            self.status_lbl.setStringValue_("stopped")
        self.item.button().setTitle_("◉" if midi_ok else "○")


def _safe_descriptions(cfg):
    try:
        cls = targets_mod.get_class(cfg.get("target", "resolve"))
        return cls.describe_actions(cls)
    except Exception:
        try:
            from .targets.resolve_target import DESCRIPTIONS
            return DESCRIPTIONS
        except Exception:
            return []


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    ctrl = Controller.alloc().init()
    if not ctrl.lic.ok:
        ctrl.showLicence_(None)
    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    main()
