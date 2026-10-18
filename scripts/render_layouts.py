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

# update this if layers are added, removed, or repurposed
LAYER_NAMES = {
    0: "Base",
    1: "Symbols",
    2: "Nav / Function",
    3: "Gaming",
    4: "Numpad (nested)",
}

# how to render each keycode token. unmapped tokens fall back to a stripped
# raw form, so new keycodes won't crash this -- just look less polished.
LABELS = {
    "KC_TRANSPARENT": "",
    "KC_ESCAPE": "Esc",
    "KC_TAB": "Tab",
    "KC_LEFT_GUI": "Gui",
    "KC_LEFT_SHIFT": "Shift",
    "KC_RIGHT_SHIFT": "Shift",
    "KC_LEFT_CTRL": "Ctrl",
    "KC_LEFT_ALT": "Alt",
    "KC_RIGHT_GUI": "Gui",
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
    "OSM(MOD_LSFT)": "Sft*",
    "OSM(MOD_LGUI)": "Gui*",
    "OSM(MOD_LALT)": "Alt*",
    "OSM(MOD_LCTL)": "Ctl*",
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

COMBO_MARKER_COLOR = "#ff4fd8"

CANVAS_PAD = 20
UNIT = 58
KEY_SIZE = 50


def label_for(token):
    if token in LABELS:
        return LABELS[token]
    m = re.match(r"^MO\((\d+)\)$", token)
    if m:
        return f"Lyr{m.group(1)}"
    m = re.match(r"^TG\((\d+)\)$", token)
    if m:
        return f"Tgl{m.group(1)}"
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
    """returns [([trigger keycode tokens], action token), ...]"""
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
            combos.append((combo_defs[name], action))
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
    combo_keycodes = {kc for keys, _ in combos for kc in keys}

    LAYOUT_DIR.mkdir(exist_ok=True)
    max_x = max(x for x, y in coords) + 1
    max_y = max(y for x, y in coords) + 1
    width = max_x * UNIT + CANVAS_PAD * 2
    height = max_y * UNIT + CANVAS_PAD * 2

    base_tokens = keymap_layers.get(0)

    for layer_idx in sorted(keymap_layers):
        tokens = keymap_layers[layer_idx]
        colors = led_layers.get(layer_idx)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
               f'viewBox="0 0 {width} {height}" font-family="monospace">']
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
                fs = 11 if len(label) <= 5 else 9
                opacity = ' fill-opacity="0.45" font-style="italic"' if inherited else ""
                svg.append(
                    f'<text x="{px + KEY_SIZE/2}" y="{py + KEY_SIZE/2 + 4}" '
                    f'text-anchor="middle" font-size="{fs}" fill="{text_color}"{opacity}>{xml_escape(label)}</text>'
                )
            if layer_idx == 0 and token in combo_keycodes:
                svg.append(
                    f'<circle cx="{px + KEY_SIZE - 7}" cy="{py + 7}" r="4" '
                    f'fill="{COMBO_MARKER_COLOR}" stroke="#0d0d0d" stroke-width="1"/>'
                )
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
            f'### Combos (marked <span style="color:{COMBO_MARKER_COLOR}">●</span> on Layer 0 above)'
        )
        section_lines.append("")
        section_lines.append("| Keys | Action |")
        section_lines.append("|---|---|")
        for keys, action in combos:
            key_labels = " + ".join(label_for(k) for k in keys)
            section_lines.append(f"| {key_labels} | {describe_action(action)} |")
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
