#include QMK_KEYBOARD_H
#include "version.h"
#include "secrets.h"
#define MOON_LED_LEVEL LED_LEVEL
#ifndef ZSA_SAFE_RANGE
#define ZSA_SAFE_RANGE SAFE_RANGE
#endif

enum custom_keycodes {
  RGB_SLD = ZSA_SAFE_RANGE,
  ALT_TAB,
  GAME_CTL,
  GAME_TAB,
  RGB_LEDOFF,
  PW_DROP,
  MAGIC,
};

static bool is_alt_tab_active = false;
static bool game_ctl_held = false;
static bool game_alt_active = false;
static bool left_alt_combo_held = false;
static bool right_alt_combo_held = false;
static bool combo_alt_registered = false;
// tracks whatever keycode was most recently pressed, for the Sturdy
// layer's `magic` key (see the MAGIC case in process_record_user) --
// read BEFORE it gets updated for the current keypress, so MAGIC's own
// handler sees what came immediately before it, including a second
// consecutive MAGIC press.
static uint16_t magic_last_keycode = KC_NO;

enum combo_events {
  CAPS_COMBO = 0,
  GAMING_COMBO,
  ALT_COMBO_LEFT,
  ALT_COMBO_RIGHT,
  RGUI_COMBO,
  STURDY_ON_COMBO,
  STURDY_OFF_COMBO,
};


const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
  [0] = LAYOUT_voyager(
    KC_ESCAPE,      KC_1,           KC_2,           KC_3,           KC_4,           KC_5,                                           KC_6,           KC_7,           KC_8,           KC_9,           KC_0,           KC_BSPC,
    KC_TAB,         KC_Q,           KC_W,           KC_E,           KC_R,           KC_T,                                           KC_Y,           KC_U,           KC_I,           KC_O,           KC_P,           KC_BSLS,
    KC_LEFT_GUI,    KC_A,           KC_S,           KC_D,           KC_F,           KC_G,                                           KC_H,           KC_J,           KC_K,           KC_L,           KC_SCLN,        KC_QUOTE,
    KC_LEFT_SHIFT,  KC_Z,           KC_X,           KC_C,           KC_V,           KC_B,                                           KC_N,           KC_M,           KC_COMMA,       KC_DOT,         KC_SLASH,       KC_RIGHT_SHIFT,
                                                    KC_LEFT_CTRL,   MO(2),                                          KC_ENTER,       KC_SPACE
  ),
  [1] = LAYOUT_voyager(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_V,           KC_M,           KC_L,           KC_C,           KC_P,                                           KC_X,           KC_F,           KC_O,           KC_U,           KC_J,           KC_TRANSPARENT,
    KC_TRANSPARENT, KC_S,           KC_T,           KC_R,           KC_D,           KC_Y,                                           KC_DOT,         KC_N,           KC_A,           KC_E,           KC_I,           KC_TRANSPARENT,
    KC_TRANSPARENT, KC_Z,           KC_K,           KC_Q,           KC_G,           KC_W,                                           KC_B,           KC_H,           KC_QUOTE,       KC_SCLN,        KC_COMMA,       KC_TRANSPARENT,
                                                    KC_TRANSPARENT, KC_TRANSPARENT,                                 MAGIC,          KC_TRANSPARENT
  ),
  [2] = LAYOUT_voyager(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    ALT_TAB,        LALT(LCTL(KC_SPACE)),PW_DROP,        KC_TRANSPARENT, TG(5),          KC_PLUS,                                        KC_EXLM,        KC_LBRC,        KC_RBRC,        KC_PERC,        KC_PERC,        KC_TRANSPARENT,
    KC_TRANSPARENT, MO(3),          LGUI(LSFT(KC_S)),KC_LEFT_SHIFT,  MO(5),          KC_EQUAL,                                       KC_ASTR,        KC_LPRN,        KC_RPRN,        KC_MINUS,       KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, OSM(MOD_LSFT),  OSM(MOD_LGUI),  OSM(MOD_LALT),  OSM(MOD_LCTL),  KC_TRANSPARENT,                                 KC_DLR,         KC_LBRC,        KC_RBRC,        KC_GRAVE,       KC_SCLN,        KC_TRANSPARENT,
                                                    KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_BSPC
  ),
  [3] = LAYOUT_voyager(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, QK_BOOT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_F2,          KC_TRANSPARENT,                                 KC_F1,          KC_F2,          KC_F3,          KC_F4,          KC_F5,          KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_LEFT_SHIFT,  KC_LEFT_CTRL,   KC_TRANSPARENT,                                 KC_LEFT,        KC_DOWN,        KC_UP,          KC_RIGHT,       KC_F11,         KC_F12,
    KC_TRANSPARENT, KC_TRANSPARENT, RGB_LEDOFF,     RM_VALU,        RM_VALD,        KC_TRANSPARENT,                                 KC_F6,          KC_F7,          KC_F8,          KC_F9,          KC_F10,         KC_TRANSPARENT,
                                                    KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT
  ),
  [4] = LAYOUT_voyager(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_BSPC,
    GAME_TAB,       KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_LEFT_ALT,    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
                                                    KC_SPACE,       GAME_CTL,                                       KC_TRANSPARENT, KC_TRANSPARENT
  ),
  [5] = LAYOUT_voyager(
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_7,           KC_8,           KC_9,           KC_BSPC,        KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_4,           KC_5,           KC_6,           KC_DOT,         KC_TRANSPARENT,
    KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_1,           KC_2,           KC_3,           KC_0,           KC_TRANSPARENT,
                                                    KC_TRANSPARENT, KC_TRANSPARENT,                                 KC_TRANSPARENT, KC_TRANSPARENT
  ),
};


const uint16_t PROGMEM combo0[] = { KC_D, KC_F, COMBO_END};
const uint16_t PROGMEM combo1[] = { KC_D, KC_G, COMBO_END};
const uint16_t PROGMEM combo2[] = { KC_X, KC_C, COMBO_END};
const uint16_t PROGMEM combo3[] = { KC_COMMA, KC_DOT, COMBO_END};
const uint16_t PROGMEM combo4[] = { KC_M, KC_COMMA, COMBO_END};
const uint16_t PROGMEM combo5[] = { KC_Z, KC_SLASH, COMBO_END};
const uint16_t PROGMEM combo6[] = { KC_Z, KC_COMMA, COMBO_END};

combo_t key_combos[COMBO_COUNT] = {
    [CAPS_COMBO] = COMBO(combo0, KC_CAPS),
    [GAMING_COMBO] = COMBO(combo1, TG(4)),
    [ALT_COMBO_LEFT] = COMBO_ACTION(combo2),
    [ALT_COMBO_RIGHT] = COMBO_ACTION(combo3),
    [RGUI_COMBO] = COMBO_ACTION(combo4),
    // same two physical keys (Z + the key next to the right pinky) toggle
    // the Sturdy layer both ways -- from Base that key is "/" (Z+/ turns
    // Sturdy on), but Sturdy's own layout puts "," there instead, so the
    // way back off is Z+, (Z itself is the one letter that sits in the
    // same spot on both layouts).
    [STURDY_ON_COMBO] = COMBO(combo5, TG(1)),
    [STURDY_OFF_COMBO] = COMBO(combo6, TG(1)),
};

// X+C (left) and ,+. (right) both hold Alt for as long as EITHER combo is
// still engaged -- releasing just one of the two chord keys doesn't let go,
// only releasing both does (a combo is a single virtual key: held until
// every one of its members is back up). M+, (right hand) holds Right GUI
// the same way, independently.
void process_combo_event(uint16_t combo_index, bool pressed) {
  switch (combo_index) {
    case ALT_COMBO_LEFT:
      left_alt_combo_held = pressed;
      break;
    case ALT_COMBO_RIGHT:
      right_alt_combo_held = pressed;
      break;
    case RGUI_COMBO:
      if (pressed) {
        register_code(KC_RIGHT_GUI);
      } else {
        unregister_code(KC_RIGHT_GUI);
      }
      return;
    default:
      return;
  }
  bool should_hold = left_alt_combo_held || right_alt_combo_held;
  if (should_hold && !combo_alt_registered) {
    combo_alt_registered = true;
    register_code(KC_LALT);
  } else if (!should_hold && combo_alt_registered) {
    combo_alt_registered = false;
    unregister_code(KC_LALT);
  }
}

// Shift+Backspace sends Delete -- there's no dedicated Delete key anywhere
// in this layout otherwise.
const key_override_t delete_key_override = ko_make_basic(MOD_MASK_SHIFT, KC_BSPC, KC_DEL);

// Symlayer pairs each of these onto one key, real-keyboard style -- tap for
// the plain symbol, shift+tap for its paired one. None of the base (left)
// keycodes here are ever produced outside Symlayer, so these are safe to
// leave globally scoped rather than restricting them to one layer.
const key_override_t lbrc_lcbr_override = ko_make_basic(MOD_MASK_SHIFT, KC_LBRC, KC_LCBR);
const key_override_t rbrc_rcbr_override = ko_make_basic(MOD_MASK_SHIFT, KC_RBRC, KC_RCBR);
const key_override_t perc_at_override = ko_make_basic(MOD_MASK_SHIFT, KC_PERC, KC_AT);
const key_override_t exlm_circ_override = ko_make_basic(MOD_MASK_SHIFT, KC_EXLM, KC_CIRC);
const key_override_t astr_hash_override = ko_make_basic(MOD_MASK_SHIFT, KC_ASTR, KC_HASH);
const key_override_t dlr_ampr_override = ko_make_basic(MOD_MASK_SHIFT, KC_DLR, KC_AMPR);
const key_override_t grave_tild_override = ko_make_basic(MOD_MASK_SHIFT, KC_GRAVE, KC_TILD);
const key_override_t minus_unds_override = ko_make_basic(MOD_MASK_SHIFT, KC_MINUS, KC_UNDS);

const key_override_t *key_overrides[] = {
    &delete_key_override,
    &lbrc_lcbr_override,
    &rbrc_rcbr_override,
    &perc_at_override,
    &exlm_circ_override,
    &astr_hash_override,
    &dlr_ampr_override,
    &grave_tild_override,
    &minus_unds_override,
};



extern rgb_config_t rgb_matrix_config;

RGB hsv_to_rgb_with_value(HSV hsv) {
  RGB rgb = hsv_to_rgb( hsv );
  float f = (float)rgb_matrix_config.hsv.v / UINT8_MAX;
  return (RGB){ f * rgb.r, f * rgb.g, f * rgb.b };
}

void keyboard_post_init_user(void) {
  rgb_matrix_enable();
}

const uint8_t PROGMEM ledmap[][RGB_MATRIX_LED_COUNT][3] = {
    [0] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,160}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255}, {0,0,255} },

    [1] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255}, {191,130,255} },

    [2] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {170,130,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255}, {170,130,255} },

    [3] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {85,130,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255}, {85,130,255} },

    [4] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,140,255}, {30,140,255}, {61,140,255}, {91,140,255}, {122,140,255}, {152,140,255}, {0,140,255}, {30,140,255}, {61,140,255}, {91,140,255}, {122,140,255}, {152,140,255}, {183,140,255}, {213,140,255}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },

    [5] = { {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255}, {135,140,255} },

};

void set_layer_color(int layer) {
  for (int i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
    HSV hsv = {
      .h = pgm_read_byte(&ledmap[layer][i][0]),
      .s = pgm_read_byte(&ledmap[layer][i][1]),
      .v = pgm_read_byte(&ledmap[layer][i][2]),
    };
    if (!hsv.h && !hsv.s && !hsv.v) {
        rgb_matrix_set_color( i, 0, 0, 0 );
    } else {
        RGB rgb = hsv_to_rgb_with_value(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
  }
}

bool rgb_matrix_indicators_user(void) {
  if (rawhid_state.rgb_control) {
      return false;
  }
  if (!keyboard_config.disable_layer_led) {
    switch (biton32(layer_state)) {
      case 0:
        set_layer_color(0);
        break;
      case 1:
        set_layer_color(1);
        break;
      case 2:
        set_layer_color(2);
        break;
      case 3:
        set_layer_color(3);
        break;
      case 4:
        set_layer_color(4);
        break;
      case 5:
        set_layer_color(5);
        break;
     default:
        if (rgb_matrix_get_flags() == LED_FLAG_NONE) {
          rgb_matrix_set_color_all(0, 0, 0);
        }
    }
  } else {
    if (rgb_matrix_get_flags() == LED_FLAG_NONE) {
      rgb_matrix_set_color_all(0, 0, 0);
    }
  }

  return true;
}


bool process_record_user(uint16_t keycode, keyrecord_t *record) {
  // capture the tracker's value from BEFORE this keypress updates it, so
  // MAGIC's own handler below sees whatever came immediately before it
  // (including a second consecutive MAGIC press, which must output "n").
  uint16_t magic_prev_keycode = magic_last_keycode;
  if (record->event.pressed) {
    magic_last_keycode = keycode;
  }

  switch (keycode) {

    case MAGIC:
      // Sturdy layer's adaptive "magic" key, ported from Magic Sturdy
      // (github.com/Ikcelaks/keyboard_layouts). Output depends on
      // whichever key was typed immediately before this one; a second
      // press in a row always outputs "n" regardless of what came before
      // that first press.
      if (record->event.pressed) {
        if (magic_prev_keycode == MAGIC) {
          SEND_STRING("n");
        } else {
          switch (magic_prev_keycode) {
            case KC_A: SEND_STRING("o"); break;
            case KC_B: SEND_STRING("efore"); break;
            case KC_C: SEND_STRING("y"); break;
            case KC_D: SEND_STRING("y"); break;
            case KC_E: SEND_STRING("u"); break;
            case KC_G: SEND_STRING("y"); break;
            case KC_I: SEND_STRING("on"); break;
            case KC_J: SEND_STRING("ust"); break;
            case KC_K: SEND_STRING("s"); break;
            case KC_L: SEND_STRING("k"); break;
            case KC_M: SEND_STRING("ent"); break;
            case KC_N: SEND_STRING("ion"); break;
            case KC_O: SEND_STRING("a"); break;
            case KC_P: SEND_STRING("y"); break;
            case KC_R: SEND_STRING("l"); break;
            case KC_S: SEND_STRING("k"); break;
            case KC_T: SEND_STRING("ment"); break;
            case KC_U: SEND_STRING("e"); break;
            case KC_V: SEND_STRING("er"); break;
            case KC_W: SEND_STRING("hich"); break;
            case KC_X: SEND_STRING("es"); break;
            case KC_Y: SEND_STRING("p"); break;
            case KC_COMMA: SEND_STRING(" but"); break;
            case KC_DOT: SEND_STRING("\\"); break;
            case KC_MINUS: SEND_STRING(">"); break;
            case KC_EQUAL: SEND_STRING(">"); break;
            // "wspc": previous key was space, tab, enter, quote, or
            // left-paren -- all treated as "end of word" for this purpose
            case KC_SPACE:
            case KC_TAB:
            case KC_ENTER:
            case KC_QUOTE:
            case KC_LPRN:
              SEND_STRING("the");
              break;
            default:
              break;
          }
        }
      }
      return false;

    case RGB_SLD:
      if (record->event.pressed) {
        rgblight_mode(1);
      }
      return false;

    case RGB_LEDOFF:
      if (record->event.pressed) {
        rgb_matrix_disable();
      }
      return false;

    // brightness up/down also turns the lighting back on if it was off --
    // otherwise RGB_LEDOFF would be a one-way door.
    case RM_VALU:
    case RM_VALD:
      if (record->event.pressed && !rgb_matrix_is_enabled()) {
        rgb_matrix_enable();
      }
      return true;

    case PW_DROP:
      if (record->event.pressed) {
        SEND_STRING(PW_DROP_STRING);
      }
      return false;

    case ALT_TAB:
      if (record->event.pressed) {
        if (!is_alt_tab_active) {
          is_alt_tab_active = true;
          register_code(KC_LALT);
        }
        register_code(KC_TAB);
      } else {
        unregister_code(KC_TAB);
      }
      return false;

    case MO(2):
      if (!record->event.pressed && is_alt_tab_active) {
        unregister_code(KC_LALT);
        is_alt_tab_active = false;
      }
      return true;

    case GAME_CTL:
      if (record->event.pressed) {
        game_ctl_held = true;
        register_code(KC_LEFT_CTRL);
      } else {
        game_ctl_held = false;
        if (game_alt_active) {
          unregister_code(KC_LEFT_ALT);
          game_alt_active = false;
        } else {
          unregister_code(KC_LEFT_CTRL);
        }
      }
      return false;

    case GAME_TAB:
      if (record->event.pressed) {
        if (game_ctl_held && !game_alt_active) {
          unregister_code(KC_LEFT_CTRL);
          register_code(KC_LEFT_ALT);
          game_alt_active = true;
        }
        register_code(KC_TAB);
      } else {
        unregister_code(KC_TAB);
      }
      return false;
  }
  return true;
}
