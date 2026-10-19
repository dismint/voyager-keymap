# Instructions for Claude Code working in this repo

This is Justin's personal QMK keymap, primarily for his ZSA Voyager.
Development happens entirely in this repo — there is no more Oryx
export/re-import cycle. If a conversation ever mentions an Oryx
`_source.zip`, treat it as a one-off reference import (e.g. for porting to
a new physical board), not something to build against directly.

The same logical keymap is also generated for a ZSA Moonlander. **The
Voyager (`keymap/keymap.c`) is the single source of truth.**
`keymap-moonlander/keymap.c` is a **generated file — never hand-edit it.**
`scripts/generate_moonlander.py` derives it from `keymap/keymap.c` by
re-mapping the Voyager's 52 argument-position keycodes/colors onto their
Moonlander equivalents and copying every other line (enums, combos,
`process_record_user`, lighting functions — none of it is keyboard-
specific) verbatim. `scripts/build.sh moonlander` runs the generator
automatically before compiling, so the two can't drift out of sync as long
as you only ever edit `keymap/keymap.c`. See "Porting to a new board"
below for the exact position mapping.

**One thing the generator does NOT cover: `config.h`.** Each board has its
own hand-written `config.h` (different `SERIAL_NUMBER`, intentionally).
`COMBO_COUNT` lives there, not in `keymap.c` — if a combo is added or
removed, update `COMBO_COUNT` in *both* `keymap/config.h` and
`keymap-moonlander/config.h` by hand. A mismatch here compiles fine but
silently drops or corrupts combos at runtime.

## Build environment

- `~/qmk_firmware` is ZSA's QMK fork, checked out on branch **`firmware25`**
  (not `firmware24` — that branch is missing `modules/zsa/oryx`, the
  community module Oryx's own cloud builder links in, and firmware built
  without it behaves differently, especially around RGB/live-control).
- `~/qmk_firmware/keyboards/zsa/voyager/keymaps/yayaya-alttab` and
  `~/qmk_firmware/keyboards/zsa/moonlander/keymaps/yayaya-alttab` are
  **symlinks** to this repo's `keymap/` and `keymap-moonlander/`
  directories respectively. Edit files here, not there.
- The Moonlander only compiles against a specific revision folder:
  `-kb zsa/moonlander/reva` (there's no default revision at the top-level
  `zsa/moonlander`, so the bare path errors out). `scripts/build.sh
  moonlander` already knows this.
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

1. Edit `keymap/keymap.c` (or the other three Voyager files) directly.
   Never edit `keymap-moonlander/keymap.c` — it's generated (see above).
2. Run `./scripts/build.sh` for the Voyager. For the Moonlander, run
   `./scripts/build.sh moonlander` — this regenerates
   `keymap-moonlander/keymap.c` from the Voyager source first, then
   compiles. (You can also run `./scripts/generate_moonlander.py` on its
   own if you just want to inspect the generated file without compiling.)
3. The `.bin` lands in `build/` and gets copied to Windows Downloads
   automatically. Tell the user to flash it with **Keymapp** (not Wally —
   deprecated) and briefly summarize what changed.
4. Run `./scripts/render_layouts.py` whenever `keymap/keymap.c` changed —
   it regenerates `layout/*.svg` from the current keymap and splices fresh
   image embeds into README.md between the `LAYOUT:START`/`LAYOUT:END`
   markers. Keep the `LAYER_NAMES` dict at the top of that script in sync
   if a layer's purpose changes or a layer is added/removed. There's no
   separate diagram generation for the Moonlander — it's not meant to be
   "first class," just kept logically in sync.
5. Commit when the user asks you to (same rule as everywhere else — don't
   commit unprompted). `keymap-moonlander/keymap.c` is still checked into
   git even though it's generated, so the repo is buildable without
   re-running the generator — but always regenerate before committing a
   Voyager change, so the committed Moonlander file never goes stale.

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

**This is a strict, closed palette — do not reintroduce per-layer unique
colors or add a new category without being asked.** Only light keys that
are genuinely remapped/active on that layer; anything transparent/inherited
(unchanged from layer 0, e.g. WASD on the Gaming layer, or a key that's
explicitly redeclared but with the exact same value layer 0 already has,
e.g. Backspace on the Gaming layer) stays fully dark (`{0,0,0}`), even if
it's functionally important on that layer — **"changed from layer 0" is
what earns color, not "important."**

| Color | HSV | Category | Used for |
|---|---|---|---|
| white (primary) | `0,0,255` | Primary | any plain functional key — letters, numbers, symbols, Enter/Backspace/Space, arrow keys. The default for "just a regular key." |
| light green (layer) | `85,140,255` | Layer | any layer-switch key, `MO()` or `TG()` alike — color doesn't distinguish hold vs. toggle, the label text does (`LR n` vs `TO n`) |
| light blue (modifier) | `150,170,255` | Modifier | Ctrl/Alt/Shift/Meta, held or one-shot (`OSM(...)`) alike — all 4 OSM variants share this one color now, not 4 distinct ones |
| light orange (special) | `28,140,255` | Special | a unique, non-obvious mechanism that doesn't fit the other 3 — omnibar, the Windows+Shift+S screenshot shortcut, `ALT_TAB`, the gaming layer's `GAME_CTL`/`GAME_TAB` pair |

Two sanctioned exceptions, both requested explicitly — don't extend this
pattern elsewhere without being asked:
- **Layer-identity strip**: the `1`-`5` number row is forced to one solid
  color per layer (overriding whatever category its actual keycode would
  otherwise earn), so you can tell which layer is active on the physical
  keyboard at a glance. Base = plain white (`0,0,255`), Symlayer = blue
  (`170,150,255`), ArrowFN = orange (`28,200,255`), Gaming = red
  (`0,200,255`), Numpad = teal (`135,210,255`). This is a real firmware
  lighting feature, not just a diagram artifact — it's set directly in
  `ledmap[]` for every layer.
- **ArrowFN's F-keys** are the same blue as the identity strip
  (`170,150,255`), deliberately distinct from modifier-blue, to set them
  apart from the white arrow keys on that layer.

All saturations are deliberately kept in the ~140-210 range, not maxed at
255 — the user explicitly prefers this softer look over harsh fully-
saturated colors (confirmed preference, not a default).

When a new key needs a color, pick the category by what the key *is*, not
by what layer it's on: a modifier is always modifier-blue regardless of
layer, a layer-switch key is always layer-green, and only genuinely unique
one-off mechanisms get special-orange. Don't invent a new color for "this
layer's theme" outside the two sanctioned exceptions above.

## Alt-Tab mechanics (there are two independent implementations)

**Symlayer (layer 1)**: the Tab key there is the custom keycode `ALT_TAB`.
Pressing it registers `KC_LALT` (if not already registered) and taps
`KC_TAB`; the `case MO(1):` handler in `process_record_user` releases
`KC_LALT` when the layer-hold thumb key is released. This is the "usual
motion" referenced elsewhere in this doc: hold the thumb, tap Tab, release
to select — zero delay, because nothing is predicted in advance, only
decided retroactively on release.

**Gaming (layer 3)**: a different mechanism, `GAME_CTL` (the left-thumb key)
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
   sensitive, though — that's why the Gaming layer moved away from it.

## Gaming layer (3) constraints — read before changing anything on it

- **Left-hand only.** The right hand is on the mouse. Never put a gaming-
  layer binding on the right half of the board or the right thumb cluster —
  this was tried and explicitly rejected.
- **No hand repositioning off WASD.** Modifiers must stay within the
  pinky's reach on the leftmost column (where Tab/home-row/Shift already
  sit) or the thumb cluster. Putting things on the top row above Q/W was
  tried and rejected — it requires lifting the whole hand off the WASD
  resting position, which defeats the point.
- **Alt-Tab must use the thumb-hold + Tab-tap gesture**, matching
  Symlayer's muscle memory, not a finger-key hold. This is why Ctrl/Alt
  ended up on `GAME_CTL`/`GAME_TAB` (thumb) rather than a home-row key.

Current layout on the Gaming layer: Space = left-inner thumb, `GAME_CTL`
(Ctrl, or Alt-Tab when combined with Tab) = left-outer thumb, standalone
Alt = home row below Tab, Escape = top-left (plain, inherited from layer 0
— there's no dedicated layer-shift key on this layer), Backspace = top-
right corner (explicitly redeclared the same as layer 0 — functionally
present, but **not lit**, since it's identical to the base layer rather
than something this layer changed; see "flow-through" below for the
general principle).

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
1/2/4 automatically; Gaming has it set explicitly instead since that corner
position needs a non-transparent value there for unrelated reasons, but
it's still functionally identical to layer 0's Backspace). When adding a
new universally-useful key, prefer setting it on layer 0 and letting it
flow down over repeating it on every layer.

Lighting does NOT flow through automatically the way keycodes do —
`ledmap[]` is per-layer and independent. But per the lighting philosophy
above, don't just mechanically copy a key's base-layer color onto every
layer that inherits it either: **only light it on a layer if that layer's
value is actually different from layer 0** (whether via real transparency
or an explicit-but-identical redeclaration, like Gaming's Backspace). If
it's the same as the base layer, leave it dark — that sameness is the
whole signal "nothing changed here."

## Porting to a new board (the Voyager → Moonlander mapping)

The Moonlander's `LAYOUT_moonlander`/`LAYOUT` macro (in
`keyboards/zsa/moonlander/reva/keyboard.json`) has 72 argument positions
vs. the Voyager's 52: each half gets an extra pinky column, an extra
bottom row, and a 4-key thumb cluster (vs. 2). Justin's request when
porting was "exact same layout" with the extra keys left idle, specifically:

- the 3-key inner-edge column per half (the column nearest the thumb
  cluster/center gap, rows 0-2 — matrix col 6 on the left half, col 0 on
  the right)
- the entire bottom main row per half (including the big wide key under
  the pinky column)
- the innermost (closest to the center gap) of each half's 3 regular
  thumb-cluster keys. The outer two are the real thumb keys — these are
  the same two physical keys Justin's actual Moonlander layout already
  uses for Ctrl/Meta on the left and Enter/Space-ish keys on the right, so
  the port reuses the slots his muscle memory already expects rather than
  the innermost two (which don't match his existing habits).

This gives a clean, total 1:1 mapping (52 used + 20 unused = 72) with zero
ambiguity — every real Voyager key has exactly one Moonlander home, and
every leftover Moonlander key is unused. The mapping (Moonlander argument
position → Voyager argument position, both 0-indexed, left-to-right
top-to-bottom thumbs-last within each board's own `LAYOUT_xxx(...)` order)
is hardcoded as `MOONLANDER_TO_VOYAGER` in `scripts/generate_moonlander.py`:

| Moonlander row | Moonlander positions | Voyager positions | Notes |
|---|---|---|---|
| row 0 | 0-5 | 0-5 | Esc,1,2,3,4,5 |
| row 0 | 6,7 | — | unused (inner-edge pair) |
| row 0 | 8-13 | 6-11 | 6,7,8,9,0,Bksp |
| row 1 | 14-19 | 12-17 | Tab,Q,W,E,R,T |
| row 1 | 20,21 | — | unused |
| row 1 | 22-27 | 18-23 | Y,U,I,O,P,\\ |
| row 2 | 28-33 | 24-29 | Meta,A,S,D,F,G |
| row 2 | 34,35 | — | unused |
| row 2 | 36-41 | 30-35 | H,J,K,L,;,' |
| row 3 | 42-47 | 36-41 | Shift,Z,X,C,V,B (no edge keys on this row) |
| row 3 | 48-53 | 42-47 | N,M,,,.,/,Shift |
| row 4 | 54-65 | — | unused (whole bottom row, both halves + big wide keys) |
| thumb | 66,67 | 48,49 | Ctrl, `LR 1` (left outer, left middle) |
| thumb | 68 | — | unused (left inner/innermost thumb key) |
| thumb | 69 | — | unused (right inner/innermost thumb key) |
| thumb | 70,71 | 50,51 | Enter, Space (right middle, right outer) |

Everything that isn't the two `keymaps[]`/`ledmap[]` arrays — the custom
keycode enum, combo definitions, `process_combo_event`, Alt-Tab/
`GAME_CTL`/`GAME_TAB` logic, `set_layer_color`/`rgb_matrix_indicators_user`
— is copied verbatim by `scripts/generate_moonlander.py` from
`keymap/keymap.c`; none of it is keyboard-specific. Combos in particular
transfer with zero changes, since QMK combos trigger on keycodes, not
physical position.

If the physical choice of which key is idle in any of the above categories
needs to change, edit `MOONLANDER_TO_VOYAGER` in
`scripts/generate_moonlander.py` and re-run it (or `scripts/build.sh
moonlander`) — don't hand-edit `keymap-moonlander/keymap.c` itself, it'll
just get overwritten on the next regeneration.
