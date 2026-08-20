"""Accessibility / post-event permission.

Synthetic pointer and key events are refused silently without this, which looks
exactly like 'the app runs but nothing happens'. Check it, ask for it, and say so.
"""
import subprocess
import Quartz

PANE = ("x-apple.systempreferences:com.apple.preference.security"
        "?Privacy_Accessibility")


def can_post_events():
    try:
        return bool(Quartz.CGPreflightPostEventAccess())
    except Exception:
        return True          # older macOS: no gate


def request():
    """Ask macOS for it. Shows the system prompt the first time and adds the app
    to the Accessibility list so the user only has to flip the switch."""
    try:
        return bool(Quartz.CGRequestPostEventAccess())
    except Exception:
        return True


def open_settings():
    subprocess.run(["open", PANE], capture_output=True)


def app_path():
    import sys, os
    p = sys.executable
    if ".app/Contents/MacOS/" in p:
        return p.split(".app/Contents/MacOS/")[0] + ".app"
    return p
