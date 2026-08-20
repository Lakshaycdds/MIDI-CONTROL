"""Target registry. Drop a new module here and add it to _MODULES."""
import importlib

_MODULES = {
    "resolve":      ".resolve_target",
    "aftereffects": ".aftereffects_target",
    "premiere":     ".premiere_target",
    "logic":        ".logic_target",
    "macos":        ".macos_target",
}
_CACHE = {}


def available():
    """[(name, label)] for every target that imports cleanly on this machine."""
    out = []
    for name in _MODULES:
        try:
            out.append((name, get_class(name).label))
        except Exception:
            continue
    return out


def get_class(name):
    if name not in _CACHE:
        mod = importlib.import_module(_MODULES[name], __package__)
        _CACHE[name] = mod.TARGET
    return _CACHE[name]


def make(name, cfg=None):
    return get_class(name)(cfg)
