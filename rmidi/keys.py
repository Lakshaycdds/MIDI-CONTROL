"""Keystrokes to DaVinci Resolve via Quartz CGEvent. Used only for what the API cannot do."""
import Quartz, time

# US layout virtual keycodes
VK = {
    'a':0,'s':1,'d':2,'f':3,'h':4,'g':5,'z':6,'x':7,'c':8,'v':9,'b':11,'q':12,'w':13,
    'e':14,'r':15,'y':16,'t':17,'1':18,'2':19,'3':20,'4':21,'6':22,'5':23,'=':24,'9':25,
    '7':26,'-':27,'8':28,'0':29,']':30,'o':31,'u':32,'[':33,'i':34,'p':35,'return':36,
    'l':37,'j':38,"'":39,'k':40,';':41,'\\':42,',':43,'/':44,'n':45,'m':46,'.':47,
    'tab':48,'space':49,'`':50,'delete':51,'escape':53,
    'f1':122,'f2':120,'f3':99,'f4':118,'f5':96,'f6':97,'f7':98,'f8':100,'f9':101,
    'f10':109,'f11':103,'f12':111,
    'left':123,'right':124,'down':125,'up':126,
}
MOD = {
    'cmd': Quartz.kCGEventFlagMaskCommand,
    'shift': Quartz.kCGEventFlagMaskShift,
    'alt': Quartz.kCGEventFlagMaskAlternate,
    'opt': Quartz.kCGEventFlagMaskAlternate,
    'ctrl': Quartz.kCGEventFlagMaskControl,
}


def _pid_of(owner_name):
    for app in Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
        if app.get('kCGWindowOwnerName') == owner_name:
            return app.get('kCGWindowOwnerPID')
    return None


def _pid_of_resolve():
    return _pid_of('DaVinci Resolve')


_BUNDLE_PIDS = {}


def _pid_for_bundle(bundle_id):
    """Resolve a bundle id to a pid, cached; falls back to the frontmost app."""
    import subprocess
    if not bundle_id:
        return None
    pid = _BUNDLE_PIDS.get(bundle_id)
    if pid and _alive(pid):
        return pid
    try:
        out = subprocess.run(["osascript", "-e",
              f'tell application "System Events" to return unix id of '
              f'(first process whose bundle identifier is "{bundle_id}")'],
              capture_output=True, text=True, timeout=3)
        pid = int(out.stdout.strip()) if out.stdout.strip() else None
    except Exception:
        pid = None
    if pid:
        _BUNDLE_PIDS[bundle_id] = pid
    return pid


def _alive(pid):
    import os
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def send(combo: str, bundle_id: str = None):
    """combo like 'cmd+opt+g' or 's' or 'shift+d'.
    bundle_id targets a specific app; None means DaVinci Resolve."""
    parts = [p.strip().lower() for p in combo.split('+')]
    key = parts[-1]
    if key not in VK:
        return False
    flags = 0
    for m in parts[:-1]:
        flags |= MOD.get(m, 0)
    pid = _pid_for_bundle(bundle_id) if bundle_id else _pid_of_resolve()
    code = VK[key]
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, code, down)
        Quartz.CGEventSetFlags(ev, flags)
        if pid:
            Quartz.CGEventPostToPid(pid, ev)
        else:
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.001)
    return True


def has_permission():
    return bool(Quartz.CGPreflightListenEventAccess()) if hasattr(
        Quartz, 'CGPreflightListenEventAccess') else True
