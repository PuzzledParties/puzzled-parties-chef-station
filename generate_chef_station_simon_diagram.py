from __future__ import annotations

import html
import textwrap
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent
SVG_PATH = OUT_DIR / "chef_station_simon_wiring_diagram.svg"
PNG_PATH = OUT_DIR / "chef_station_simon_wiring_diagram.png"
FZZ_PATH = OUT_DIR / "chef_station_simon_wiring_diagram.fzz"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist.md"

W, H = 3000, 2320
TOP_RAIL_Y = 160
GND_RAIL_Y = 2200

COLORS = {
    "bg": "#fbfaf7",
    "grid": "#d9d2c3",
    "ink": "#1f2933",
    "muted": "#52606d",
    "board": "#2a9d8f",
    "board_dark": "#1f756b",
    "perf": "#f1ead7",
    "perf_stroke": "#d8ccb0",
    "red": "#d71920",
    "black": "#111111",
    "yellow": "#f4b400",
    "blue": "#1e88e5",
    "green": "#178f46",
    "orange": "#f57c00",
    "purple": "#7b61ff",
    "resistor": "#e7c99a",
    "resistor_stroke": "#946b2d",
    "mosfet": "#2f343b",
    "metal": "#c7cdd4",
    "terminal": "#eef2f7",
    "terminal_stroke": "#9aa5b1",
    "white": "#ffffff",
}

BUTTONS = [
    {"n": 1, "name": "Ingredient 1", "sw": "GPIO 16", "lamp": "GPIO 21", "color": "#e53935"},
    {"n": 2, "name": "Ingredient 2", "sw": "GPIO 17", "lamp": "GPIO 22", "color": "#43a047"},
    {"n": 3, "name": "Ingredient 3", "sw": "GPIO 18", "lamp": "GPIO 23", "color": "#ffffff"},
    {"n": 4, "name": "Ingredient 4", "sw": "GPIO 19", "lamp": "GPIO 25", "color": "#fbc02d"},
    {"n": 5, "name": "Ingredient 5", "sw": "GPIO 26", "lamp": "GPIO 27", "color": "#1e88e5"},
]

ROWS = [400, 640, 880, 1120, 1360]


def find_font(bold: bool = False) -> str | None:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return item
    return None


FONT_REGULAR = find_font(False)
FONT_BOLD = find_font(True)


def pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_file = FONT_BOLD if bold else FONT_REGULAR
    if font_file:
        return ImageFont.truetype(font_file, size)
    return ImageFont.load_default()


class Diagram:
    def __init__(self) -> None:
        self.image = Image.new("RGB", (W, H), COLORS["bg"])
        self.draw = ImageDraw.Draw(self.image)
        self.svg: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            "<defs>",
            "<filter id=\"shadow\" x=\"-20%\" y=\"-20%\" width=\"140%\" height=\"140%\">",
            "<feDropShadow dx=\"0\" dy=\"3\" stdDeviation=\"4\" flood-color=\"#000000\" flood-opacity=\"0.16\"/>",
            "</filter>",
            "</defs>",
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="{COLORS["bg"]}"/>',
            '<g id="breadboard">',
        ]

    def save(self) -> None:
        self.svg.append("</g>")
        self.svg.append("</svg>")
        SVG_PATH.write_text("\n".join(self.svg), encoding="utf-8")
        self.image.save(PNG_PATH)

    def line(self, points, color, width=5, dash=None, below_svg=False):
        if len(points) < 2:
            return
        self.draw.line(points, fill=color, width=width, joint="curve")
        points_s = " ".join(f"{x},{y}" for x, y in points)
        dash_s = f' stroke-dasharray="{dash}"' if dash else ""
        el = (
            f'<polyline points="{points_s}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash_s}/>'
        )
        self.svg.append(el)

    def rect(self, xy, fill, outline=COLORS["ink"], width=2, radius=0, shadow=False):
        x1, y1, x2, y2 = xy
        if radius:
            self.draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
            shadow_s = ' filter="url(#shadow)"' if shadow else ""
            self.svg.append(
                f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" rx="{radius}" '
                f'fill="{fill}" stroke="{outline}" stroke-width="{width}"{shadow_s}/>'
            )
        else:
            self.draw.rectangle(xy, fill=fill, outline=outline, width=width)
            shadow_s = ' filter="url(#shadow)"' if shadow else ""
            self.svg.append(
                f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" '
                f'fill="{fill}" stroke="{outline}" stroke-width="{width}"{shadow_s}/>'
            )

    def ellipse(self, xy, fill, outline=COLORS["ink"], width=2):
        x1, y1, x2, y2 = xy
        self.draw.ellipse(xy, fill=fill, outline=outline, width=width)
        self.svg.append(
            f'<ellipse cx="{(x1 + x2) / 2}" cy="{(y1 + y2) / 2}" rx="{(x2 - x1) / 2}" '
            f'ry="{(y2 - y1) / 2}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>'
        )

    def circle(self, x, y, r, fill, outline=COLORS["ink"], width=2):
        self.ellipse((x - r, y - r, x + r, y + r), fill, outline, width)

    def text(self, x, y, s, size=28, fill=COLORS["ink"], bold=False, anchor="lt", max_width=None, line_height=1.18):
        if max_width is not None:
            chars = max(8, int(max_width / (size * 0.54)))
            lines: list[str] = []
            for paragraph in str(s).split("\n"):
                wrapped = textwrap.wrap(paragraph, width=chars) or [""]
                lines.extend(wrapped)
            for idx, line in enumerate(lines):
                self.text(x, y + idx * size * line_height, line, size, fill, bold, anchor)
            return

        font = pil_font(size, bold)
        bbox = self.draw.textbbox((0, 0), str(s), font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        px, py = x, y
        svg_anchor = "start"
        baseline = "hanging"
        if "m" in anchor[0:1]:
            px -= tw / 2
            svg_anchor = "middle"
        elif "r" in anchor[0:1]:
            px -= tw
            svg_anchor = "end"
        if anchor.endswith("m"):
            py -= th / 2
            baseline = "middle"
        elif anchor.endswith("b"):
            py -= th
            baseline = "baseline"

        self.draw.text((px, py), str(s), fill=fill, font=font)
        weight = "700" if bold else "400"
        self.svg.append(
            f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{svg_anchor}" '
            f'alignment-baseline="{baseline}">{html.escape(str(s))}</text>'
        )

    def resistor_h(self, x, y, w, h, label, lead_color, other_color=None):
        cy = y + h / 2
        self.line([(x - 50, cy), (x, cy)], lead_color, 5)
        self.rect((x, y, x + w, y + h), COLORS["resistor"], COLORS["resistor_stroke"], 2, 9)
        self.line([(x + w, cy), (x + w + 50, cy)], other_color or lead_color, 5)
        self.text(x + w / 2, y + h / 2, label, 20, COLORS["ink"], True, "mm")

    def resistor_v(self, x, y, w, h, label):
        cx = x + w / 2
        self.rect((x, y, x + w, y + h), COLORS["resistor"], COLORS["resistor_stroke"], 2, 9)
        self.text(cx, y + h / 2, label, 18, COLORS["ink"], True, "mm")


def draw_perfboard(d: Diagram) -> None:
    x1, y1, x2, y2 = 600, 255, 2005, 1545
    d.rect((x1, y1, x2, y2), COLORS["perf"], COLORS["perf_stroke"], 3, 10)
    d.text(x1 + 22, y1 + 20, "Perfboard area: MOSFET low-side lamp drivers", 27, COLORS["muted"], True)
    for x in range(x1 + 35, x2 - 20, 40):
        for y in range(y1 + 80, y2 - 30, 40):
            d.circle(x, y, 3, COLORS["grid"], COLORS["grid"], 1)


def draw_title_and_rails(d: Diagram) -> None:
    d.text(70, 40, "Chef Station \"Simon\" ESP32 Illuminated Button Wiring", 42, COLORS["ink"], True)
    d.text(72, 90, "Five momentary switch inputs + five individually switched lamp outputs", 25, COLORS["muted"])

    d.line([(70, TOP_RAIL_Y), (2930, TOP_RAIL_Y)], COLORS["red"], 12)
    d.circle(260, TOP_RAIL_Y, 8, COLORS["red"], COLORS["red"], 1)
    d.rect((275, 116, 1145, 150), COLORS["bg"], COLORS["bg"], 1)
    d.text(285, 119, "+12V lamp supply rail - shared lamp positives only", 28, COLORS["red"], True)

    d.line([(70, GND_RAIL_Y), (2930, GND_RAIL_Y)], COLORS["black"], 12)
    d.circle(260, GND_RAIL_Y, 8, COLORS["black"], COLORS["black"], 1)
    d.rect((275, GND_RAIL_Y - 72, 1535, GND_RAIL_Y - 36), COLORS["bg"], COLORS["bg"], 1)
    d.text(
        285,
        GND_RAIL_Y - 69,
        "COMMON GROUND RAIL: ESP32 GND + supply - + switch GND + MOSFET sources",
        26,
        COLORS["black"],
        True,
    )


def draw_supply(d: Diagram) -> None:
    x, y, w, h = 80, 180, 285, 120
    d.rect((x, y, x + w, y + h), COLORS["white"], COLORS["terminal_stroke"], 3, 10, True)
    d.text(x + w / 2, y + 28, "External 12V", 27, COLORS["ink"], True, "mm")
    d.text(x + w / 2, y + 55, "lamp supply", 22, COLORS["ink"], True, "mm")
    d.circle(x + 74, y + 88, 12, COLORS["red"], COLORS["ink"], 2)
    d.circle(x + 210, y + 88, 12, COLORS["black"], COLORS["ink"], 2)
    d.text(x + 74, y + 111, "+", 25, COLORS["red"], True, "mm")
    d.text(x + 210, y + 111, "-", 25, COLORS["black"], True, "mm")
    d.line([(x + 74, y + 88), (x + 74, TOP_RAIL_Y)], COLORS["red"], 6)
    d.line([(x + 210, y + 88), (x + 210, GND_RAIL_Y)], COLORS["black"], 6)


def draw_esp32(d: Diagram) -> None:
    x, y, w, h = 110, 300, 440, 1260
    d.rect((x, y, x + w, y + h), COLORS["board"], COLORS["board_dark"], 5, 20, True)
    d.rect((x + 125, y + 25, x + 315, y + 82), COLORS["metal"], COLORS["board_dark"], 3, 8)
    d.text(x + w / 2, y + 130, "ESP32 DevKit", 36, COLORS["white"], True, "mm")
    d.text(x + w / 2, y + 175, "Inputs: INPUT_PULLUP", 22, COLORS["white"], True, "mm")
    d.text(x + w / 2, y + 207, "unpressed = HIGH   pressed = LOW", 20, COLORS["white"], False, "mm")

    # Board side rails and ground tie.
    d.circle(x + 55, y + h - 95, 11, COLORS["black"], COLORS["white"], 2)
    d.text(x + 84, y + h - 103, "GND", 22, COLORS["white"], True)
    d.line([(x + 55, y + h - 95), (x + 55, GND_RAIL_Y)], COLORS["black"], 6)

    for item, row in zip(BUTTONS, ROWS):
        input_y = row - 64
        output_y = row + 64
        pin_x = x + w
        d.rect((pin_x - 64, input_y - 17, pin_x - 8, input_y + 17), COLORS["white"], COLORS["board_dark"], 2, 4)
        d.rect((pin_x - 64, output_y - 17, pin_x - 8, output_y + 17), COLORS["white"], COLORS["board_dark"], 2, 4)
        d.text(pin_x - 78, input_y, f'{item["sw"]}  BTN{item["n"]} switch', 20, COLORS["white"], False, "rm")
        d.text(pin_x - 78, output_y, f'{item["lamp"]}  BTN{item["n"]} lamp', 20, COLORS["white"], False, "rm")


def draw_mosfet_bank_heading(d: Diagram) -> None:
    d.rect((1260, 205, 1610, 248), COLORS["white"], COLORS["terminal_stroke"], 2, 8)
    d.text(1435, 226, "TO-220 front pinout: Gate / Drain / Source", 20, COLORS["ink"], True, "mm")
    d.text(1435, 252, "tab = Drain", 18, COLORS["muted"], False, "mm")


def draw_button_module(d: Diagram, item, row: int) -> None:
    n = item["n"]
    term_x, term_w = 2170, 265
    term_y, term_h = row - 110, 220
    port_x = term_x
    right_x = term_x + term_w
    lplus_y = row - 72
    lminus_y = row - 24
    sw_y = row + 34
    gnd_y = row + 82
    center_x = 2700

    d.rect((term_x, term_y, term_x + term_w, term_y + term_h), COLORS["terminal"], COLORS["terminal_stroke"], 2, 8)
    d.text(term_x + term_w / 2, term_y + 22, f"BTN{n} terminal block", 19, COLORS["ink"], True, "mm")
    labels = [
        ("LED +", lplus_y, COLORS["red"]),
        ("LED -", lminus_y, COLORS["orange"]),
        ("SW SIG", sw_y, COLORS["yellow"]),
        ("SW GND", gnd_y, COLORS["black"]),
    ]
    for label, yy, color in labels:
        d.circle(port_x, yy, 9, color, COLORS["ink"], 2)
        d.circle(right_x, yy, 9, COLORS["white"], COLORS["terminal_stroke"], 2)
        d.text(term_x + 55, yy, label, 19, color if color != COLORS["black"] else COLORS["ink"], True, "lm")

    # Internal button representation.
    d.circle(center_x, row, 84, item["color"], COLORS["ink"], 4)
    d.circle(center_x, row, 54, "#ffffff55", COLORS["white"], 2)
    label_fill = COLORS["ink"] if item["color"] == "#ffffff" else COLORS["white"]
    d.text(center_x, row - 5, f"BTN{n}", 26, label_fill, True, "mm")
    d.text(center_x, row + 105, item["name"], 25, COLORS["ink"], True, "mm")
    d.text(center_x, row + 135, "illuminated arcade button", 18, COLORS["muted"], False, "mm")

    # Internal lamp and switch hints.
    d.line([(right_x, lplus_y), (2520, row - 52)], COLORS["red"], 4)
    d.line([(right_x, lminus_y), (2520, row - 16)], COLORS["orange"], 4)
    d.text(2525, row - 67, "lamp", 16, COLORS["ink"], True)
    d.line([(right_x, sw_y), (2520, row + 25)], COLORS["yellow"], 4)
    d.line([(right_x, gnd_y), (2520, row + 58)], COLORS["black"], 4)
    d.text(2525, row + 36, "switch", 16, COLORS["ink"], True)


def draw_driver_row(d: Diagram, item, row: int) -> None:
    n = item["n"]
    sw_pin_y = row - 64
    lamp_pin_y = row + 64
    esp_pin_x = 550

    # Button terminal coordinates.
    term_x = 2170
    lplus_y = row - 72
    lminus_y = row - 24
    sw_y = row + 34
    gnd_y = row + 82

    # Lamp positive and switch ground are shared rails.
    d.line([(2080, lplus_y), (term_x, lplus_y)], COLORS["red"], 6)
    d.circle(2080, lplus_y, 6, COLORS["red"], COLORS["red"], 1)
    d.line([(2030, gnd_y), (term_x, gnd_y)], COLORS["black"], 6)
    d.circle(2030, gnd_y, 6, COLORS["black"], COLORS["black"], 1)

    # Switch signal to ESP32 input.
    switch_route_y = row - 115
    sig_color = COLORS["yellow"] if n % 2 else COLORS["blue"]
    d.line(
        [
            (esp_pin_x, sw_pin_y),
            (665, sw_pin_y),
            (665, switch_route_y),
            (1960, switch_route_y),
            (1960, sw_y),
            (term_x, sw_y),
        ],
        sig_color,
        6,
    )
    d.text(690, switch_route_y - 22, f'BTN{n} switch -> {item["sw"]}', 18, sig_color, True)

    # Gate control from ESP32 to MOSFET through 100 ohm resistor.
    gate_line_y = row + 64
    resistor_x, resistor_y = 785, gate_line_y - 16
    d.line([(esp_pin_x, lamp_pin_y), (resistor_x - 50, lamp_pin_y)], COLORS["green"], 6)
    d.resistor_h(resistor_x, resistor_y, 130, 32, "100 ohm", COLORS["green"])
    gate_node = (1168, row + 84)
    mos_x = 1280
    gate_pin = (mos_x + 35, row + 84)
    d.line([(resistor_x + 180, lamp_pin_y), (gate_node[0], lamp_pin_y), gate_node, gate_pin], COLORS["green"], 6)
    d.circle(*gate_node, 7, COLORS["green"], COLORS["green"], 1)
    d.text(930, gate_line_y - 42, f'{item["lamp"]} lamp PWM/flash', 18, COLORS["green"], True)

    # 10k gate pulldown resistor.
    d.line([gate_node, (1210, gate_node[1]), (1210, row + 106)], COLORS["green"], 5)
    d.resistor_v(1188, row + 106, 44, 72, "10k")
    d.line([(1210, row + 178), (1210, row + 198), (1515, row + 198)], COLORS["black"], 5)
    d.text(1242, row + 142, "gate pulldown", 16, COLORS["muted"], False)

    # MOSFET body and pins.
    body_x, body_y, body_w, body_h = mos_x, row - 58, 150, 106
    d.rect((body_x + 34, body_y - 28, body_x + 116, body_y + 8), COLORS["metal"], COLORS["mosfet"], 2, 4)
    d.rect((body_x, body_y, body_x + body_w, body_y + body_h), COLORS["mosfet"], COLORS["black"], 3, 10)
    d.circle(body_x + body_w / 2, body_y + 24, 10, COLORS["metal"], COLORS["black"], 1)
    d.text(body_x + body_w / 2, body_y + 55, f"Q{n}", 22, COLORS["white"], True, "mm")
    d.text(body_x + body_w / 2, body_y + 82, "IRFB11N50APBF", 15, COLORS["white"], False, "mm")

    pin_y1 = body_y + body_h
    pin_y2 = row + 84
    gate_x, drain_x, source_x = body_x + 35, body_x + 75, body_x + 115
    for px, label in [(gate_x, "G"), (drain_x, "D"), (source_x, "S")]:
        d.line([(px, pin_y1), (px, pin_y2)], COLORS["metal"], 8)
        d.text(px, pin_y2 + 22, label, 17, COLORS["ink"], True, "mm")
    d.text(gate_x - 6, pin_y2 + 44, "Gate", 14, COLORS["muted"], False, "mm")
    d.text(drain_x, pin_y2 + 44, "Drain", 14, COLORS["muted"], False, "mm")
    d.text(source_x + 8, pin_y2 + 44, "Source", 14, COLORS["muted"], False, "mm")

    # Drain to individual lamp negative.
    d.line([(drain_x, pin_y2), (drain_x, lminus_y), (term_x, lminus_y)], COLORS["orange"], 6)
    d.text(1605, lminus_y - 23, f"BTN{n} individual lamp -", 17, COLORS["orange"], True)

    # Source to common ground spine.
    d.line([(source_x, pin_y2), (1515, pin_y2)], COLORS["black"], 6)
    d.circle(1515, pin_y2, 6, COLORS["black"], COLORS["black"], 1)


def draw_ground_spine(d: Diagram) -> None:
    d.line([(1515, 295), (1515, GND_RAIL_Y)], COLORS["black"], 8)
    d.circle(1515, GND_RAIL_Y, 7, COLORS["black"], COLORS["black"], 1)
    d.text(1538, 305, "MOSFET sources + pulldowns to common GND", 20, COLORS["black"], True)


def draw_button_buses(d: Diagram) -> None:
    d.line([(2080, TOP_RAIL_Y), (2080, 1475)], COLORS["red"], 7)
    d.line([(2030, 310), (2030, GND_RAIL_Y)], COLORS["black"], 7)
    d.circle(2080, TOP_RAIL_Y, 7, COLORS["red"], COLORS["red"], 1)
    d.circle(2030, GND_RAIL_Y, 7, COLORS["black"], COLORS["black"], 1)
    d.text(2105, 185, "shared lamp + feed", 20, COLORS["red"], True)
    d.text(2054, 1490, "switch GND taps", 18, COLORS["black"], True)


def draw_notes_and_legend(d: Diagram) -> None:
    note_x, note_y, note_w, note_h = 70, 1715, 1500, 160
    d.rect((note_x, note_y, note_x + note_w, note_y + note_h), COLORS["white"], COLORS["terminal_stroke"], 2, 10)
    d.text(note_x + 22, note_y + 20, "Visible wiring notes", 25, COLORS["ink"], True)
    note = (
        "All grounds must be common. Do not connect lamp negatives together if individual flashing is required. "
        "Shared +V is OK; switched low side controls each lamp. Use INPUT_PULLUP for button inputs. "
        "These uxcell buttons use 12V LEDs; observe LED polarity."
    )
    d.text(note_x + 22, note_y + 58, note, 21, COLORS["ink"], False, max_width=note_w - 44)

    mos_note_x, mos_note_y, mos_note_w, mos_note_h = 70, 1595, 1500, 105
    d.rect((mos_note_x, mos_note_y, mos_note_x + mos_note_w, mos_note_y + mos_note_h), "#fff7ed", "#d97706", 2, 10)
    d.text(mos_note_x + 22, mos_note_y + 18, "MOSFET note", 25, "#9a3412", True)
    mos_note = (
        "IRFB11N50APBF is overkill and not logic-level, but acceptable for small lamp loads; "
        "replace with a logic-level MOSFET if lamps do not fully turn on."
    )
    d.text(mos_note_x + 22, mos_note_y + 54, mos_note, 21, COLORS["ink"], False, max_width=mos_note_w - 44)

    legend_x, legend_y, legend_w, legend_h = 1660, 1595, 1270, 280
    d.rect((legend_x, legend_y, legend_x + legend_w, legend_y + legend_h), COLORS["white"], COLORS["terminal_stroke"], 2, 10)
    d.text(legend_x + 22, legend_y + 22, "Legend", 27, COLORS["ink"], True)
    legend_lines = [
        (COLORS["red"], "red", "shared +5V/lamp supply positive"),
        (COLORS["black"], "black", "common ground"),
        (COLORS["yellow"], "yellow/blue", "switch signal to ESP32 input"),
        (COLORS["green"], "green", "ESP32 lamp output to MOSFET gate"),
        (COLORS["orange"], "orange", "individual lamp negative to MOSFET drain"),
    ]
    for idx, (color, name, label) in enumerate(legend_lines):
        yy = legend_y + 66 + idx * 30
        d.line([(legend_x + 24, yy), (legend_x + 90, yy)], color, 7)
        d.text(legend_x + 105, yy - 12, f"{name}: {label}", 19, COLORS["ink"], False)
    side_note = "Switch side: one switch terminal to GND, one to GPIO. Lamp side: LED+ to +V, LED- to MOSFET drain."
    d.text(legend_x + 580, legend_y + 67, side_note, 20, COLORS["ink"], False, max_width=650)


def write_checklist() -> None:
    lines = [
        "# Chef Station Simon Wiring Checklist",
        "",
        "Assumption: the prompt requested five buttons but only listed suggested pins for four, so BTN5 uses GPIO 26 for the switch input and GPIO 27 for the lamp output.",
        "",
        "Button reference used for this revision: uxcell 60mm 12V LED illuminated arcade pushbuttons with a normally-open microswitch and screw terminals. Use a 12V lamp supply for these specific LED modules.",
        "",
        "## Pin Map",
        "",
        "| Button | Switch input | Lamp gate output |",
        "| --- | --- | --- |",
    ]
    for item in BUTTONS:
        lines.append(f'| BTN{item["n"]} / {item["name"]} | {item["sw"]} | {item["lamp"]} |')
    lines.extend(
        [
            "",
            "## Wiring",
            "",
            "- Tie ESP32 GND, external lamp supply negative, all switch ground terminals, MOSFET sources, and all 10k pulldown ground ends to the common ground rail.",
            "- Feed every LED/lamp positive from the shared +12V lamp rail for the linked uxcell buttons. If you substitute 5V illuminated buttons, use the matching 5V lamp rail instead.",
            "- Run each lamp negative separately to its own MOSFET drain. Do not tie lamp negatives together.",
            "- Connect each MOSFET source to common ground.",
            "- Connect each ESP32 lamp GPIO to its MOSFET gate through a 100 ohm resistor.",
            "- Add a 10k resistor from each MOSFET gate to common ground.",
            "- Wire each button switch with one side to GND and the other side to its ESP32 input GPIO.",
            "- Configure each button input as INPUT_PULLUP in firmware: unpressed = HIGH, pressed = LOW.",
            "- Observe LED polarity on the arcade button lamp terminals; if an LED does not light, swap its LED + and LED - leads.",
            "- IRFB11N50APBF can work for small lamp loads, but it is not a logic-level MOSFET. If lamps are dim or do not fully turn on, replace it with a logic-level N-channel MOSFET.",
        ]
    )
    CHECKLIST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_fritzing_sketch() -> None:
    base_svg = SVG_PATH.read_text(encoding="utf-8")
    layer_svgs = {
        "breadboard": base_svg,
        "icon": base_svg.replace('id="breadboard"', 'id="icon"', 1),
        "schematic": base_svg.replace('id="breadboard"', 'id="schematic"', 1),
        "pcb": base_svg.replace('id="breadboard"', 'id="silkscreen"', 1),
    }
    fzp = """<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="chef_station_simon_wiring_diagram_part">
  <version>1</version>
  <author>OpenAI Codex</author>
  <title>Chef Station Simon ESP32 Wiring Diagram</title>
  <label>SIMON</label>
  <date>2026-05-23</date>
  <tags>
    <tag>ESP32</tag>
    <tag>Simon</tag>
    <tag>arcade button</tag>
    <tag>MOSFET</tag>
    <tag>wiring diagram</tag>
  </tags>
  <properties>
    <property name="family">Wiring Diagram</property>
    <property name="lamp supply">12V for linked uxcell buttons</property>
    <property name="control">ESP32 GPIO with N-channel MOSFET low-side switches</property>
  </properties>
  <description>Annotated breadboard-style wiring diagram for five illuminated arcade buttons controlled by an ESP32.</description>
  <views>
    <iconView>
      <layers image="icon/chef_station_simon_wiring_diagram.svg">
        <layer layerId="icon"/>
      </layers>
    </iconView>
    <breadboardView>
      <layers image="breadboard/chef_station_simon_wiring_diagram.svg">
        <layer layerId="breadboard"/>
      </layers>
    </breadboardView>
    <schematicView>
      <layers image="schematic/chef_station_simon_wiring_diagram.svg">
        <layer layerId="schematic"/>
      </layers>
    </schematicView>
    <pcbView>
      <layers image="pcb/chef_station_simon_wiring_diagram.svg">
        <layer layerId="silkscreen"/>
      </layers>
    </pcbView>
  </views>
  <connectors/>
</module>
"""
    fz = """<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" icon=".png">
  <project_properties>
    <simulator_animation_time_s value="5s"/>
    <simulator_number_of_steps value="400"/>
    <simulator_time_step_mode value="false"/>
    <simulator_time_step_s value="1us"/>
  </project_properties>
  <views>
    <view name="breadboardView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="0" alignToGrid="0" viewFromBelow="0" colorWiresByLength="0"/>
    <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="0" alignToGrid="1" viewFromBelow="0"/>
    <view name="pcbView" backgroundColor="#ffffff" gridSize="0.05in" showGrid="0" alignToGrid="1" viewFromBelow="0" autorouteViaHoleSize="" autorouteTraceWidth="24" GPG_Keepout="" autorouteViaRingThickness="" DRC_Keepout="0.01in"/>
  </views>
  <instances>
    <instance moduleIdRef="chef_station_simon_wiring_diagram_part" modelIndex="1001" path="part.chef_station_simon_wiring_diagram_part.fzp">
      <title>Chef Station Simon ESP32 Wiring Diagram</title>
      <views>
        <breadboardView layer="breadboard">
          <geometry z="1" x="0" y="0"/>
        </breadboardView>
        <schematicView layer="schematic">
          <geometry z="1" x="0" y="0"/>
        </schematicView>
        <pcbView layer="silkscreen">
          <geometry z="1" x="0" y="0"/>
        </pcbView>
      </views>
    </instance>
  </instances>
</module>
"""
    with zipfile.ZipFile(FZZ_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("chef_station_simon_wiring_diagram.fz", fz)
        zf.writestr("part.chef_station_simon_wiring_diagram_part.fzp", fzp)
        zf.writestr("svg.breadboard.chef_station_simon_wiring_diagram.svg", layer_svgs["breadboard"])
        zf.writestr("svg.icon.chef_station_simon_wiring_diagram.svg", layer_svgs["icon"])
        zf.writestr("svg.schematic.chef_station_simon_wiring_diagram.svg", layer_svgs["schematic"])
        zf.writestr("svg.pcb.chef_station_simon_wiring_diagram.svg", layer_svgs["pcb"])


def main() -> None:
    d = Diagram()
    draw_title_and_rails(d)
    draw_perfboard(d)
    draw_supply(d)
    draw_ground_spine(d)
    draw_button_buses(d)
    draw_esp32(d)
    draw_mosfet_bank_heading(d)
    for item, row in zip(BUTTONS, ROWS):
        draw_driver_row(d, item, row)
        draw_button_module(d, item, row)
    draw_notes_and_legend(d)
    d.save()
    write_checklist()
    make_fritzing_sketch()
    print(f"Wrote {SVG_PATH}")
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {FZZ_PATH}")
    print(f"Wrote {CHECKLIST_PATH}")


if __name__ == "__main__":
    main()
