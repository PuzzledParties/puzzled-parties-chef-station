from __future__ import annotations

import html
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "library-art"
FZZ_PATH = OUT_DIR / "chef_station_simon_4btn_audio_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_simon_4btn_audio_editable.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_4btn_audio.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")


BUTTONS = [
    {"n": 1, "name": "Ingredient 1", "sw": "GPIO 16", "lamp": "GPIO 20", "color": "red"},
    {"n": 2, "name": "Ingredient 2", "sw": "GPIO 17", "lamp": "GPIO 21", "color": "green"},
    {"n": 3, "name": "Ingredient 3", "sw": "GPIO 18", "lamp": "GPIO 22", "color": "white"},
    {"n": 4, "name": "Ingredient 4", "sw": "GPIO 19", "lamp": "GPIO 23", "color": "yellow"},
]


STOCK = {
    "resistor_1k": PARTS / "obsolete" / "resistor_1k.fzp",
    "resistor_10k": PARTS / "obsolete" / "resistor_10k.fzp",
    "mosfet": PARTS / "core" / "basic_fet_n.fzp",
    "terminal4": PARTS / "core" / "Camdenboss_CTB0158-4_5_08mm_pitch_90deg_terminals.fzp",
    "arcade_red": PARTS / "contrib" / "Arcade_Button__red___c12cc3bca053e12377a7a3c856ef34e4_24.fzp",
    "arcade_yellow": PARTS / "contrib" / "Arcade_Button__yellow___afee1ba07e56f9a78a19f30fa6b24e7f_B2.fzp",
    "arcade_white": PARTS / "contrib" / "Arcade_Button__white___56f11dd8030025047c5ba1044fac4aa2_37.fzp",
    "arcade_blue": PARTS / "contrib" / "Arcade_Button__blue___0c30cbbdde0863c5df34b75e4acddb07_20.fzp",
}


WIRE = {
    "vplus": "#d71920",
    "v5": "#f59e0b",
    "gnd": "#111111",
    "switch_a": "#f4b400",
    "switch_b": "#1e88e5",
    "gate": "#178f46",
    "lamp_minus": "#f57c00",
    "audio": "#7b1fa2",
}


@dataclass
class Part:
    key: str
    module_id: str
    fzp_name: str
    fzp: str
    svg_entries: dict[str, str]
    pins: dict[str, tuple[float, float]]


@dataclass
class Instance:
    key: str
    part: str
    title: str
    x: float
    y: float
    idx: int
    props: dict[str, str] = field(default_factory=dict)
    connects: dict[str, list[tuple[int, str]]] = field(default_factory=dict)


@dataclass
class Wire:
    idx: int
    title: str
    a: str
    ac: str
    b: str
    bc: str
    color: str
    width: float = 10


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_stock_part(key: str, fzp_path: Path, pins: dict[str, tuple[float, float]]) -> Part:
    fzp = fzp_path.read_text(encoding="utf-8", errors="replace")
    module_id = re.search(r'moduleId="([^"]+)"', fzp).group(1)
    group = fzp_path.parent.name
    svg_entries: dict[str, str] = {}
    for img in re.findall(r'<layers image="([^"]+)"', fzp):
        view, filename = img.split("/", 1)
        candidates = [
            PARTS / "svg" / group / view / filename,
            PARTS / "svg" / "core" / view / filename,
            PARTS / "svg" / "obsolete" / view / filename,
        ]
        source = next((p for p in candidates if p.exists()), candidates[0])
        svg_entries[f"svg.{view}.{filename}"] = source.read_text(encoding="utf-8", errors="replace")
    return Part(key, module_id, f"part.{module_id}.fzp", fzp, svg_entries, pins)


def make_waveshare_esp32_p4_poe_eth_part() -> Part:
    module_id = "chef_simon_waveshare_esp32_p4_poe_eth"
    width = 330
    height = 760
    left_x = 24
    right_x = width - 24
    left_pins = [
        ("gpio54", "GPIO54"),
        ("gpio19", "GPIO19"),
        ("gnd_l0", "GND"),
        ("gpio18", "GPIO18"),
        ("gpio17", "GPIO17"),
        ("gpio16", "GPIO16"),
        ("gpio15", "GPIO15"),
        ("gnd_l1", "GND"),
        ("gpio14", "GPIO14"),
        ("gpio6", "GPIO6"),
        ("gpio5", "GPIO5"),
        ("gpio4", "GPIO4"),
        ("gnd_l2", "GND"),
        ("gpio3", "GPIO3"),
        ("gpio2", "GPIO2"),
        ("gpio8", "SCL/GPIO8"),
        ("gpio7", "SDA/GPIO7"),
        ("gnd_l3", "GND"),
        ("gpio24", "DM/GPIO24"),
        ("gpio25", "DP/GPIO25"),
    ]
    right_pins = [
        ("vbus", "VBUS"),
        ("vsys", "VSYS"),
        ("gnd_r0", "GND"),
        ("en", "EN"),
        ("3v3", "3V3"),
        ("gpio20", "GPIO20"),
        ("gpio21", "GPIO21"),
        ("gnd_r1", "GND"),
        ("gpio22", "GPIO22"),
        ("gpio23", "GPIO23"),
        ("run", "RUN"),
        ("gpio26", "GPIO26"),
        ("gnd_r2", "GND"),
        ("gpio27", "GPIO27"),
        ("gpio32", "GPIO32"),
        ("gpio33", "GPIO33"),
        ("gpio46", "GPIO46"),
        ("gnd_r3", "GND"),
        ("gpio47", "GPIO47"),
        ("gpio48", "GPIO48"),
    ]
    pins: dict[str, tuple[float, float]] = {}
    connectors = []

    def pin_color(label: str) -> str:
        if label in {"GND"}:
            return WIRE["gnd"]
        if label in {"VBUS", "VSYS", "3V3"}:
            return WIRE["vplus"]
        if label in {"EN", "RUN"}:
            return "#f4a6aa"
        if label.startswith("DM") or label.startswith("DP"):
            return "#0ea5e9"
        return "#65a30d"

    pin_svg = []
    label_svg = []
    for side, side_pins, x, text_anchor, tx in [
        ("left", left_pins, left_x, "end", left_x - 2),
        ("right", right_pins, right_x, "start", right_x + 12),
    ]:
        for i, (pin_id, label) in enumerate(side_pins):
            y = 58 + i * 32
            pins[pin_id] = (x, y)
            color = pin_color(label)
            pin_svg.append(f'<circle id="{pin_id}pin" cx="{x}" cy="{y}" r="6" fill="#ffffff" stroke="{color}" stroke-width="3"/>')
            label_svg.append(
                f'<text x="{tx}" y="{y + 4}" font-family="Segoe UI, Arial, sans-serif" font-size="13" '
                f'font-weight="700" fill="{color}" text-anchor="{text_anchor}">{esc(label)}</text>'
            )
            connectors.append(
                f'<connector id="{pin_id}" type="male" name="{esc(label)}">'
                f'<views><breadboardView><p layer="breadboard" svgId="{pin_id}pin"/></breadboardView>'
                f'<schematicView><p layer="schematic" svgId="{pin_id}pin"/></schematicView>'
                f'<pcbView><p layer="silkscreen" svgId="{pin_id}pin"/></pcbView></views></connector>'
            )

    board_body = f'''
    <rect x="54" y="26" width="222" height="694" rx="18" fill="#111827" stroke="#374151" stroke-width="3"/>
    <rect x="80" y="56" width="170" height="74" rx="10" fill="#0f766e" stroke="#14b8a6" stroke-width="2"/>
    <text x="165" y="84" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="800" fill="#ffffff" text-anchor="middle">Waveshare</text>
    <text x="165" y="108" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="700" fill="#ccfbf1" text-anchor="middle">ESP32-P4-POE-ETH</text>
    <rect x="92" y="158" width="146" height="118" rx="8" fill="#1f2937" stroke="#4b5563"/>
    <text x="165" y="206" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#e5e7eb" text-anchor="middle">ESP32 PoE</text>
    <text x="165" y="232" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#9ca3af" text-anchor="middle">PoE controller only</text>
    <rect x="90" y="332" width="150" height="54" rx="7" fill="#f8fafc" stroke="#94a3b8"/>
    <text x="165" y="365" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="800" fill="#334155" text-anchor="middle">RJ45 + PoE</text>
    <rect x="96" y="440" width="138" height="60" rx="7" fill="#1d4ed8" stroke="#60a5fa"/>
    <text x="165" y="466" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="800" fill="#ffffff" text-anchor="middle">GPIO control only</text>
    <text x="165" y="486" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe" text-anchor="middle">Lamps/audio use external rails</text>
    <rect x="108" y="686" width="114" height="34" rx="5" fill="#f8fafc" stroke="#94a3b8"/>
    <text x="165" y="706" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="800" fill="#334155" text-anchor="middle">NO LOAD POWER OUT</text>
    <text x="165" y="548" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">Do not draw lamp/audio current from ESP32</text>
    <text x="165" y="568" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">Use 12V_SHOW / 5V_LED / 5V_AUDIO_SERVO</text>
    '''
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="breadboard">{board_body}{''.join(pin_svg)}{''.join(label_svg)}</g>
  <g id="schematic">{board_body}{''.join(pin_svg)}{''.join(label_svg)}</g>
  <g id="silkscreen">{board_body}{''.join(pin_svg)}{''.join(label_svg)}</g>
  <g id="icon">{board_body}{''.join(pin_svg)}{''.join(label_svg)}</g>
</svg>
'''
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH</title><label>PoE</label>
  <properties>
    <property name="family">ESP32 PoE development board</property>
    <property name="board">Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH</property>
    <property name="audio">External audio modules/amps use 5V_AUDIO_SERVO</property>
  </properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>{''.join(connectors)}</connectors>
  <buses/>
</module>
'''
    return Part(
        "esp32_p4_poe_eth",
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg,
            f"svg.breadboard.{module_id}.svg": svg,
            f"svg.schematic.{module_id}.svg": svg,
            f"svg.pcb.{module_id}.svg": svg,
        },
        pins,
    )


def make_label_part(key: str, text_lines: list[str], width: int = 210, size: int = 15) -> Part:
    height = max(32, 24 + len(text_lines) * (size + 4))
    texts = []
    y = 18
    for i, line in enumerate(text_lines):
        weight = "700" if i == 0 else "500"
        texts.append(
            f'<text x="8" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="#1f2933">{esc(line)}</text>'
        )
        y += size + 5
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="breadboard"><rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#fffefa" stroke="#d0d7de"/>{''.join(texts)}</g>
  <g id="schematic"><rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#fffefa" stroke="#d0d7de"/>{''.join(texts)}</g>
  <g id="silkscreen"><rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#fffefa" stroke="#d0d7de"/>{''.join(texts)}</g>
  <g id="icon"><rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#fffefa" stroke="#d0d7de"/>{''.join(texts)}</g>
</svg>
'''
    module_id = f"chef_simon_label_{key}"
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>{esc(text_lines[0])}</title><label>TXT</label>
  <properties><property name="family">Chef Simon annotations</property></properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors/><buses/>
</module>
'''
    return Part(
        key,
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg,
            f"svg.breadboard.{module_id}.svg": svg,
            f"svg.schematic.{module_id}.svg": svg,
            f"svg.pcb.{module_id}.svg": svg,
        },
        {},
    )


def make_junction_part() -> Part:
    module_id = "chef_simon_wire_waypoint"
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="6" height="6" viewBox="0 0 6 6">
  <g id="breadboard"><circle id="pinpin" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/></g>
  <g id="schematic"><circle id="pinpin" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/></g>
  <g id="silkscreen"><circle id="pinpin" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/></g>
  <g id="icon"><circle id="pinpin" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/></g>
</svg>
'''
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>Wire waypoint</title><label>WP</label>
  <properties><property name="family">Chef Simon routing helpers</property></properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>
    <connector id="pin" type="male" name="waypoint"><views><breadboardView><p layer="breadboard" svgId="pinpin"/></breadboardView><schematicView><p layer="schematic" svgId="pinpin"/></schematicView><pcbView><p layer="silkscreen" svgId="pinpin"/></pcbView></views></connector>
  </connectors><buses/>
</module>
'''
    return Part(
        "waypoint",
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg,
            f"svg.breadboard.{module_id}.svg": svg,
            f"svg.schematic.{module_id}.svg": svg,
            f"svg.pcb.{module_id}.svg": svg,
        },
        {"pin": (3, 3)},
    )


def make_rail_part(key: str, title: str, color: str, labels: list[str]) -> Part:
    tap_count = 22
    width = 1260
    connectors = []
    pins = {}
    for i in range(tap_count):
        x = 35 + i * 55
        connectors.append(f'<connector id="tap{i}" type="male" name="tap {i}"><views><breadboardView><p layer="breadboard" svgId="tap{i}pin"/></breadboardView><schematicView><p layer="schematic" svgId="tap{i}pin"/></schematicView><pcbView><p layer="silkscreen" svgId="tap{i}pin"/></pcbView></views></connector>')
        pins[f"tap{i}"] = (x, 24)
    circles = "".join(f'<circle id="tap{i}pin" cx="{35+i*55}" cy="24" r="5" fill="#ffffff" stroke="{color}" stroke-width="2"/>' for i in range(tap_count))
    label_svg = "".join(f'<text x="16" y="{52+i*20}" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="600" fill="#1f2933">{esc(line)}</text>' for i, line in enumerate(labels))
    height = 70 + len(labels) * 20
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="breadboard"><rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="schematic"><rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="silkscreen"><rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="icon"><rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
</svg>
'''
    module_id = f"chef_simon_{key}"
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>{esc(title)}</title><label>RAIL</label>
  <properties><property name="family">Chef Simon rails</property></properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>{''.join(connectors)}</connectors>
  <buses><bus id="{key}">{''.join(f'<nodeMember connectorId="tap{i}"/>' for i in range(tap_count))}</bus></buses>
</module>
'''
    return Part(
        key,
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg,
            f"svg.breadboard.{module_id}.svg": svg,
            f"svg.schematic.{module_id}.svg": svg,
            f"svg.pcb.{module_id}.svg": svg,
        },
        pins,
    )


def make_local_ground_bus_part() -> Part:
    module_id = "chef_simon_local_ground_bus"
    width = 560
    height = 62
    tap_xs = [30, 130, 230, 330, 430, 530]
    connectors = []
    pins = {}
    for i, x in enumerate(tap_xs):
        connectors.append(f'<connector id="tap{i}" type="male" name="ground tap {i}"><views><breadboardView><p layer="breadboard" svgId="tap{i}pin"/></breadboardView><schematicView><p layer="schematic" svgId="tap{i}pin"/></schematicView><pcbView><p layer="silkscreen" svgId="tap{i}pin"/></pcbView></views></connector>')
        pins[f"tap{i}"] = (x, 20)
    circles = "".join(f'<circle id="tap{i}pin" cx="{x}" cy="20" r="5" fill="#ffffff" stroke="{WIRE["gnd"]}" stroke-width="2"/>' for i, x in enumerate(tap_xs))
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="breadboard"><rect x="0" y="0" width="{width}" height="{height}" rx="6" fill="#ffffff" stroke="#9aa5b1"/><line x1="16" y1="20" x2="{width-16}" y2="20" stroke="{WIRE["gnd"]}" stroke-width="6"/>{circles}<text x="16" y="48" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#1f2933">local GND bus: branches only, one trunk to common rail</text></g>
  <g id="schematic"><rect x="0" y="0" width="{width}" height="{height}" rx="6" fill="#ffffff" stroke="#9aa5b1"/><line x1="16" y1="20" x2="{width-16}" y2="20" stroke="{WIRE["gnd"]}" stroke-width="6"/>{circles}<text x="16" y="48" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#1f2933">local GND bus: branches only, one trunk to common rail</text></g>
  <g id="silkscreen"><rect x="0" y="0" width="{width}" height="{height}" rx="6" fill="#ffffff" stroke="#9aa5b1"/><line x1="16" y1="20" x2="{width-16}" y2="20" stroke="{WIRE["gnd"]}" stroke-width="6"/>{circles}<text x="16" y="48" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#1f2933">local GND bus: branches only, one trunk to common rail</text></g>
  <g id="icon"><rect x="0" y="0" width="{width}" height="{height}" rx="6" fill="#ffffff" stroke="#9aa5b1"/><line x1="16" y1="20" x2="{width-16}" y2="20" stroke="{WIRE["gnd"]}" stroke-width="6"/>{circles}<text x="16" y="48" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#1f2933">local GND bus: branches only, one trunk to common rail</text></g>
</svg>
'''
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>Local GND bus</title><label>GND</label>
  <properties><property name="family">Chef Simon rails</property></properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>{''.join(connectors)}</connectors>
  <buses><bus id="local_ground">{''.join(f'<nodeMember connectorId="tap{i}"/>' for i in range(len(tap_xs)))}</bus></buses>
</module>
'''
    return Part(
        "local_gnd_bus",
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg,
            f"svg.breadboard.{module_id}.svg": svg,
            f"svg.schematic.{module_id}.svg": svg,
            f"svg.pcb.{module_id}.svg": svg,
        },
        pins,
    )


def uniquify_svg_entries(part: Part) -> Part:
    renamed_entries = {}
    for old_entry, svg_text in part.svg_entries.items():
        view = old_entry.split(".")[1]
        old_file = old_entry.split(".", 2)[2]
        new_file = f"{part.module_id}_{view}.svg"
        part.fzp = part.fzp.replace(f"{view}/{old_file}", f"{view}/{new_file}")
        renamed_entries[f"svg.{view}.{new_file}"] = svg_text
    part.svg_entries = renamed_entries
    return part


def build_parts() -> dict[str, Part]:
    parts = {
        "esp32": make_waveshare_esp32_p4_poe_eth_part(),
        "resistor_1k": uniquify_svg_entries(read_stock_part("resistor_1k", STOCK["resistor_1k"], {"connector0": (0.7, 3.6), "connector1": (30.2, 3.6)})),
        "resistor_10k": uniquify_svg_entries(read_stock_part("resistor_10k", STOCK["resistor_10k"], {"connector0": (0.7, 3.6), "connector1": (30.2, 3.6)})),
        "mosfet": read_stock_part("mosfet", STOCK["mosfet"], {"connector0": (6.5, 42.8), "connector1": (13.7, 42.8), "connector2": (20.9, 42.8)}),
        "terminal4": read_stock_part("terminal4", STOCK["terminal4"], {"connector0": (9, 26), "connector1": (27, 26), "connector2": (45, 26), "connector3": (63, 26)}),
        "arcade_red": read_stock_part("arcade_red", STOCK["arcade_red"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_yellow": read_stock_part("arcade_yellow", STOCK["arcade_yellow"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_white": read_stock_part("arcade_white", STOCK["arcade_white"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_blue": read_stock_part("arcade_blue", STOCK["arcade_blue"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "vrail": make_rail_part("vplus_12v_show_rail", "12V_SHOW lamp rail", WIRE["vplus"], ["12V_SHOW to 12V-rated lamp positives only", "If using 5V lamps, use the master 5V_LED rail instead"]),
        "audiorail": make_rail_part("vplus_5v_audio_servo_rail", "5V_AUDIO_SERVO rail", WIRE["v5"], ["5V_AUDIO_SERVO for any Simon audio module / amplifier", "Do not power audio from the ESP32 PoE board"]),
        "gndrail": make_rail_part("common_ground_rail", "COMMON_GND rail", WIRE["gnd"], ["All signal-crossing grounds must be common"]),
        "local_gnd_bus": make_local_ground_bus_part(),
        "notes": make_label_part("notes", ["Notes", "Controller: Waveshare ESP32-P4-POE-ETH / NH powered by PoE.", "PoE powers ESP32 only; no lamp/audio load power from board.", "Use INPUT_PULLUP: unpressed HIGH, pressed LOW.", "Do not tie LED/lamp negatives together.", "12V lamps use 12V_SHOW; 5V lamps use 5V_LED.", "Any audio module/amp uses 5V_AUDIO_SERVO.", "COMMON_GND is required for GPIO-controlled external loads."], 960, 16),
        "waypoint": make_junction_part(),
    }
    # No stock green arcade button exists in this Fritzing install; use red library artwork as a derived green part.
    green = read_stock_part("arcade_green", STOCK["arcade_red"], {"connector1": (55, 135), "connector2": (76, 135)})
    green.module_id = "chef_simon_library_derived_green_arcade_button"
    green.fzp_name = f"part.{green.module_id}.fzp"
    green.fzp = re.sub(r'moduleId="[^"]+"', f'moduleId="{green.module_id}"', green.fzp)
    green.fzp = green.fzp.replace("Arcade Button (red)", "Arcade Button (green, library-art derived)")
    green.fzp = green.fzp.replace("<property name=\"color\">red</property>", "<property name=\"color\">green</property>")
    renamed_entries = {}
    for old_entry, svg_text in green.svg_entries.items():
        view = old_entry.split(".")[1]
        old_file = old_entry.split(".", 2)[2]
        new_file = f"{green.module_id}_{view}.svg"
        green.fzp = green.fzp.replace(f"{view}/{old_file}", f"{view}/{new_file}")
        renamed_entries[f"svg.{view}.{new_file}"] = (
            svg_text.replace("#e02320", "#2f9e44")
            .replace("#ed1c24", "#2f9e44")
            .replace("#d71920", "#2f9e44")
            .replace("#C1272D", "#2f9e44")
        )
    green.svg_entries = renamed_entries
    parts["arcade_green"] = green
    return parts


def connector_instance_xml(inst: Instance) -> str:
    chunks = []
    for conn_id, wires in inst.connects.items():
        chunks.append(f'          <connector connectorId="{conn_id}" layer="breadboard"><geometry x="0" y="0"/><connects>')
        for wire_idx, wire_conn in wires:
            chunks.append(f'            <connect connectorId="{wire_conn}" modelIndex="{wire_idx}" layer="breadboardWire"/>')
        chunks.append("          </connects></connector>")
    return "\n".join(chunks)


def instance_xml(inst: Instance, parts: dict[str, Part]) -> str:
    part = parts[inst.part]
    props = "\n".join(f'      <property name="{esc(k)}" value="{esc(v)}"/>' for k, v in inst.props.items())
    connectors = connector_instance_xml(inst)
    connectors_block = f"\n        <connectors>\n{connectors}\n        </connectors>" if connectors else ""
    return f'''    <instance moduleIdRef="{part.module_id}" modelIndex="{inst.idx}" path="{part.fzp_name}">
      <title>{esc(inst.title)}</title>
{props}
      <views>
        <breadboardView layer="breadboard">
          <geometry z="2" x="{inst.x:.2f}" y="{inst.y:.2f}"/>{connectors_block}
        </breadboardView>
      </views>
    </instance>'''


def wire_xml(w: Wire, insts: dict[str, Instance], parts: dict[str, Part]) -> str:
    a, b = insts[w.a], insts[w.b]
    ax, ay = parts[a.part].pins[w.ac]
    bx, by = parts[b.part].pins[w.bc]
    x1, y1 = a.x + ax, a.y + ay
    x2, y2 = b.x + bx, b.y + by
    return f'''    <instance moduleIdRef="WireModuleID" modelIndex="{w.idx}" path=":/resources/parts/core/wire.fzp">
      <title>{esc(w.title)}</title>
      <views>
        <breadboardView layer="breadboardWire">
          <geometry z="3" x="{x1:.2f}" y="{y1:.2f}" x1="0" y1="0" x2="{x2-x1:.2f}" y2="{y2-y1:.2f}" wireFlags="64"/>
          <wireExtras mils="{w.width:.2f}" color="{w.color}" opacity="1" banded="0"/>
          <connectors>
            <connector connectorId="connector0" layer="breadboardWire"><geometry x="0" y="0"/><connects><connect connectorId="{w.ac}" modelIndex="{a.idx}" layer="breadboard"/></connects></connector>
            <connector connectorId="connector1" layer="breadboardWire"><geometry x="0" y="0"/><connects><connect connectorId="{w.bc}" modelIndex="{b.idx}" layer="breadboard"/></connects></connector>
          </connectors>
        </breadboardView>
      </views>
    </instance>'''


def build_instances(parts: dict[str, Part]) -> tuple[list[Instance], list[Wire]]:
    inst: list[Instance] = []
    wires: list[Wire] = []
    idx = 1000
    widx = 5000

    def add(key, part, title, x, y, props=None):
        nonlocal idx
        idx += 1
        item = Instance(key, part, title, x, y, idx, props or {})
        inst.append(item)
        return item

    def add_label(key, lines, x, y, width=210):
        parts_dynamic[key] = make_label_part(key, lines, width)
        return add(key, key, lines[0], x, y)

    def wire(a, ac, b, bc, color, title, width=10):
        nonlocal widx
        ax, ay = abs_pos(a, ac)
        bx, by = abs_pos(b, bc)
        if abs(ax - bx) < 0.01 and abs(ay - by) < 0.01:
            return
        widx += 1
        wires.append(Wire(widx, title, a, ac, b, bc, color, width))

    def add_waypoint(key, x, y):
        return add(key, "waypoint", key, x - 3, y - 3)

    def abs_pos(key, conn):
        by_key = {i.key: i for i in inst}
        item = by_key[key]
        px, py = parts[item.part].pins[conn]
        return item.x + px, item.y + py

    def routed_wire(a, ac, b, bc, points, color, title, width=10):
        prev_key, prev_conn = a, ac
        last_x, last_y = abs_pos(a, ac)
        tx, ty = abs_pos(b, bc)
        for i, (x, y) in enumerate(points):
            if abs(x - last_x) < 0.01 and abs(y - last_y) < 0.01:
                continue
            if abs(x - tx) < 0.01 and abs(y - ty) < 0.01:
                continue
            wp_key = f"wp_{len(wires)}_{i}_{len(inst)}"
            add_waypoint(wp_key, x, y)
            wire(prev_key, prev_conn, wp_key, "pin", color, f"{title} segment {i + 1}", width)
            prev_key, prev_conn = wp_key, "pin"
            last_x, last_y = x, y
        wire(prev_key, prev_conn, b, bc, color, title, width)

    def route_hv(a, ac, b, bc, mid_x, color, title, width=10):
        sx, sy = abs_pos(a, ac)
        _tx, ty = abs_pos(b, bc)
        routed_wire(a, ac, b, bc, [(mid_x, sy), (mid_x, ty)], color, title, width)

    def route_vh(a, ac, b, bc, mid_y, color, title, width=10):
        sx, sy = abs_pos(a, ac)
        tx, _ty = abs_pos(b, bc)
        routed_wire(a, ac, b, bc, [(sx, mid_y), (tx, mid_y)], color, title, width)

    def route_around(a, ac, b, bc, mid_x, mid_y, color, title, width=10):
        sx, _sy = abs_pos(a, ac)
        tx, _ty = abs_pos(b, bc)
        routed_wire(a, ac, b, bc, [(mid_x, _sy), (mid_x, mid_y), (tx, mid_y)], color, title, width)

    def route_fanout(a, ac, b, bc, stub_x, lane_y, color, title, width=10):
        sx, sy = abs_pos(a, ac)
        tx, ty = abs_pos(b, bc)
        routed_wire(a, ac, b, bc, [(stub_x, sy), (stub_x, lane_y), (tx, lane_y)], color, title, width)

    def route_h_then_v(a, ac, b, bc, bus_x, color, title, width=10):
        _sx, sy = abs_pos(a, ac)
        routed_wire(a, ac, b, bc, [(bus_x, sy)], color, title, width)

    global parts_dynamic
    parts_dynamic = {}

    add("esp", "esp32", "Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH", 30, 245)
    add("vrail", "vrail", "12V_SHOW lamp rail", 420, 70)
    add("audiorail", "audiorail", "5V_AUDIO_SERVO rail", 420, 1810)
    add("gndrail", "gndrail", "COMMON_GND rail", 420, 1960)
    add("notes", "notes", "Notes", 75, 1995)
    add_label("esp_pin_labels", ["Waveshare ESP32-P4-POE-ETH / NH", "RJ45: Ethernet + PoE from LS108GP", "PoE powers ESP32 controller only", "BTN inputs: GPIO16,17,18,19", "Lamp gates: GPIO20,21,22,23", "External lamps/audio use named rails"], 32, 145, 345)

    route_around("esp", "gnd_l3", "gndrail", "tap0", 40, 1840, WIRE["gnd"], "ESP32 GND reference to COMMON_GND rail", 12)

    rows = [240, 600, 960, 1320]
    esp_sw = {1: "gpio16", 2: "gpio17", 3: "gpio18", 4: "gpio19"}
    esp_lamp = {1: "gpio20", 2: "gpio21", 3: "gpio22", 4: "gpio23"}
    colors = {"red": "arcade_red", "green": "arcade_green", "white": "arcade_white", "yellow": "arcade_yellow", "blue": "arcade_blue"}
    for item, row in zip(BUTTONS, rows):
        n = item["n"]
        add(f"rg{n}", "resistor_1k", f"R{n} 1k gate", 360, row + 92, {"Resistance": "1k"})
        add(f"rp{n}", "resistor_10k", f"R{n} 10k gate pulldown", 500, row + 142, {"Resistance": "10k"})
        add(f"q{n}", "mosfet", f"Q{n} IRFB11N50APBF", 650, row + 72)
        add(f"term{n}", "terminal4", f"BTN{n} 4-terminal plug", 900, row + 98)
        add(f"button{n}", colors[item["color"]], f'{item["name"]} arcade button visual', 1085, row + 50)
        add(f"gbus{n}", "local_gnd_bus", f"BTN{n} local GND bus", 560, row + 292)
        add_label(f"plug_labels_{n}", [f"BTN{n} plug order", "1 LED +   2 LED -", "3 SW SIG  4 SW GND"], 875, row + 6, 250)
        add_label(f"resistor_labels_{n}", [f"BTN{n} resistors", "Gate: 1k", "Pulldown: 10k"], 330, row + 14, 170)
        add_label(f"mosfet_labels_{n}", [f"Q{n} G / D / S", "Gate via 1k", "Drain to LED -", "Source to GND"], 610, row + 4, 210)

        # Orthogonal lane routing. Each net receives a distinct lane so parallel wires do not overlap.
        ledp_lane = row + 58
        ledm_lane = row + 206
        swsig_lane = row + 236
        swgnd_lane = row + 266
        gate_lane = row + 118
        pulldown_lane = row + 176
        local_gnd_y = row + 312

        route_around("vrail", f"tap{n}", f"term{n}", "connector0", 810 + n * 16, ledp_lane, WIRE["vplus"], f"BTN{n} LED+ to 12V_SHOW lamp rail", 12)
        route_around(f"term{n}", "connector1", f"q{n}", "connector1", 848 + n * 16, ledm_lane, WIRE["lamp_minus"], f"BTN{n} LED- to MOSFET drain", 10)
        route_vh(f"q{n}", "connector2", f"gbus{n}", "tap1", local_gnd_y, WIRE["gnd"], f"Q{n} source branch to local GND bus", 12)
        route_vh(f"term{n}", "connector3", f"gbus{n}", "tap4", local_gnd_y, WIRE["gnd"], f"BTN{n} switch GND branch to local GND bus", 10)
        _sw_pin_x, sw_pin_y = abs_pos("esp", esp_sw[n])
        term_sig_x, _term_sig_y = abs_pos(f"term{n}", "connector2")
        switch_escape_x = 8 + n * 8
        switch_return_x = 390 + n * 14
        switch_escape_y = 1035 + n * 28
        routed_wire(
            "esp",
            esp_sw[n],
            f"term{n}",
            "connector2",
            [
                (switch_escape_x, sw_pin_y),
                (switch_escape_x, switch_escape_y),
                (switch_return_x, switch_escape_y),
                (switch_return_x, swsig_lane),
                (term_sig_x, swsig_lane),
            ],
            WIRE["switch_a"] if n % 2 else WIRE["switch_b"],
            f"BTN{n} switch signal to {item['sw']}",
            10,
        )
        route_around("esp", esp_lamp[n], f"rg{n}", "connector0", 430 + n * 10, gate_lane, WIRE["gate"], f"{item['lamp']} to 1k gate resistor", 10)
        route_fanout(f"rg{n}", "connector1", f"q{n}", "connector0", 440 + n * 9, gate_lane + 18, WIRE["gate"], f"1k resistor to Q{n} gate", 10)
        route_around(f"q{n}", "connector0", f"rp{n}", "connector0", 620 + n * 12, pulldown_lane, WIRE["gate"], f"Q{n} gate to 10k pulldown", 8)
        route_vh(f"rp{n}", "connector1", f"gbus{n}", "tap0", local_gnd_y, WIRE["gnd"], f"10k pulldown branch to local GND bus", 8)
        route_h_then_v(f"gbus{n}", "tap5", "gndrail", f"tap{15+n}", 420 + 35 + (15+n) * 55, WIRE["gnd"], f"BTN{n} local GND bus trunk to COMMON_GND rail", 12)
        route_fanout(f"term{n}", "connector2", f"button{n}", "connector1", 975 + n * 8, swsig_lane, WIRE["switch_a"], f"BTN{n} plug SW SIG to arcade switch lug", 7)
        route_fanout(f"term{n}", "connector3", f"button{n}", "connector2", 1005 + n * 8, swgnd_lane, WIRE["gnd"], f"BTN{n} plug SW GND to arcade switch lug", 7)

    add_label("audio_labels", ["Optional Simon audio", "Use separate DFPlayer/amp if needed.", "Power audio from 5V_AUDIO_SERVO.", "Control/data from ESP32 GPIO only.", "Return audio power to COMMON_GND.", "Do not power amplifier from PoE board."], 610, 1595, 460)

    by_key = {i.key: i for i in inst}
    for w in wires:
        by_key[w.a].connects.setdefault(w.ac, []).append((w.idx, "connector0"))
        by_key[w.b].connects.setdefault(w.bc, []).append((w.idx, "connector1"))
    return inst, wires


def write_fzz(parts: dict[str, Part], inst: list[Instance], wires: list[Wire]) -> None:
    all_parts = {**parts, **parts_dynamic}
    by_key = {i.key: i for i in inst}
    fz_instances = "\n".join([wire_xml(w, by_key, all_parts) for w in wires] + [instance_xml(i, all_parts) for i in inst])
    fz = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" icon=".png">
  <project_properties><simulator_animation_time_s value="5s"/><simulator_number_of_steps value="400"/><simulator_time_step_mode value="false"/><simulator_time_step_s value="1us"/></project_properties>
  <views>
    <view name="breadboardView" backgroundColor="#fbfaf7" gridSize="0.1in" showGrid="0" alignToGrid="0" viewFromBelow="0" colorWiresByLength="0"/>
    <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="0" alignToGrid="1" viewFromBelow="0"/>
    <view name="pcbView" backgroundColor="#ffffff" gridSize="0.05in" showGrid="0" alignToGrid="1" viewFromBelow="0" autorouteViaHoleSize="" autorouteTraceWidth="24" GPG_Keepout="" autorouteViaRingThickness="" DRC_Keepout="0.01in"/>
  </views>
  <instances>
{fz_instances}
  </instances>
</module>
'''
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(FZZ_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("chef_station_simon_lane_routed_editable.fz", fz)
        for part in all_parts.values():
            z.writestr(part.fzp_name, part.fzp)
            for name, text in part.svg_entries.items():
                z.writestr(name, text)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Simon 4-Button Wiring Checklist

This revision uses a Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH controller powered and networked by the LS108GP PoE switch. PoE powers the ESP32 controller only. Button lamps, audio modules, amplifiers, and other loads use external named accessory rails.

## Pin Map

| Function | ESP32 pin |
| --- | --- |
| BTN1 / Ingredient 1 switch input | GPIO 16 |
| BTN2 / Ingredient 2 switch input | GPIO 17 |
| BTN3 / Ingredient 3 switch input | GPIO 18 |
| BTN4 / Ingredient 4 switch input | GPIO 19 |
| BTN1 lamp MOSFET gate | GPIO 20 |
| BTN2 lamp MOSFET gate | GPIO 21 |
| BTN3 lamp MOSFET gate | GPIO 22 |
| BTN4 lamp MOSFET gate | GPIO 23 |

## Power Rails

| Rail | Use |
| --- | --- |
| PoE from LS108GP | ESP32 controller power and Ethernet only |
| 12V_SHOW | 12V-rated Simon button lamps or show loads only |
| 5V_LED | Use instead of 12V_SHOW if the button lamps are 5V-rated |
| 5V_AUDIO_SERVO | Optional Simon DFPlayer/audio module/amplifier |
| COMMON_GND | Signal reference and accessory return bus |

## Button And Lamp Wiring

- Configure each button input as `INPUT_PULLUP`: unpressed = HIGH, pressed = LOW.
- Wire each switch with one terminal to COMMON_GND and the other terminal to its ESP32 GPIO input.
- Feed each button lamp positive from the rail matching the lamp voltage: `12V_SHOW` for 12V lamps or `5V_LED` for 5V lamps.
- Run each button lamp negative separately to its own MOSFET drain.
- Connect each MOSFET source to the local ground bus, then to COMMON_GND.
- Connect each ESP32 lamp GPIO to its MOSFET gate through a 1k resistor.
- Add a 10k pulldown from each MOSFET gate to COMMON_GND.
- Do not connect lamp negatives together if individual flashing is required.

## Audio Option

- Do not power audio modules or amplifiers from the ESP32 PoE board.
- If Simon uses sound, power the DFPlayer/audio module or small amplifier from `5V_AUDIO_SERVO`.
- Any ESP32 audio trigger/control line must share COMMON_GND with the audio rail.
- Route speaker current through the audio amplifier wiring, not through ESP32 ground pins.

## Grounding Notes

- Tie the Simon ESP32 GND reference to COMMON_GND anywhere GPIO controls externally powered lamps or audio.
- Do not route high-current lamp/audio return current through ESP32 ground pins.
- Use a ground terminal block or bus for lamp and audio returns.

## Setup Checklist

- Verify each adjustable adapter output with a multimeter before connecting the module.
- Confirm lamp voltage before connecting to `12V_SHOW` or `5V_LED`.
- Do not connect 12V to 5V lamps or 5V to ESP32 3.3V pins.
- Do not parallel separate buck converter outputs.
- Do not parallel separate wall adapter positive outputs.
- Label both ends of every lamp, signal, and rail cable.

## Part Notes

- ESP32 controller: custom editable Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH helper art with functional GPIO labels. Verify exact board pinout before final harness fabrication.
- Resistors: value-specific Fritzing 1k and 10k resistor artwork, plus visible labels.
- MOSFET: stock Fritzing TO-220 N-channel MOSFET artwork, titled as IRFB11N50APBF.
- Arcade buttons: stock Fritzing arcade button visuals plus labeled 4-position terminal blocks showing lamp +, lamp -, SW SIG, and SW GND.
- Rails, buses, and callouts are custom editable Fritzing helper parts for readability.
""",
        encoding="utf-8",
    )


def export() -> Path:
    if EXPORT_DIR.exists():
        for old in EXPORT_DIR.glob("*"):
            if old.is_file():
                old.unlink()
    else:
        EXPORT_DIR.mkdir(parents=True)
    shutil.copy2(FZZ_PATH, EXPORT_DIR / FZZ_PATH.name)
    subprocess.run([str(FRITZING), "-svg", str(EXPORT_DIR)], check=True)
    exported = EXPORT_DIR / f"{FZZ_PATH.stem}_breadboard.svg"
    if not exported.exists():
        raise FileNotFoundError(f"Expected Fritzing breadboard SVG export not found: {exported}")
    return exported


def render_png(svg_path: Path) -> None:
    if not EDGE.exists():
        print(f"Skipped PNG render; Microsoft Edge not found at {EDGE}")
        return
    subprocess.run(
        [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--screenshot={PNG_PATH}",
            "--window-size=2600,2300",
            svg_path.as_uri(),
        ],
        check=True,
    )


def count_diagonal_segments(inst: list[Instance], wires: list[Wire], parts: dict[str, Part]) -> int:
    all_parts = {**parts, **parts_dynamic}
    by_key = {item.key: item for item in inst}
    diagonal = 0
    for item in wires:
        a, b = by_key[item.a], by_key[item.b]
        ax, ay = all_parts[a.part].pins[item.ac]
        bx, by = all_parts[b.part].pins[item.bc]
        x1, y1 = a.x + ax, a.y + ay
        x2, y2 = b.x + bx, b.y + by
        if abs(x1 - x2) > 0.01 and abs(y1 - y2) > 0.01:
            diagonal += 1
    return diagonal


def main() -> None:
    parts = build_parts()
    inst, wires = build_instances(parts)
    write_fzz(parts, inst, wires)
    write_checklist()
    svg_path = export()
    render_png(svg_path)
    print(f"Wrote {FZZ_PATH}")
    print(f"Wrote {svg_path}")
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {CHECKLIST_PATH}")
    print(f"Editable part instances: {len(inst)}")
    print(f"Editable wires: {len(wires)}")
    print(f"Fritzing SVG export: {EXPORT_DIR}")
    print(f"Diagonal wire segments: {count_diagonal_segments(inst, wires, parts)}")


if __name__ == "__main__":
    main()
