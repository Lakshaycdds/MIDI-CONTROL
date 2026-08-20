"""Licence window — key entry, activation, buy link. Matches the main window's theme."""
import threading, webbrowser
import objc
from AppKit import (NSWindow, NSTextField, NSButton, NSColor, NSFont, NSMakeRect, NSApp,
                    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
                    NSBackingStoreBuffered, NSBezelStyleRounded, NSSecureTextField)
from Foundation import NSObject

from . import license as lic

DARK_BG = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.09, 0.10, 0.13, 1.0)
TEXT    = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.88, 0.90, 0.94, 1.0)
DIM     = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.55, 0.58, 0.64, 1.0)
OK_C    = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.82, 0.45, 1.0)
BAD_C   = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.85, 0.35, 0.35, 1.0)


def _label(text, x, y, w, h, size=12, color=None, bold=False):
    f = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    f.setStringValue_(text); f.setBezeled_(False); f.setDrawsBackground_(False)
    f.setEditable_(False); f.setSelectable_(True)
    f.setTextColor_(color or TEXT)
    f.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
    return f


class LicenseWindow(NSObject):
    """on_done(status) is called after a successful activation."""

    def initWithCallback_(self, cb):
        self = objc.super(LicenseWindow, self).init()
        self.cb = cb
        self.busy = False
        rect = NSMakeRect(0, 0, 520, 268)
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False)
        self.win.setTitle_("rmidi — Licence")
        self.win.setBackgroundColor_(DARK_BG)
        self.win.center()
        self.win.setReleasedWhenClosed_(False)
        v = self.win.contentView()

        v.addSubview_(_label("Activate rmidi", 28, 216, 300, 26, 18, TEXT, True))
        self.sub = _label("", 28, 194, 464, 18, 11, DIM)
        v.addSubview_(self.sub)

        v.addSubview_(_label("LICENCE KEY", 28, 158, 200, 16, 10, DIM, True))
        self.field = NSTextField.alloc().initWithFrame_(NSMakeRect(28, 126, 464, 28))
        self.field.setFont_(NSFont.monospacedSystemFontOfSize_weight_(13, 0))
        self.field.setPlaceholderString_("XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX")
        self.field.setTarget_(self); self.field.setAction_(b"activate:")
        v.addSubview_(self.field)

        self.msg = _label("", 28, 96, 464, 20, 11, DIM)
        v.addSubview_(self.msg)

        self.act_btn = NSButton.alloc().initWithFrame_(NSMakeRect(348, 52, 144, 32))
        self.act_btn.setTitle_("Activate")
        self.act_btn.setBezelStyle_(NSBezelStyleRounded)
        self.act_btn.setKeyEquivalent_("\r")
        self.act_btn.setTarget_(self); self.act_btn.setAction_(b"activate:")
        v.addSubview_(self.act_btn)

        buy = NSButton.alloc().initWithFrame_(NSMakeRect(188, 52, 152, 32))
        buy.setTitle_("Buy a licence")
        buy.setBezelStyle_(NSBezelStyleRounded)
        buy.setTarget_(self); buy.setAction_(b"buy:")
        v.addSubview_(buy)

        self.later_btn = NSButton.alloc().initWithFrame_(NSMakeRect(28, 52, 152, 32))
        self.later_btn.setTitle_("Continue trial")
        self.later_btn.setBezelStyle_(NSBezelStyleRounded)
        self.later_btn.setTarget_(self); self.later_btn.setAction_(b"later:")
        v.addSubview_(self.later_btn)

        v.addSubview_(_label("The key is in your Gumroad receipt e-mail. "
                             f"One licence covers {lic.SEATS} Macs.",
                             28, 22, 464, 18, 10, DIM))
        return self

    # --------------------------------------------------------------- showing
    @objc.python_method
    def show(self, status):
        if status.mode == "trial":
            self.sub.setStringValue_(
                f"Trial — {status.days_left} day"
                f"{'s' if status.days_left != 1 else ''} left. Every feature is unlocked.")
            self.later_btn.setTitle_("Continue trial")
            self.later_btn.setEnabled_(True)
        elif status.mode == "licensed":
            self.sub.setStringValue_("This Mac is licensed. Thank you.")
            self.later_btn.setTitle_("Close")
            self.later_btn.setEnabled_(True)
        else:
            self.sub.setStringValue_("Your trial has ended. Enter a licence key to keep going.")
            self.later_btn.setTitle_("Quit")
            self.later_btn.setEnabled_(True)
        self.msg.setStringValue_("")
        self.expired = (status.mode not in ("trial", "licensed"))
        self.win.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    # --------------------------------------------------------------- actions
    def buy_(self, sender):
        webbrowser.open(lic.STORE_URL)

    def later_(self, sender):
        if getattr(self, "expired", False):
            NSApp.terminate_(self)
        else:
            self.win.orderOut_(None)

    def activate_(self, sender):
        if self.busy:
            return
        key = str(self.field.stringValue()).strip()
        if not key:
            self._say("Enter your licence key.", False)
            return
        self.busy = True
        self.act_btn.setEnabled_(False)
        self._say("Checking with Gumroad…", None)
        threading.Thread(target=self._work, args=(key,), daemon=True).start()

    @objc.python_method
    def _work(self, key):
        st = lic.activate(key)
        self.performSelectorOnMainThread_withObject_waitUntilDone_(b"_done:", st, False)

    def _done_(self, st):
        self.busy = False
        self.act_btn.setEnabled_(True)
        self._say(st.message, st.ok)
        if st.ok:
            self.sub.setStringValue_("This Mac is licensed. Thank you.")
            self.later_btn.setTitle_("Close")
            self.expired = False
            if self.cb:
                self.cb(st)

    @objc.python_method
    def _say(self, text, good):
        self.msg.setStringValue_(text or "")
        self.msg.setTextColor_(DIM if good is None else (OK_C if good else BAD_C))
