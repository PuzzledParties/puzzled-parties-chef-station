from __future__ import annotations

import html
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "library_art_fritzing"
FZZ_PATH = OUT_DIR / "chef_station_simon_4btn_audio_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")
ESP32_FZPZ = ROOT / "downloaded_parts" / "DOIT_Esp32_DevKit_v1_improved.fzpz"


BUTTONS = [
    {"n": 1, "name": "Ingredient 1", "sw": "GPIO 16", "lamp": "GPIO 21", "color": "red"},
    {"n": 2, "name": "Ingredient 2", "sw": "GPIO 17", "lamp": "GPIO 22", "color": "green"},
    {"n": 3, "name": "Ingredient 3", "sw": "GPIO 18", "lamp": "GPIO 23", "color": "white"},
    {"n": 4, "name": "Ingredient 4", "sw": "GPIO 19", "lamp": "GPIO 25", "color": "yellow"},
]


STOCK = {
    "resistor_1k": PARTS / "obsolete" / "resistor_1k.fzp",
    "resistor_10k": PARTS / "obsolete" / "resistor_10k.fzp",
    "mosfet": PARTS / "core" / "basic_fet_n.fzp",
    "terminal4": PARTS / "core" / "Camdenboss_CTB0158-4_5_08mm_pitch_90deg_terminals.fzp",
    "speaker": PARTS / "core" / "sparkfun-electromechanical-speaker-.fzp",
    "arcade_red": PARTS / "contrib" / "Arcade_Button__red___c12cc3bca053e12377a7a3c856ef34e4_24.fzp",
    "arcade_yellow": PARTS / "contrib" / "Arcade_Button__yellow___afee1ba07e56f9a78a19f30fa6b24e7f_B2.fzp",
    "arcade_white": PARTS / "contrib" / "Arcade_Button__white___56f11dd8030025047c5ba1044fac4aa2_37.fzp",
    "arcade_blue": PARTS / "contrib" / "Arcade_Button__blue___0c30cbbdde0863c5df34b75e4acddb07_20.fzp",
}


WIRE = {
    "vplus": "#d71920",
    "gnd": "#111111",
    "switch_a": "#f4b400",
    "switch_b": "#1e88e5",
    "gate": "#178f46",
    "lamp_minus": "#f57c00",
    "audio": "#7b1fa2",
    "speaker_pos": "#8d4f16",
    "speaker_neg": "#5f6368",
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


def read_esp32_part() -> Part:
    with zipfile.ZipFile(ESP32_FZPZ) as zf:
        fzp_name = next(n for n in zf.namelist() if n.endswith(".fzp"))
        fzp = zf.read(fzp_name).decode("utf-8", errors="replace")
        module_id = re.search(r'moduleId="([^"]+)"', fzp).group(1)
        svg_entries = {n: zf.read(n).decode("utf-8", errors="replace") for n in zf.namelist() if n.endswith(".svg")}
    # The downloaded ESP32 art uses 1000 SVG units per inch. Fritzing canvas is 72 px/in.
    s = 72 / 1000
    raw = {
        "connector1": (1054.7, 1537.4),  # GND
        "connector5": (1054.5, 1137.4),  # GPIO16 / RX2
        "connector6": (1054.5, 1037.4),  # GPIO17 / TX2
        "connector8": (1054.5, 837.4),   # GPIO18
        "connector9": (1054.5, 737.4),   # GPIO19
        "connector10": (1054.5, 637.4),  # GPIO21
        "connector13": (1054.4, 337.1),  # GPIO22
        "connector14": (1054.5, 237.2),  # GPIO23
        "connector22": (54.5, 937.4),    # GPIO25
        "connector23": (54.5, 1037.4),   # GPIO26
        "connector24": (54.5, 1137.4),   # GPIO27
    }
    pins = {k: (x * s, y * s) for k, (x, y) in raw.items()}
    return Part("esp32", module_id, fzp_name, fzp, svg_entries, pins)


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


def make_pam8403_part() -> Part:
    module_id = "chef_simon_generic_pam8403_mini_amp"
    width = 280
    height = 180
    pins = {
        "lin": (10, 50),
        "in_gnd": (10, 90),
        "rin": (10, 130),
        "vcc": (105, 10),
        "pwr_gnd": (155, 10),
        "lplus": (270, 48),
        "lminus": (270, 82),
        "rplus": (270, 118),
        "rminus": (270, 152),
    }
    circles = "".join(
        f'<circle id="{pin}pin" cx="{x}" cy="{y}" r="5" fill="#ffffff" stroke="#374151" stroke-width="2"/>'
        for pin, (x, y) in pins.items()
    )
    labels = [
        ("L IN", 22, 54), ("IN GND", 22, 94), ("R IN", 22, 134),
        ("5V", 92, 28), ("GND", 139, 28),
        ("L+", 235, 52), ("L-", 235, 86), ("R+", 235, 122), ("R-", 235, 156),
    ]
    label_svg = "".join(
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{esc(text)}</text>'
        for text, x, y in labels
    )
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="breadboard">
    <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#2f80ed" stroke="#1f4f9a" stroke-width="2"/>
    <rect x="84" y="60" width="112" height="58" rx="4" fill="#1f2937" stroke="#111827"/>
    <text x="88" y="84" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="800" fill="#ffffff">PAM8403</text>
    <text x="96" y="104" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe">5V stereo amp</text>
    {circles}{label_svg}
  </g>
  <g id="schematic">
    <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#2f80ed" stroke="#1f4f9a" stroke-width="2"/>
    <rect x="84" y="60" width="112" height="58" rx="4" fill="#1f2937" stroke="#111827"/>
    <text x="88" y="84" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="800" fill="#ffffff">PAM8403</text>
    <text x="96" y="104" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe">5V stereo amp</text>
    {circles}{label_svg}
  </g>
  <g id="silkscreen">
    <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#2f80ed" stroke="#1f4f9a" stroke-width="2"/>
    <rect x="84" y="60" width="112" height="58" rx="4" fill="#1f2937" stroke="#111827"/>
    <text x="88" y="84" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="800" fill="#ffffff">PAM8403</text>
    <text x="96" y="104" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe">5V stereo amp</text>
    {circles}{label_svg}
  </g>
  <g id="icon">
    <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#2f80ed" stroke="#1f4f9a" stroke-width="2"/>
    <rect x="84" y="60" width="112" height="58" rx="4" fill="#1f2937" stroke="#111827"/>
    <text x="88" y="84" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="800" fill="#ffffff">PAM8403</text>
    <text x="96" y="104" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe">5V stereo amp</text>
    {circles}{label_svg}
  </g>
</svg>
'''
    connector_xml = "".join(
        f'<connector id="{pin}" type="male" name="{pin}"><views><breadboardView><p layer="breadboard" svgId="{pin}pin"/></breadboardView><schematicView><p layer="schematic" svgId="{pin}pin"/></schematicView><pcbView><p layer="silkscreen" svgId="{pin}pin"/></pcbView></views></connector>'
        for pin in pins
    )
    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version><author>OpenAI Codex</author><title>Generic PAM8403 5V mini amplifier</title><label>AMP</label>
  <properties><property name="family">PAM8403 mini amplifier</property><property name="part number">PAM8403</property></properties>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>{connector_xml}</connectors>
  <buses/>
</module>
'''
    return Part(
        "pam8403",
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
        "esp32": read_esp32_part(),
        "resistor_1k": uniquify_svg_entries(read_stock_part("resistor_1k", STOCK["resistor_1k"], {"connector0": (0.7, 3.6), "connector1": (30.2, 3.6)})),
        "resistor_10k": uniquify_svg_entries(read_stock_part("resistor_10k", STOCK["resistor_10k"], {"connector0": (0.7, 3.6), "connector1": (30.2, 3.6)})),
        "mosfet": read_stock_part("mosfet", STOCK["mosfet"], {"connector0": (6.5, 42.8), "connector1": (13.7, 42.8), "connector2": (20.9, 42.8)}),
        "terminal4": read_stock_part("terminal4", STOCK["terminal4"], {"connector0": (9, 26), "connector1": (27, 26), "connector2": (45, 26), "connector3": (63, 26)}),
        "speaker": read_stock_part("speaker", STOCK["speaker"], {"connector0": (32.0, 78.2), "connector1": (39.3, 78.2)}),
        "arcade_red": read_stock_part("arcade_red", STOCK["arcade_red"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_yellow": read_stock_part("arcade_yellow", STOCK["arcade_yellow"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_white": read_stock_part("arcade_white", STOCK["arcade_white"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_blue": read_stock_part("arcade_blue", STOCK["arcade_blue"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "vrail": make_rail_part("vplus_12v_rail", "+12V lamp rail", WIRE["vplus"], ["Shared +12V to every LED + terminal"]),
        "amp5vrail": make_rail_part("amp_5v_rail", "+5V amp rail", WIRE["vplus"], ["PAM8403 VCC only: do not power amp from +12V"]),
        "gndrail": make_rail_part("common_ground_rail", "Common ground rail", WIRE["gnd"], ["All grounds must be common"]),
        "local_gnd_bus": make_local_ground_bus_part(),
        "pam8403": make_pam8403_part(),
        "notes": make_label_part("notes", ["Notes", "Use INPUT_PULLUP: unpressed HIGH, pressed LOW.", "Do not tie LED/lamp negatives together.", "PAM8403 uses +5V only; speaker is across L+ and L-.", "Do not connect either speaker lead to GND.", "IRFB11N50APBF is not logic-level; replace if LEDs are dim."], 850, 16),
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

    add("esp", "esp32", "DOIT ESP32 DevKit V1", 75, 310)
    add("vrail", "vrail", "+12V LED rail", 420, 70)
    add("amp5vrail", "amp5vrail", "+5V PAM8403 rail", 420, 150)
    add("gndrail", "gndrail", "Common GND rail", 420, 1960)
    add("notes", "notes", "Notes", 75, 1995)
    add_label("esp_pin_labels", ["ESP32 GPIOs", "BTN inputs: 16,17,18,19", "Lamp gates: 21,22,23,25", "Audio: GPIO26 DAC/PWM"], 32, 210, 270)

    route_around("esp", "connector1", "gndrail", "tap0", 40, 1840, WIRE["gnd"], "ESP32 GND to common GND rail", 12)

    rows = [240, 600, 960, 1320]
    esp_sw = {1: "connector5", 2: "connector6", 3: "connector8", 4: "connector9", 5: "connector23"}
    esp_lamp = {1: "connector10", 2: "connector13", 3: "connector14", 4: "connector22", 5: "connector24"}
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

        route_around("vrail", f"tap{n}", f"term{n}", "connector0", 810 + n * 16, ledp_lane, WIRE["vplus"], f"BTN{n} LED+ to shared +12V", 12)
        route_around(f"term{n}", "connector1", f"q{n}", "connector1", 848 + n * 16, ledm_lane, WIRE["lamp_minus"], f"BTN{n} LED- to MOSFET drain", 10)
        route_vh(f"q{n}", "connector2", f"gbus{n}", "tap1", local_gnd_y, WIRE["gnd"], f"Q{n} source branch to local GND bus", 12)
        route_vh(f"term{n}", "connector3", f"gbus{n}", "tap4", local_gnd_y, WIRE["gnd"], f"BTN{n} switch GND branch to local GND bus", 10)
        route_around("esp", esp_sw[n], f"term{n}", "connector2", 260 + n * 16, swsig_lane, WIRE["switch_a"] if n % 2 else WIRE["switch_b"], f"BTN{n} switch signal to {item['sw']}", 10)
        route_around("esp", esp_lamp[n], f"rg{n}", "connector0", 220 + n * 14, gate_lane, WIRE["gate"], f"{item['lamp']} to 1k gate resistor", 10)
        route_fanout(f"rg{n}", "connector1", f"q{n}", "connector0", 440 + n * 9, gate_lane + 18, WIRE["gate"], f"1k resistor to Q{n} gate", 10)
        route_around(f"q{n}", "connector0", f"rp{n}", "connector0", 620 + n * 12, pulldown_lane, WIRE["gate"], f"Q{n} gate to 10k pulldown", 8)
        route_vh(f"rp{n}", "connector1", f"gbus{n}", "tap0", local_gnd_y, WIRE["gnd"], f"10k pulldown branch to local GND bus", 8)
        route_h_then_v(f"gbus{n}", "tap5", "gndrail", f"tap{15+n}", 420 + 35 + (15+n) * 55, WIRE["gnd"], f"BTN{n} local GND bus trunk to common rail", 12)
        route_fanout(f"term{n}", "connector2", f"button{n}", "connector1", 975 + n * 8, swsig_lane, WIRE["switch_a"], f"BTN{n} plug SW SIG to arcade switch lug", 7)
        route_fanout(f"term{n}", "connector3", f"button{n}", "connector2", 1005 + n * 8, swgnd_lane, WIRE["gnd"], f"BTN{n} plug SW GND to arcade switch lug", 7)

    add("amp", "pam8403", "Generic PAM8403 5V mini amplifier", 650, 1705)
    add("speaker", "speaker", "SP1 4 ohm / 3W speaker", 1110, 1630, {"Resistance": "4 ohm", "Power": "3W"})
    add_label("audio_labels", ["Audio amp", "GPIO26 DAC/PWM -> L IN", "PAM8403 VCC -> +5V only", "Speaker across L+ / L-", "R channel unused"], 610, 1588, 330)

    route_around("amp5vrail", "tap18", "amp", "vcc", 1410, 1620, WIRE["vplus"], "PAM8403 VCC to +5V amp rail", 12)
    route_around("amp", "pwr_gnd", "gndrail", "tap13", 1225, 1860, WIRE["gnd"], "PAM8403 power GND to common GND", 12)
    route_around("amp", "in_gnd", "gndrail", "tap12", 600, 1878, WIRE["gnd"], "PAM8403 input GND to common GND", 10)
    route_around("esp", "connector23", "amp", "lin", 300, 1742, WIRE["audio"], "ESP32 GPIO26 DAC/PWM audio to PAM8403 L IN", 10)
    route_fanout("amp", "lplus", "speaker", "connector1", 1000, 1760, WIRE["speaker_pos"], "PAM8403 L+ to speaker red lead", 10)
    route_fanout("amp", "lminus", "speaker", "connector0", 1030, 1790, WIRE["speaker_neg"], "PAM8403 L- to speaker black lead", 10)

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


def export() -> None:
    if EXPORT_DIR.exists():
        for old in EXPORT_DIR.glob("*"):
            if old.is_file():
                old.unlink()
    else:
        EXPORT_DIR.mkdir(parents=True)
    shutil.copy2(FZZ_PATH, EXPORT_DIR / FZZ_PATH.name)
    subprocess.run([str(FRITZING), "-svg", str(EXPORT_DIR)], check=True)


def main() -> None:
    parts = build_parts()
    inst, wires = build_instances(parts)
    write_fzz(parts, inst, wires)
    export()
    print(f"Wrote {FZZ_PATH}")
    print(f"Editable part instances: {len(inst)}")
    print(f"Editable wires: {len(wires)}")
    print(f"Fritzing SVG export: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
