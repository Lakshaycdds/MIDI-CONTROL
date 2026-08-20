import os, yaml
HERE = os.path.dirname(__file__)
PROFILES = os.path.join(HERE, "profiles")

def load(path):
    if not os.path.exists(path):
        alt = os.path.join(PROFILES, path if path.endswith(".yaml") else path + ".yaml")
        if os.path.exists(alt):
            path = alt
        else:
            raise SystemExit(f"no such profile: {path}")
    with open(path) as f:
        return yaml.safe_load(f)

def save(cfg, path):
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, default_flow_style=False)
    return path

def list_profiles():
    return sorted(x for x in os.listdir(PROFILES) if x.endswith(".yaml"))
