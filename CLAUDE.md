# Instructions for Claude Code working in this repo

This is Justin's personal QMK keymap for his ZSA Voyager. Development now
happens entirely in this repo, directly in `keymap/keymap.c` — there is no
more Oryx export/re-import cycle. If a conversation ever mentions an Oryx
`_source.zip`, that workflow is retired; just edit the files here.

## Build environment

- `~/qmk_firmware` is ZSA's QMK fork, checked out on branch **`firmware25`**
  (not `firmware24` — that branch is missing `modules/zsa/oryx`, the
  community module Oryx's own cloud builder links in, and firmware built
  without it behaves differently, especially around RGB/live-control).
- `~/qmk_firmware/keyboards/zsa/voyager/keymaps/yayaya-alttab` is a **symlink**
  to this repo's `keymap/` directory. Edit files here, not there.
- The nixpkgs `qmk` package is missing the `appdirs` python dependency.
  `scripts/build.sh` and `scripts/setup.sh` work around this by resolving
  it separately via `nix build nixpkgs#python3Packages.appdirs` and passing
  it through `PYTHONPATH`. If `qmk compile`/`qmk setup` ever fails with
  `Could not find module appdirs!`, that's the workaround to check.
- This qmk_firmware checkout has one local patch on top of `firmware25`:
  `lib/python/qmk/math.py` uses the Python `ast.Num` API, removed in Python
  3.12+. `scripts/setup.sh` patches it to `ast.Constant` automatically. If
  qmk_firmware ever gets reset/re-cloned, re-run `scripts/setup.sh`.
- `qmk compile` reads `config.h`/`rules.mk`/`keymap.json` from the keymap dir
  too (not just `keymap.c`) — all four files matter and all four live in
  `keymap/` here.

## Workflow for making changes

1. Edit `keymap/keymap.c` (or the other three files) directly.
2. Run `./scripts/build.sh` from the repo root.
3. The `.bin` lands in `build/` and gets copied to Windows Downloads
   automatically. Tell the user to flash it with **Keymapp** (not Wally —
   deprecated) and briefly summarize what changed.
4. Commit when the user asks you to (same rule as everywhere else — don't
   commit unprompted).

## The LED-index gotcha (read before touching any color)

`ledmap[][RGB_MATRIX_LED_COUNT][3]` in `keymap.c` is indexed in **LED wiring
order**. The keycodes inside `LAYOUT_voyager(...)` are listed in a
**different order** (reading order: left-to-right, top-to-bottom, thumbs
last). These two orders are NOT the same, and guessing the mapping by eye
reliably lights the wrong physical key.

Before writing a color:
1. Find the key's position in the `LAYOUT_voyager(...)` argument list,
   counting from 0 (first key of the first layer row = 0).
2. Run `scripts/arg_to_led.py <that position>` to get the real LED index.
3. Write the color at that index in `ledmap[]`.

For a whole layer at once, it's much less error-prone to write all 52
colors in argument order (matching the keycodes visually, top to bottom)
and pipe them through `scripts/render_ledmap.py`, which reorders them
correctly and prints the finished array literal — this is faster and safer
than hand-computing 52 individual indices.

Both scripts derive the mapping from `keyboards/zsa/voyager/keyboard.json`'s
`layouts.LAYOUT.layout` (argument position → matrix `[row,col]`) and
`rgb_matrix.layout` (LED index → matrix `[row,col]`), which is stable across
every keymap edit (it's a hardware property, not a keymap property) — no
need to recompute it from scratch each time, just call the scripts.

After writing colors, sanity-check by rendering the layer as a labeled grid
(key name + color name, laid out like the physical board) before compiling —
this catches category mistakes that the index math alone can't.

## Lighting philosophy

Only light keys that actually do something on the active layer; everything
unused/transparent stays dark (`{0,0,0}`). Beyond that baseline, **design
each layer's lighting proactively** — infer the layer's purpose from its
keycodes and give it its own visual identity, and make functionally special
clusters (movement keys, numpad digits, a launcher key, etc.) pop in their
own color rather than defaulting everything to the same bucket. Don't wait
to be told exact colors each time.

Current shared palette (HSV, hue/sat/val out of 255) — reuse these for
continuity rather than inventing new ones per layer unless a layer's theme
genuinely needs something new:

| Color | HSV | Meaning |
|---|---|---|
| white | `0,0,255` | plain functional key (letters, numbers, Enter, Backspace, Space) |
| light blue | `150,170,255` | modifier (Esc/Tab/Shift/Ctrl/GUI/Alt) |
| light green | `85,140,255` | layer-switch key |
| blue | `170,150,255` | symbols layer's punctuation/shortcut keys |
| light orange | `28,140,255` | macro/launcher-style shortcut key (omnibar, screenshot shortcut) |
| orange | `28,200,255` | function keys (F1-F12) |
| purple | `191,180,255` | OSM GUI |
| magenta | `213,180,255` | OSM Alt |
| yellow | `43,190,255` | OSM Ctrl |
| teal | `135,210,255` | numpad digits (layer 4) |
| red | `0,200,255` | gaming-layer movement keys (WASD) |

All saturations are deliberately kept in the ~140-210 range, not maxed at
255 — the user explicitly prefers this softer look over harsh fully-
saturated colors (confirmed preference, not a default).

## Alt-Tab mechanics (there are two independent implementations)

**Layer 1 (symbols)**: the Tab key there is the custom keycode `ALT_TAB`.
Pressing it registers `KC_LALT` (if not already registered) and taps
`KC_TAB`; the `case MO(1):` handler in `process_record_user` releases
`KC_LALT` when the layer-hold thumb key is released. This is the "usual
motion" referenced elsewhere in this doc: hold the thumb, tap Tab, release
to select — zero delay, because nothing is predicted in advance, only
decided retroactively on release.

**Layer 3 (gaming)**: a different mechanism, `GAME_CTL` (the left-thumb key)
+ `GAME_TAB` (that layer's Tab slot). `GAME_CTL` is real Ctrl for everything
by default. The *first* time `GAME_TAB` is pressed while `GAME_CTL` is held,
it swaps live — unregisters Ctrl, registers `KC_LALT` instead, sets
`game_alt_active` — then sends Tab. Releasing Tab only releases Tab; Alt
stays registered so repeated Tab taps keep the real OS switcher open and
cycling. Only releasing `GAME_CTL` itself releases Alt and resets the swap.
This was a deliberate design after iterating through several alternatives —
see "design history" below before changing it again.

If a `TD(...)` tap-dance keycode shows up in this keymap again (there was
one briefly, since removed), watch for two generated-template bugs:
1. `_finished`/`_reset` switches often omit the `SINGLE_HOLD`/`DOUBLE_HOLD`
   cases, so press-and-hold (not just tapping) silently does nothing.
2. `dance_step()` often checks `state->interrupted` before `state->pressed`,
   so pressing a third key while mid-hold gets misclassified as a tap
   instead of a hold. Check `state->pressed` first:
   ```c
   if (state->count == 1) {
       if (state->pressed) return SINGLE_HOLD;
       else return SINGLE_TAP;
   } else if (state->count == 2) {
       if (state->pressed) return DOUBLE_HOLD;
       else if (state->interrupted) return DOUBLE_SINGLE_TAP;
       else return DOUBLE_TAP;
   }
   ```
   Prefer plain dedicated keys over tap-dance for anything performance-
   sensitive, though — that's why layer 3 moved away from it.

## Gaming layer (3) constraints — read before changing anything on it

- **Left-hand only.** The right hand is on the mouse. Never put a gaming-
  layer binding on the right half of the board or the right thumb cluster —
  this was tried and explicitly rejected.
- **No hand repositioning off WASD.** Modifiers must stay within the
  pinky's reach on the leftmost column (where Tab/home-row/Shift already
  sit) or the thumb cluster. Putting things on the top row above Q/W was
  tried and rejected — it requires lifting the whole hand off the WASD
  resting position, which defeats the point.
- **Alt-Tab must use the thumb-hold + Tab-tap gesture**, matching layer 1's
  muscle memory, not a finger-key hold. This is why Ctrl/Alt ended up on
  `GAME_CTL`/`GAME_TAB` (thumb) rather than a home-row key.

Current layout on layer 3: Space = left-inner thumb, `GAME_CTL` (Ctrl, or
Alt-Tab when combined with Tab) = left-outer thumb, standalone Alt = home
row below Tab, layer-shift `MO(1)` = top row above Tab, Backspace = top-
right corner (inherited from layer 0, see below).

### Design history (don't silently re-litigate these)

The gaming layer went through several iterations before landing here:
tap-dance (Ctrl+Alt on one key, double-tap-hold for Alt) → too much friction,
removed. Then two plain keys (Ctrl home-row, Alt thumb) → Alt-Tab didn't
match "the usual motion." Then swapped (Alt thumb, Ctrl home-row) → but
then there was no way to get Ctrl *and* Alt-Tab both easily without two
keys. Landed on `GAME_CTL`/`GAME_TAB`: one thumb key that's Ctrl by default
and silently becomes Alt the instant Tab joins it. If asked to "simplify"
this again, make sure whatever replaces it still satisfies: thumb-hold alone
= Ctrl, thumb-hold + Tab = Alt-Tab with Alt sustained across repeated taps.

## Keycode flow-through

Transparent (`KC_TRANSPARENT`) keys fall through to the next layer down,
ultimately to layer 0. Setting something on layer 0 "flows down" for free
to every layer that leaves that position transparent — this is how the
top-right Backspace key works (set once on layer 0, inherited by layers
1/2/4 automatically; layer 3 has it set explicitly since that corner is
otherwise unused there too). When adding a new universally-useful key,
prefer setting it on layer 0 and letting it flow down over repeating it on
every layer — but remember the **lighting doesn't flow through automatically**
the way keycodes do; `ledmap[]` is per-layer and independent, so light the
same position on every layer that inherits the keycode if you want the
lighting to reflect it.
