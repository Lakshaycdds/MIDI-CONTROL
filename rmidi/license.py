"""Licence checking for rmidi — Gumroad licence keys, no server of our own.

Flow
----
first launch          -> TRIAL_DAYS free, full features
after trial           -> app runs but the engine refuses to start until a key is entered
key entered           -> POST api.gumroad.com/v2/licenses/verify (increments the use count)
                         success -> stored in Application Support, bound to this machine
later launches        -> local file trusted for RECHECK_DAYS, then re-verified online
                         (silently, without incrementing) so refunds/chargebacks revoke
offline               -> keeps working for GRACE_DAYS past the last successful check

Only the standard library is used, so nothing new has to be bundled by PyInstaller.
urllib is tried first; if the frozen app has no usable CA bundle it falls back to
/usr/bin/curl, which always has the system roots.
"""
import os, json, time, ssl, hashlib, subprocess, urllib.request, urllib.parse, urllib.error

# --------------------------------------------------------------------- config
# Set this to the Gumroad product id once the product exists.
# Gumroad -> Products -> your product -> "..." menu -> ID.  Overridable for testing.
GUMROAD_PRODUCT_ID = os.environ.get("RMIDI_PRODUCT_ID", "PASTE_GUMROAD_PRODUCT_ID_HERE")

VERIFY_URL   = "https://api.gumroad.com/v2/licenses/verify"
TRIAL_DAYS   = 7      # full-feature free trial
SEATS        = 2      # machines one licence may activate
RECHECK_DAYS = 7      # re-verify online this often
GRACE_DAYS   = 30     # keep running offline this long after the last good check
TIMEOUT      = 12

SUPPORT_DIR  = os.path.expanduser("~/Library/Application Support/rmidi")
LIC_FILE     = os.path.join(SUPPORT_DIR, "license.json")
TRIAL_FILE   = os.path.join(SUPPORT_DIR, "trial.json")

STORE_URL    = "https://rmidi.app"   # where the Buy button lives


# ------------------------------------------------------------------- machine
def machine_id():
    """Stable per-Mac id: the IOPlatformUUID, hashed so we never store the raw one."""
    raw = ""
    try:
        out = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if "IOPlatformUUID" in line:
                raw = line.split('"')[-2]
                break
    except Exception:
        pass
    if not raw:                                  # last resort, still stable per user
        raw = os.path.expanduser("~") + os.uname().nodename
    return hashlib.sha256(("rmidi:" + raw).encode()).hexdigest()[:32]


# ----------------------------------------------------------------- disk state
def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _write(path, data):
    os.makedirs(SUPPORT_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _sign(d):
    """Cheap tamper check so a hand-edited json does not silently unlock the app.
    This is a speed bump, not security — a determined user owns the binary anyway."""
    blob = json.dumps({k: d[k] for k in sorted(d) if k != "sig"}, sort_keys=True)
    return hashlib.sha256((blob + machine_id()).encode()).hexdigest()[:24]


def _valid(d):
    return bool(d) and d.get("sig") == _sign(d)


# --------------------------------------------------------------------- trial
def trial_started():
    d = _read(TRIAL_FILE)
    if _valid(d):
        return float(d.get("start", 0))
    d = {"start": time.time(), "machine": machine_id()}
    d["sig"] = _sign(d)
    _write(TRIAL_FILE, d)
    return d["start"]


def trial_days_left():
    used = (time.time() - trial_started()) / 86400.0
    return max(0, int(round(TRIAL_DAYS - used + 0.49)))


# ---------------------------------------------------------------- gumroad API
def _post(url, fields):
    body = urllib.parse.urlencode(fields).encode()
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"User-Agent": "rmidi/1.2",
                                              "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:            # 404 = bad key, body is still json
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"success": False, "message": f"HTTP {e.code}"}
    except (urllib.error.URLError, ssl.SSLError, OSError):
        pass                                       # fall through to curl

    try:                                           # frozen-app CA fallback
        out = subprocess.run(
            ["/usr/bin/curl", "-s", "-m", str(TIMEOUT), "-X", "POST", url,
             "--data", urllib.parse.urlencode(fields)],
            capture_output=True, text=True, timeout=TIMEOUT + 5).stdout
        return json.loads(out)
    except Exception as e:
        return {"success": False, "offline": True, "message": str(e)}


def _verify(key, increment):
    if GUMROAD_PRODUCT_ID.startswith("PASTE_"):
        return {"success": False, "message": "This build has no product id compiled in."}
    return _post(VERIFY_URL, {
        "product_id": GUMROAD_PRODUCT_ID,
        "license_key": key.strip(),
        "increment_uses_count": "true" if increment else "false",
    })


def _dead(purchase):
    """Refunded / disputed / cancelled subscription -> licence no longer valid."""
    if purchase.get("refunded") or purchase.get("chargebacked") or purchase.get("disputed"):
        return "This purchase was refunded."
    if purchase.get("subscription_cancelled_at") or purchase.get("subscription_failed_at"):
        return "This subscription is no longer active."
    return None


# --------------------------------------------------------------------- status
class Status:
    def __init__(self, ok, mode, message="", days_left=0, email=""):
        self.ok = ok                  # may the engine run?
        self.mode = mode              # licensed | trial | expired | invalid
        self.message = message
        self.days_left = days_left
        self.email = email

    def __bool__(self):
        return self.ok

    @property
    def short(self):
        if self.mode == "licensed":
            return "licensed"
        if self.mode == "trial":
            return f"trial — {self.days_left} day{'s' if self.days_left != 1 else ''} left"
        return "unlicensed"


def activate(key):
    """User typed a key. Verify online, consume a seat, store it. Returns Status."""
    key = (key or "").strip()
    if not key:
        return Status(False, "invalid", "Enter your licence key.")

    r = _verify(key, increment=True)
    if not r.get("success"):
        if r.get("offline"):
            return Status(False, "invalid",
                          "Could not reach Gumroad. Check your internet and try again.")
        return Status(False, "invalid", r.get("message") or "That key was not recognised.")

    p = r.get("purchase", {}) or {}
    gone = _dead(p)
    if gone:
        return Status(False, "invalid", gone)

    uses = int(r.get("uses", 1) or 1)
    if uses > SEATS:
        return Status(False, "invalid",
                      f"This key is already active on {uses - 1} machines "
                      f"(limit {SEATS}). Email support to reset it.")

    d = {"key": key, "machine": machine_id(), "checked": time.time(),
         "email": p.get("email", ""), "uses": uses}
    d["sig"] = _sign(d)
    _write(LIC_FILE, d)
    return Status(True, "licensed", "Licence activated. Thank you.", email=d["email"])


def check():
    """Called at launch and before the engine starts. Never blocks for long."""
    if os.environ.get("RMIDI_DEV"):
        return Status(True, "licensed", "Developer build.")
    d = _read(LIC_FILE)
    if _valid(d) and d.get("machine") == machine_id():
        age_days = (time.time() - float(d.get("checked", 0))) / 86400.0
        if age_days < RECHECK_DAYS:
            return Status(True, "licensed", email=d.get("email", ""))

        r = _verify(d["key"], increment=False)     # silent re-check, no seat consumed
        if r.get("success"):
            gone = _dead(r.get("purchase", {}) or {})
            if gone:
                deactivate()
                return Status(False, "invalid", gone)
            d["checked"] = time.time()
            d["sig"] = _sign(d)
            _write(LIC_FILE, d)
            return Status(True, "licensed", email=d.get("email", ""))

        if r.get("offline") and age_days < GRACE_DAYS:
            return Status(True, "licensed", "Working offline.", email=d.get("email", ""))
        if r.get("offline"):
            return Status(False, "invalid",
                          "Could not verify your licence for 30 days. Connect once to continue.")
        deactivate()
        return Status(False, "invalid", r.get("message") or "Licence no longer valid.")

    left = trial_days_left()
    if left > 0:
        return Status(True, "trial", f"Trial — {left} days left.", days_left=left)
    return Status(False, "expired", "Your 7-day trial has ended.")


def deactivate():
    try:
        os.remove(LIC_FILE)
    except OSError:
        pass
