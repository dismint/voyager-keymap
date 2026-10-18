#!/usr/bin/env python3
"""
Render SVG diagrams of every layer in keymap/keymap.c, matching the Voyager's
physical key layout and the actual configured RGB colors, then splice them
into README.md between the LAYOUT:START/LAYOUT:END markers.

This reads keymap.c directly (not a hand-maintained description of it), so
it can't drift from what's actually flashed. Run it after any keymap change:

    ./scripts/render_layouts.py

Only the layer name map below (LAYER_NAMES) and the keycode label map
(LABELS) need manual upkeep — everything else is derived from the source.
"""
import colorsys
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

REPO_DIR = Path(__file__).resolve().parent.parent
QMK_FIRMWARE = Path.home() / "qmk_firmware"
KEYMAP_C = REPO_DIR / "keymap" / "keymap.c"
README = REPO_DIR / "README.md"
LAYOUT_DIR = REPO_DIR / "layout"
KEYBOARD_JSON = QMK_FIRMWARE / "keyboards/zsa/voyager/keyboard.json"

# update this if layers are added, removed, or repurposed. these are the
# canonical layer names used everywhere (README, images, CLAUDE.md prose).
LAYER_NAMES = {
    0: "Base",
    1: "Symlayer",
    2: "ArrowFN",
    3: "Gaming",
    4: "Numpad",
}

# how to render each keycode token. unmapped tokens fall back to a stripped
# raw form, so new keycodes won't crash this -- just look less polished.
LABELS = {
    "KC_TRANSPARENT": "",
    "KC_ESCAPE": "Esc",
    "KC_TAB": "Tab",
    "KC_LEFT_GUI": "Meta",
    "KC_LEFT_SHIFT": "Shift",
    "KC_RIGHT_SHIFT": "Shift",
    "KC_LEFT_CTRL": "Ctrl",
    "KC_LEFT_ALT": "Alt",
    "KC_RIGHT_GUI": "Meta",
    "KC_ENTER": "Enter",
    "KC_SPACE": "Space",
    "KC_BSPC": "Bksp",
    "KC_BSLS": "\\",
    "KC_SCLN": ";",
    "KC_QUOTE": "'",
    "KC_COMMA": ",",
    "KC_DOT": ".",
    "KC_SLASH": "/",
    "KC_PLUS": "+",
    "KC_EQUAL": "=",
    "KC_EXLM": "!",
    "KC_LCBR": "{",
    "KC_RCBR": "}",
    "KC_AT": "@",
    "KC_PERC": "%",
    "KC_CIRC": "^",
    "KC_HASH": "#",
    "KC_LPRN": "(",
    "KC_RPRN": ")",
    "KC_MINUS": "-",
    "KC_UNDS": "_",
    "KC_ASTR": "*",
    "KC_DLR": "$",
    "KC_LBRC": "[",
    "KC_RBRC": "]",
    "KC_GRAVE": "`",
    "KC_TILD": "~",
    "KC_AMPR": "&",
    "OSM(MOD_LSFT)": "OSM Sft",
    "OSM(MOD_LGUI)": "OSM Meta",
    "OSM(MOD_LALT)": "OSM Alt",
    "OSM(MOD_LCTL)": "OSM Ctl",
    "LALT(LCTL(KC_SPACE))": "Omni",
    "LGUI(LSFT(KC_S))": "Snip",
    "ALT_TAB": "AltTab",
    "GAME_CTL": "Ctrl",
    "GAME_TAB": "Tab",
    "KC_LEFT": "Left",
    "KC_RIGHT": "Right",
    "KC_UP": "Up",
    "KC_DOWN": "Down",
    "KC_CAPS": "Caps Lock",
}

# one marker color per combo, assigned by combo definition order. add more
# if a 7th+ combo ever shows up.
COMBO_COLORS = ["#ff4fd8", "#4fd8ff", "#ffd84f", "#9d4fff", "#4fff9d", "#ff8a4f"]

# which layer's diagram shows each combo's dot marker, keyed by the combo's
# variable name in keymap.c (e.g. "combo0"). combos not listed here default
# to layer 0. this is purely a display choice -- doesn't affect the "Works
# on" column, which is computed from the actual keymap regardless.
COMBO_DISPLAY_LAYER = {}
DEFAULT_COMBO_DISPLAY_LAYER = 0

CANVAS_PAD = 20
UNIT = 58
KEY_SIZE = 50
LEGEND_LINE_HEIGHT = 20
LEGEND_PAD = 16


def label_for(token):
    if token in LABELS:
        return LABELS[token]
    m = re.match(r"^MO\((\d+)\)$", token)
    if m:
        return f"LR {m.group(1)}"
    m = re.match(r"^TG\((\d+)\)$", token)
    if m:
        return f"TO {m.group(1)}"
    m = re.match(r"^KC_([A-Z0-9]+)$", token)
    if m:
        return m.group(1).capitalize()
    return token.replace("KC_", "").replace("_", " ").strip()[:8]


def split_top_level(s):
    """split on commas at depth 0, tracking both () and {} nesting"""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def extract_balanced(s, start, open_ch="(", close_ch=")"):
    """s[start] must be open_ch; returns the content between it and its match"""
    assert s[start] == open_ch, f"expected {open_ch!r} at {start}, got {s[start]!r}"
    depth = 0
    for i in range(start, len(s)):
        if s[i] == open_ch:
            depth += 1
        elif s[i] == close_ch:
            depth -= 1
            if depth == 0:
                return s[start + 1:i]
    raise ValueError("unbalanced delimiters")


def parse_layers(text, array_name):
    """returns {layer_index: [52 raw tokens]}, scanning only within this
    array's own declaration so it can't bleed into a different array below it"""
    name_pos = text.index(f"{array_name}[]")
    eq_pos = text.index("=", name_pos)
    open_brace = text.index("{", eq_pos)
    body = extract_balanced(text, open_brace, "{", "}")

    layers = {}
    for m in re.finditer(r"\[(\d+)\]\s*=\s*(LAYOUT_voyager|\{)", body):
        idx = int(m.group(1))
        abs_pos = m.end() - 1
        if m.group(2) == "LAYOUT_voyager":
            open_paren = body.index("(", abs_pos)
            content = extract_balanced(body, open_paren, "(", ")")
        else:
            content = extract_balanced(body, abs_pos, "{", "}")
        tokens = split_top_level(content)
        if len(tokens) == 52:
            layers[idx] = tokens
    return layers


def parse_combos(text):
    """returns [(combo_name, [trigger keycode tokens], action token), ...]"""
    combo_defs = {}
    for m in re.finditer(r"const uint16_t PROGMEM (\w+)\[\] = \{([^}]*)\};", text):
        name = m.group(1)
        toks = [t.strip() for t in m.group(2).split(",")]
        combo_defs[name] = [t for t in toks if t and t != "COMBO_END"]

    kc_pos = text.index("key_combos[")
    open_brace = text.index("{", kc_pos)
    body = extract_balanced(text, open_brace, "{", "}")

    combos = []
    for m in re.finditer(r"COMBO\(", body):
        content = extract_balanced(body, m.end() - 1, "(", ")")
        name, action = split_top_level(content)[:2]
        if name in combo_defs:
            combos.append((name, combo_defs[name], action))
    return combos


def describe_action(token):
    """friendlier prose form of an action keycode, for the combos list"""
    m = re.match(r"^MO\((\d+)\)$", token)
    if m:
        n = int(m.group(1))
        return f"Hold layer {n} ({LAYER_NAMES.get(n, n)})"
    m = re.match(r"^TG\((\d+)\)$", token)
    if m:
        n = int(m.group(1))
        return f"Toggle layer {n} ({LAYER_NAMES.get(n, n)})"
    return label_for(token)


def hsv_to_hex(h, s, v):
    if h == 0 and s == 0 and v == 0:
        return "#1a1a1a"  # unlit key, rendered as dark-but-visible, not pure black
    r, g, b = colorsys.hsv_to_rgb(h / 255, s / 255, v / 255)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def luminance(hexcolor):
    r = int(hexcolor[1:3], 16)
    g = int(hexcolor[3:5], 16)
    b = int(hexcolor[5:7], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def main():
    with open(KEYBOARD_JSON) as f:
        kb = json.load(f)
    arg_to_matrix = [tuple(e["matrix"]) for e in kb["layouts"]["LAYOUT"]["layout"]]
    coords = [(e["x"], e["y"]) for e in kb["layouts"]["LAYOUT"]["layout"]]
    matrix_to_led = {tuple(e["matrix"]): i for i, e in enumerate(kb["rgb_matrix"]["layout"])}
    arg_to_led = [matrix_to_led[m] for m in arg_to_matrix]

    text = KEYMAP_C.read_text()
    keymap_layers = parse_layers(text, "keymaps")
    led_layers = parse_layers(text, "ledmap")
    combos = parse_combos(text)

    LAYOUT_DIR.mkdir(exist_ok=True)
    max_x = max(x for x, y in coords) + 1
    max_y = max(y for x, y in coords) + 1
    width = max_x * UNIT + CANVAS_PAD * 2
    height = max_y * UNIT + CANVAS_PAD * 2

    base_tokens = keymap_layers.get(0)

    # a combo's trigger keycodes only still produce themselves on a layer if
    # nothing on that layer remaps the physical keys involved (checking only
    # a one-level fallback to layer 0, same simplification used for
    # "inherited" key labels below -- doesn't model multi-layer nesting chains)
    # this is used for the "Works on" column -- it's informational, separate
    # from which single layer's diagram actually shows the dot marker.
    combo_positions = [[base_tokens.index(k) for k in keys] for _, keys, _ in combos]
    valid_layers_by_combo = [[] for _ in combos]
    for layer_idx, layer_tokens in keymap_layers.items():
        for ci, (positions, (name, keys, action)) in enumerate(zip(combo_positions, combos)):
            effective = [layer_tokens[p] if layer_tokens[p] != "KC_TRANSPARENT" else base_tokens[p]
                         for p in positions]
            if effective == keys:
                valid_layers_by_combo[ci].append(layer_idx)

    # one chosen layer per combo gets the dot marker(s), for a clean diagram.
    # tracks WHICH combo indices land on each position (a key in N combos
    # gets N dots), not just whether any combo touches it.
    combo_indices_by_layer = {idx: {} for idx in keymap_layers}
    combos_shown_by_layer = {idx: [] for idx in keymap_layers}
    for ci, (positions, (name, keys, action)) in enumerate(zip(combo_positions, combos)):
        display_layer = COMBO_DISPLAY_LAYER.get(name, DEFAULT_COMBO_DISPLAY_LAYER)
        combos_shown_by_layer.setdefault(display_layer, []).append(ci)
        for p in positions:
            combo_indices_by_layer.setdefault(display_layer, {}).setdefault(p, []).append(ci)

    for layer_idx in sorted(keymap_layers):
        tokens = keymap_layers[layer_idx]
        colors = led_layers.get(layer_idx)
        legend_combos = combos_shown_by_layer.get(layer_idx, [])
        layer_height = height + (LEGEND_PAD + len(legend_combos) * LEGEND_LINE_HEIGHT if legend_combos else 0)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{layer_height}" '
               f'viewBox="0 0 {width} {layer_height}" font-family="monospace">']
        svg.append(f'<rect width="100%" height="100%" fill="#0d0d0d"/>')
        for argpos, token in enumerate(tokens):
            x, y = coords[argpos]
            px = CANVAS_PAD + x * UNIT
            py = CANVAS_PAD + y * UNIT
            if colors is not None:
                h, s, v = (int(c) for c in colors[arg_to_led[argpos]].strip("{}").split(","))
            else:
                h, s, v = 0, 0, 0
            fill = hsv_to_hex(h, s, v)
            text_color = "#000000" if luminance(fill) > 140 else "#e8e8e8"

            inherited = False
            display_token = token
            if token == "KC_TRANSPARENT" and layer_idx != 0 and base_tokens is not None:
                display_token = base_tokens[argpos]
                inherited = True

            label = label_for(display_token)
            svg.append(
                f'<rect x="{px}" y="{py}" width="{KEY_SIZE}" height="{KEY_SIZE}" rx="8" '
                f'fill="{fill}" stroke="#444" stroke-width="1"/>'
            )
            if label:
                fs = 11 if len(label) <= 5 else (9 if len(label) <= 7 else 7)
                opacity = ' fill-opacity="0.45" font-style="italic"' if inherited else ""
                svg.append(
                    f'<text x="{px + KEY_SIZE/2}" y="{py + KEY_SIZE/2 + 4}" '
                    f'text-anchor="middle" font-size="{fs}" fill="{text_color}"{opacity}>{xml_escape(label)}</text>'
                )
            for dot_i, ci in enumerate(combo_indices_by_layer.get(layer_idx, {}).get(argpos, [])):
                dot_color = COMBO_COLORS[ci % len(COMBO_COLORS)]
                svg.append(
                    f'<circle cx="{px + KEY_SIZE - 7 - dot_i * 9}" cy="{py + 7}" r="4" '
                    f'fill="{dot_color}" stroke="#0d0d0d" stroke-width="1"/>'
                )

        if legend_combos:
            ly = height + LEGEND_PAD
            for ci in legend_combos:
                name, keys, action = combos[ci]
                dot_color = COMBO_COLORS[ci % len(COMBO_COLORS)]
                key_labels = " + ".join(label_for(k) for k in keys)
                legend_text = f"{key_labels} → {describe_action(action)}"
                svg.append(f'<circle cx="{CANVAS_PAD + 5}" cy="{ly - 4}" r="4" fill="{dot_color}"/>')
                svg.append(
                    f'<text x="{CANVAS_PAD + 16}" y="{ly}" font-size="12" fill="#e8e8e8">'
                    f'{xml_escape(legend_text)}</text>'
                )
                ly += LEGEND_LINE_HEIGHT

        svg.append("</svg>")
        out_path = LAYOUT_DIR / f"layer{layer_idx}.svg"
        out_path.write_text("\n".join(svg))
        print(f"wrote {out_path}")

    # splice the image embeds into README.md between the markers
    section_lines = ["<!-- LAYOUT:START (generated by scripts/render_layouts.py — do not hand-edit) -->", ""]
    for layer_idx in sorted(keymap_layers):
        name = LAYER_NAMES.get(layer_idx, f"Layer {layer_idx}")
        section_lines.append(f"### Layer {layer_idx} — {name}")
        section_lines.append("")
        section_lines.append(f"![Layer {layer_idx}](layout/layer{layer_idx}.svg)")
        section_lines.append("")

    if combos:
        section_lines.append(
            "### Combos (each combo's keys + action are also drawn directly on its "
            'display layer above, next to a dot in its own color; "works on" below '
            "shows every layer it actually still fires on, which can differ from "
            "where it's drawn)"
        )
        section_lines.append("")
        section_lines.append("| | Keys | Action | Display layer | Works on |")
        section_lines.append("|---|---|---|---|---|")
        for ci, ((name, keys, action), valid_layers) in enumerate(zip(combos, valid_layers_by_combo)):
            dot = f'<span style="color:{COMBO_COLORS[ci % len(COMBO_COLORS)]}">●</span>'
            key_labels = " + ".join(label_for(k) for k in keys)
            display_layer = COMBO_DISPLAY_LAYER.get(name, DEFAULT_COMBO_DISPLAY_LAYER)
            layers_str = ", ".join(str(n) for n in sorted(valid_layers)) or "none"
            section_lines.append(
                f"| {dot} | {key_labels} | {describe_action(action)} | {display_layer} | {layers_str} |"
            )
        section_lines.append("")

    section_lines.append("<!-- LAYOUT:END -->")
    new_section = "\n".join(section_lines)

    readme = README.read_text()
    pattern = re.compile(r"<!-- LAYOUT:START.*?<!-- LAYOUT:END -->", re.DOTALL)
    if pattern.search(readme):
        readme = pattern.sub(new_section, readme)
    else:
        readme = readme.rstrip() + "\n\n## Layout\n\n" + new_section + "\n"
    README.write_text(readme)
    print(f"updated {README}")


if __name__ == "__main__":
    main()
