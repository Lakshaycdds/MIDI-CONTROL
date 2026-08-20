"""Interface every controllable application implements.

A target owns: how to reach the app, what actions it exposes, and how to report status.
Adding a new application means dropping a module in this package and registering it.
"""


class Target:
    name = "base"           # id used in profiles  ->  target: resolve
    label = "Base"          # shown in the GUI
    app_hint = ""           # bundle name, for the GUI's "is it running" check

    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    # --- lifecycle -------------------------------------------------------
    def connect(self) -> bool:
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        raise NotImplementedError

    def status(self) -> str:
        return "not connected"

    def flush(self):
        pass

    # --- what the controller can drive -----------------------------------
    def build_actions(self, engine) -> dict:
        """Return {action_name: callable(value)}."""
        raise NotImplementedError

    def startup_report(self) -> list:
        """Lines printed once when the engine starts. Target-specific detail."""
        return []

    def node_count(self) -> int:
        """Only meaningful for node-based apps; used for LED feedback."""
        return 0

    def describe_actions(self) -> list:
        """Return [(action_name, human description)] for the GUI mapping editor."""
        return []
