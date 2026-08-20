# rmidi

**Turn any MIDI controller into a control surface for DaVinci Resolve, After Effects,
Premiere Pro, Logic Pro — and for macOS itself.**

rmidi maps knobs, pads, keys and touch strips onto real application actions. In DaVinci
Resolve it writes exact numeric colour values through the scripting API — no mouse
dragging, no screen coordinates, nothing that breaks when you move a panel. In After
Effects it sets real layer properties through ExtendScript. Everywhere else it drives the
application's own keyboard shortcuts. Switch applications and the mapping follows you.

---

## Contents

- [Requirements](#requirements)
- [Install](#install)
- [Accessibility permission](#accessibility-permission--required)
- [The window](#the-window)
- [How the controls behave](#how-the-controls-behave)
- [Bindings — DaVinci Resolve](#bindings--davinci-resolve-studio)
- [Bindings — After Effects](#bindings--after-effects)
- [Bindings — Premiere Pro](#bindings--premiere-pro)
- [Bindings — Logic Pro](#bindings--logic-pro)
- [Bindings — macOS](#bindings--macos)
- [Follow active app](#follow-active-app)
- [Customising a profile](#customising-a-profile)
- [Using a different controller](#using-a-different-controller)
- [Adding another application](#adding-another-application)
- [How it works](#how-it-works)
- [Limits](#limits-read-this)
- [Troubleshooting](#troubleshooting)
- [Notes for redistribution](#notes-for-redistribution)

---

## Requirements

| | |
|---|---|
| **macOS** | 11 Big Sur or newer, Apple Silicon or Intel |
| **MIDI controller** | Any class-compliant device. Ships pre-mapped for the Novation Launchkey Mini MK4 25 |
| **DaVinci Resolve** | **Studio only** — the free build has no external scripting. Tested on 21.0.2 |
| **After Effects** | 2025 or newer (uses `DoScript`) |
| **Premiere Pro / Logic Pro** | Any recent version — driven by keyboard shortcuts |

Nothing else to install. Python and every dependency are bundled inside the app.

---

## Install

Double-click **`rmidi-x.y.z.pkg`**. It installs:

- `rmidi.app` into **/Applications**
- Two colour-space LUTs into Resolve's LUT folder

The package is not signed with an Apple Developer ID, so Gatekeeper will object the first
time — right-click the `.pkg` → **Open** → **Open**.

> **Keep only one copy of rmidi.app.** macOS grants Accessibility per binary. If several
> copies exist you will grant permission to one and run another, and nothing will work.

---

## Accessibility permission — required

Everything except Resolve colour grading works by sending synthetic pointer and keyboard
events. **macOS silently discards those unless the app is trusted** — no error, no prompt,
the controls just do nothing.

**System Settings → Privacy & Security → Accessibility**

1. Remove any stale `rmidi` entries with **−**
2. **+** → Applications → **rmidi** → switch **on**
3. Quit and reopen rmidi

The window shows its own bundle path under the title. While permission is missing it turns
red and reads `GRANT ACCESSIBILITY TO THIS EXACT APP:` — so you can confirm you granted the
right binary. The **Accessibility** light goes green once it is working.

Updating the app changes its hash and can leave a stale entry that looks enabled but grants
nothing. If controls stop after an update, remove the entry and add it again.

---

## The window

| Element | What it does |
|---|---|
| **Application** | Which software to drive |
| **MIDI device** | Your controller. Use the *MIDI Out* port, not *DAW Out* |
| **Profile** | The mapping to load. Selecting one also selects its application |
| **MIDI** light | Green when the controller port is open |
| **App** light | Green when the target application is reachable |
| **Accessibility** light | Green when macOS allows synthetic events |
| **Follow active app** | Switch profiles automatically as you change application |
| **Start / Stop** | Begin or end listening |
| **Mapping** table | Every control, its type, its action, and what it does |
| **Live log** | Each action as it fires, with resulting values |

A menu-bar icon shows **◉ running** / **○ stopped** and offers Show Window, Start/Stop and
Quit when the window is closed.

---

## How the controls behave

### Knobs never jump
rmidi reads **change, not position**. Grabbing a knob that sits at a different place from
the parameter it controls will not snap the value — it moves from where the parameter
already is. Turn faster and it moves faster.

### End stops and the clutch
Most knobs are limited pots, so they run out of travel. When one hits either end the log
prints `[endstop]` and the **CLUTCH** pad lights red. Hold **CLUTCH**, spin the knob back to
centre — input is muted while held — release, and carry on. Travel is effectively infinite.

Controllers with endless encoders need none of this; set `mode: rel` in the profile.

### Modifiers
Three pads, held rather than pressed, on the bottom-left where your other hand rests:

| Modifier | Effect |
|---|---|
| **FINE** | ×0.15 — precision work |
| **SHIFT** | ×5 — fast moves. Also selects a control's alternate action |
| **CLUTCH** | Mutes knobs so you can re-centre a bottomed-out pot |

### It survives the controller's own mode switches
Controllers like the Launchkey remap themselves as you change **Pad Mode** and **Encoder
Mode**, which silently moves every control to different MIDI addresses. rmidi handles this:

- **Knob banks self-learn.** Land on a CC bank rmidi has not seen and it detects the
  contiguous run of eight and maps them automatically, logging the bank so you can make it
  permanent.
- **Pads are octave-tolerant.** The Oct−/Oct+ buttons shift pad notes by twelve; bindings
  follow across ±3 octaves.

Keep **Pad Mode** on **Drum**. Chord Map and User Chord transpose the pads by design and no
software can compensate for that.

---

## Bindings — DaVinci Resolve Studio

Profile `launchkey-mini-mk4`. Grading is written through the scripting API as exact
numbers.

### Knobs

| # | Control | CDL parameter |
|---|---|---|
| 1 | **Lift** — shadows, all channels | Offset |
| 2 | **Gamma** — midtones | Power |
| 3 | **Gain** — highlights | Slope |
| 4 | **Saturation** | Saturation |
| 5 | **Gain Red** | Slope R |
| 6 | **Gain Green** | Slope G |
| 7 | **Gain Blue** | Slope B |
| 8 | **Lift Red** | Offset R |

Knobs 5–7 together are white balance in the highlights: red up and blue down warms the image.

### Pads — top row

| Pad | Action | LED |
|---|---|---|
| 1 | Select previous node | blue |
| 2 | Select next node | blue |
| 3 | Add serial node | green |
| 4 | Add parallel node | green |
| 5 | Delete node | red |
| 6 | Enable / disable node | orange |
| 7 | Reset this node's grade | red |
| 8 | Before / after | magenta |

### Pads — bottom row

| Pad | Action | LED |
|---|---|---|
| 9 | **FINE** (hold) | lit while held |
| 10 | **CLUTCH** (hold) | lit while held, red on endstop |
| 11 | **SHIFT** (hold) | lit while held |
| 12 | Grab still to gallery | cyan |
| 13 | Previous clip | blue |
| 14 | Next clip | blue |
| 15 | Add colour version | yellow |
| 16 | Go to Color page | white |

### Other controls

| Control | Action |
|---|---|
| **▲ ▼** | Previous / next clip |
| **Pitch strip** | Shuttle scrub — springs back to centre, further = faster, up to 25 fps |
| **Modulation strip** | Absolute saturation, 0.0 at the bottom to 2.0 at the top |
| **First key** | Build a colour-space node stack (below) |
| **SHIFT + first key** | Same, overwriting a clip that is already graded |

### The colour-space stack

Pressing the first key on an ungraded clip creates two nodes and loads:

| Node | Transform |
|---|---|
| 1 | S-Gamut3.Cine / S-Log3 → DaVinci Wide Gamut / DaVinci Intermediate |
| 2 | DaVinci Wide Gamut / DaVinci Intermediate → Rec.709 / Gamma 2.4 |

These are 65×65×65 `.cube` LUTs generated from the published Sony and Blackmagic
constants. The gamut matrices are derived from primaries and white point, and verified
against Sony's S-Gamut3.Cine→XYZ and Blackmagic's DaVinci WG→XYZ matrices to within
2×10⁻⁵. Mid grey lands exactly where a Color Space Transform with no tone mapping puts it.

They are **LUT nodes, not Color Space Transform OFX nodes** — the same maths, but without
the CST dropdowns. Resolve's API cannot create an OFX; see [Limits](#limits-read-this).

The node stack is refused on a clip that already has a grade unless you hold **SHIFT**, and
a gallery still is grabbed as a backup before the first write of a session.

---

## Bindings — After Effects

Profile `launchkey-aftereffects`. Knobs set **real property values** on every selected
layer through ExtendScript, wrapped in a single undo group.

### Knobs

| # | Property |
|---|---|
| 1 | Opacity |
| 2 | Rotation |
| 3 | Scale X |
| 4 | Scale Y |
| 5 | Position X |
| 6 | Position Y |
| 7 | Anchor Point X |
| 8 | Anchor Point Y |

### Pads

| Pad | Action | | Pad | Action |
|---|---|---|---|---|
| 1 | Previous frame | | 9 | **FINE** (hold) |
| 2 | Next frame | | 10 | **CLUTCH** (hold) |
| 3 | New solid | | 11 | **SHIFT** (hold) |
| 4 | New null | | 12 | Show keyframed properties |
| 5 | Duplicate layer | | 13 | Work area start |
| 6 | Pre-compose | | 14 | Work area end |
| 7 | Split layer | | 15 | RAM preview |
| 8 | Delete layer | | 16 | Save |

**▲▼** previous / next frame · **Pitch strip** shuttle · **Modulation strip** opacity

---

## Bindings — Premiere Pro

Profile `launchkey-premiere`. Keyboard shortcuts only — see [Limits](#limits-read-this).

### Pads

| Pad | Action | | Pad | Action |
|---|---|---|---|---|
| 1 | Previous edit point | | 9 | **FINE** (hold) |
| 2 | Next edit point | | 10 | **CLUTCH** (hold) |
| 3 | Mark in | | 11 | **SHIFT** (hold) |
| 4 | Mark out | | 12 | Mark clip |
| 5 | Cut at playhead | | 13 | Previous frame |
| 6 | Ripple delete | | 14 | Next frame |
| 7 | Insert | | 15 | Lumetri / Effect Controls |
| 8 | Overwrite | | 16 | Save |

Knobs alternate between scrubbing the timeline and nudging whichever parameter has focus.
**▲▼** previous / next edit point.

---

## Bindings — Logic Pro

Profile `launchkey-logic`. Knobs scrub the playhead.

| Pad | Action | | Pad | Action |
|---|---|---|---|---|
| 1 | Rewind | | 9 | **FINE** (hold) |
| 2 | Forward | | 10 | **CLUTCH** (hold) |
| 3 | Record | | 11 | **SHIFT** (hold) |
| 4 | Cycle mode | | 12 | Metronome |
| 5 | Split at playhead | | 13 | Mute |
| 6 | Join regions | | 14 | Solo |
| 7 | Loop region | | 15 | Mixer |
| 8 | Quantize | | 16 | Save |

---

## Bindings — macOS

Profile `launchkey-macos`. Drive the Mac with no keyboard or mouse.

### Knobs

| # | Action |
|---|---|
| 1 | Move pointer horizontally |
| 2 | Move pointer vertically |
| 3 | Scroll up / down |
| 4 | Scroll left / right |
| 5–6 | Pointer X / Y at quarter speed — precision |
| 7–8 | Scroll vertical / horizontal, slow |

Hold **FINE** for a slow pointer, **SHIFT** for a fast one. The pointer moves across the
union of all displays, so it is never trapped on one screen.

### Pads

| Pad | Action | | Pad | Action |
|---|---|---|---|---|
| 1 | Left click | | 9 | **FINE** (hold) |
| 2 | Double click | | 10 | **CLUTCH** (hold) |
| 3 | Right click | | 11 | **SHIFT** (hold) |
| 4 | Switch app (⌘-tab) | | 12 | Escape |
| 5 | Spotlight | | 13 | Volume down |
| 6 | Mission Control | | 14 | Volume up |
| 7 | Previous desktop | | 15 | Play / pause media |
| 8 | Next desktop | | 16 | Screenshot selection |

A further 25 actions — copy, paste, cut, undo, redo, save, arrows, return, tab, delete,
brightness, track skip, close window, minimise, full screen, lock screen — are available to
bind. Run **`rmidi actions`** or read the Mapping table for the full list.

---

## Follow active app

Tick **Follow active app**. rmidi watches the frontmost application and loads the matching
profile within about a second: grading in Resolve, layer properties in After Effects,
editing in Premiere, transport in Logic — and Mac control everywhere else.

The mapping lives in `rmidi/autoswitch.py`:

```python
DEFAULT_MAP = {
    "com.blackmagic-design.DaVinciResolve": "launchkey-mini-mk4",
    "com.adobe.AfterEffects.application":   "launchkey-aftereffects",
    "com.adobe.PremierePro.26":             "launchkey-premiere",
    "com.apple.logic10":                    "launchkey-logic",
}
FALLBACK = "launchkey-macos"
```

Find any application's bundle id with:

```bash
osascript -e 'id of app "Safari"'
```

---

## Customising a profile

Profiles are YAML in `rmidi/profiles/`. Edit one and restart rmidi.

```yaml
target: resolve                    # which application this profile drives
device: Launchkey Mini MK4 25 MIDI Out
push_hz: 40                        # value updates per second, coalesced
fine_scale: 0.15                   # FINE multiplier
shift_scale: 5.0                   # SHIFT multiplier
default_node: 1                    # Resolve: node the knobs write to at startup
autobackup: true                   # grab a gallery still before the first write
leds: true
led_channels: [0, 1, 2]
pad_octave_tolerant: true          # Oct-/Oct+ cannot break pad bindings
knob_cc_banks: [21, 51]            # CC banks the Encoder Modes use
shuttle_max_fps: 25

bindings:
  - {type: cc,   ch: 9, cc: 21, mode: abs, action: cdl.lift, step: 0.0025}
  - {type: note, ch: 2, note: 40, action: node.prev}
  - {type: pitch, ch: 1, action: shuttle}
  - {type: cc,   ch: 1, cc: 1, mode: absolute, action: abs.sat, min: 0.0, max: 2.0}
  - {type: note, ch: 9, note: 48, action: grade.cst_stack,
     shift_action: grade.cst_stack.force}
```

| Field | Meaning |
|---|---|
| `type` | `cc`, `note` or `pitch` |
| `ch` | MIDI channel, 1-based |
| `mode` | `abs` limited pot · `rel` endless encoder · `absolute` position-mapped fader or strip · `button` |
| `step` | Units per detent |
| `min` / `max` | Range for `absolute` mode |
| `invert` | Reverse direction |
| `shift_action` | Alternate action while SHIFT is held |

---

## Using a different controller

```bash
rmidi learn --seconds 45
```

Turn every knob end to end and press every pad. rmidi classifies each control as button,
relative or absolute and writes a profile skeleton with the addresses filled in — you add
the action names. `rmidi actions` lists every available action.

---

## Adding another application

Targets are plug-ins. Drop a module in `rmidi/targets/`:

```python
from .base import Target

class MyAppTarget(Target):
    name  = "myapp"
    label = "My Application"

    def connect(self): ...
    @property
    def connected(self): ...
    def status(self): ...                    # one line for the GUI
    def build_actions(self, engine): ...     # {action_name: callable(value)}
    def describe_actions(self): ...          # [(name, human description)]

TARGET = MyAppTarget
```

Register it in `rmidi/targets/__init__.py` under `_MODULES`, then set `target: myapp` at
the top of a profile. It appears in the Application picker automatically.

Applications driven purely by shortcuts can subclass `KeystrokeTarget` and declare a `KEYS`
dictionary — the whole Logic Pro target is about forty lines.

---

## How it works

| Path | Mechanism | Used for |
|---|---|---|
| API | `TimelineItem.SetCDL()` | Resolve: Lift / Gamma / Gain / Saturation, master and per channel |
| API | `Graph.SetLUT()` and native calls | Resolve: colour-space stack, node select and bypass, stills, versions, pages |
| ExtendScript | `DoScript` over AppleScript | After Effects layer properties |
| Keys | Quartz `CGEventPostToPid` to the app's process | Shortcuts, sent even when the app is not focused |
| Quartz | Pointer, scroll and HID media events | macOS control |

### The CDL model
Resolve applies `out = (in × Slope + Offset) ^ Power`, then Saturation.
Slope is **Gain** (default 1.0), Offset is **Lift** (0.0), Power is **Gamma** (1.0).

`SetCDL` is write-only — Resolve exposes no getter — so rmidi holds the authoritative state
per clip and node and pushes it at `push_hz`, coalesced. It never writes to a node you have
not touched, because even a neutral write mutates the node.

---

## Limits (read this)

- **DaVinci Resolve Studio is required.** The free build has no external scripting.
- **Resolve's API cannot create nodes or add OFX plugins.** The only graph writes it offers
  are `SetLUT`, `SetNodeCacheMode`, `SetNodeEnabled`, `ApplyGradeFromDRX`, `ApplyArriCdlLut`
  and `ResetAllGrades`. Nodes are therefore created with the Add-Serial keyboard shortcut,
  and colour-space transforms are applied as LUTs rather than CST OFX nodes.
- **Resolve's curves, qualifiers, power windows, HDR palette and OFX are not scriptable at
  all** and cannot be driven.
- **Premiere Pro has no ExtendScript-over-AppleScript bridge.** Numeric Lumetri values are
  unreachable; knobs send repeated arrow keys to whatever parameter has focus, which is
  coarse. Buttons work properly. Real Lumetri control would need a CEP/UXP panel running
  inside Premiere.
- **Accessibility permission is mandatory** for everything except Resolve grading.
- **macOS only.** The MIDI and application layers are portable, but keystroke sending uses
  Quartz.

---

## Troubleshooting

**Nothing happens, but the app says it started.**
Check the **Accessibility** light. If it is red, macOS is discarding every event — grant
permission to the exact bundle path shown under the title.

**Some controls work, others do nothing.**
Your controller has changed Pad Mode or Encoder Mode. Knob banks are learned automatically;
watch the log for `[bank] learned knob CC bank …`. For pads, return to **Drum** mode.

**`cannot open <device>` in the log.**
Another program has the MIDI port. Quit any other rmidi instance or DAW holding it.

**Controls stopped working after an update.**
The Accessibility entry went stale. Remove it and add the app again.

**It worked, then stopped after switching applications.**
**Follow active app** loaded a different profile. Untick it to stay on one mapping.

---

## Notes for redistribution

If you intend to distribute this commercially:

- **Sign and notarise it.** Without an Apple Developer ID ($99/year) every buyer meets a
  Gatekeeper warning, and an unsigned app's Accessibility grant breaks on each update
  because macOS identifies it by content hash. A stable Developer ID signature fixes both.
- **Check the bundled licences.** rmidi builds on mido, python-rtmidi, PyObjC, PyYAML and
  PyInstaller. All carry permissive licences that allow commercial distribution, and
  PyInstaller explicitly permits shipping frozen applications, but verify the terms of each
  for yourself before selling.
- **DaVinci Resolve, After Effects, Premiere Pro and Logic Pro are trademarks of their
  respective owners.** Describe compatibility, do not imply endorsement or affiliation.
- **The colour-space LUTs are generated from published constants**, not extracted from any
  application.
