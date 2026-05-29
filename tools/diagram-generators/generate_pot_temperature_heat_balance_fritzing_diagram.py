from __future__ import annotations

import html
import math
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "pot-temperature-heat-balance"
FZZ_PATH = OUT_DIR / "chef_station_pot_temperature_heat_balance_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_pot_temperature_heat_balance_wiring_diagram.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_pot_temperature_heat_balance.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")


WIRE = {
    "vplus": "#f59e0b",
    "gnd": "#111111",
    "led_data": "#178f46",
    "encoder": "#1e88e5",
    "v3": "#7c3aed",
    "logic": "#f59e0b",
}


@dataclass
class Connector:
    cid: str
    name: str
    x: float
    y: float
    color: str = "#ffffff"


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
    z: float = 5


@dataclass
class Wire:
    idx: int
    title: str
    a: str
    ac: str
    b: str
    bc: str
    color: str
    width: float = 9


parts_dynamic: dict[str, Part] = {}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(
    x: float,
    y: float,
    value: str,
    size: int = 14,
    fill: str = "#1f2933",
    weight: int = 600,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{esc(value)}</text>'
    )


def read_stock_part(key: str, fzp_path: Path, pins: dict[str, tuple[float, float]]) -> Part:
    fzp = fzp_path.read_text(encoding="utf-8", errors="replace")
    module_id = re.search(r'moduleId="([^"]+)"', fzp).group(1)
    group = fzp_path.parent.name
    svg_entries: dict[str, str] = {}
    for image in re.findall(r'<layers image="([^"]+)"', fzp):
        view, filename = image.split("/", 1)
        candidates = [
            PARTS / "svg" / group / view / filename,
            PARTS / "svg" / "core" / view / filename,
            PARTS / "svg" / "contrib" / view / filename,
            PARTS / "svg" / "obsolete" / view / filename,
        ]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            layer = "silkscreen" if view == "pcb" else view
            svg_entries[f"svg.{view}.{filename}"] = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">\n'
                f'  <g id="{layer}"><rect x="1" y="1" width="18" height="18" fill="none" stroke="#9aa5b1"/></g>\n'
                '</svg>\n'
            )
        else:
            svg_entries[f"svg.{view}.{filename}"] = source.read_text(encoding="utf-8", errors="replace")
    return Part(key, module_id, f"part.{module_id}.fzp", fzp, svg_entries, pins)


def uniquify_svg_entries(part: Part) -> Part:
    renamed_entries: dict[str, str] = {}
    for old_entry, svg_text in part.svg_entries.items():
        view = old_entry.split(".")[1]
        old_file = old_entry.split(".", 2)[2]
        new_file = f"{part.module_id}_{view}.svg"
        part.fzp = part.fzp.replace(f"{view}/{old_file}", f"{view}/{new_file}")
        renamed_entries[f"svg.{view}.{new_file}"] = svg_text
    part.svg_entries = renamed_entries
    return part


def custom_part(
    key: str,
    title: str,
    label: str,
    width: int,
    height: int,
    body: str,
    connectors: list[Connector] | None = None,
    properties: dict[str, str] | None = None,
    buses: dict[str, list[str]] | None = None,
) -> Part:
    connectors = connectors or []
    properties = properties or {}
    buses = buses or {}
    module_id = f"chef_pot_temp_{key}"

    def svg_for(layer: str) -> str:
        connector_svg = []
        for connector in connectors:
            connector_svg.append(
                f'<circle id="{connector.cid}pin" cx="{connector.x}" cy="{connector.y}" r="5.0" '
                f'fill="{connector.color}" stroke="#111111" stroke-width="1.4">'
                f'<title>{esc(connector.name)}</title></circle>'
            )
            connector_svg.append(
                f'<circle id="{connector.cid}terminal" cx="{connector.x}" cy="{connector.y}" '
                f'r="1.5" fill="none" stroke="none"/>'
            )
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="{layer}">
    {body}
    {''.join(connector_svg)}
  </g>
</svg>
'''

    prop_xml = "\n".join(
        f'    <property name="{esc(name)}">{esc(value)}</property>' for name, value in properties.items()
    )
    connector_xml = []
    for connector in connectors:
        connector_xml.append(
            f'''    <connector id="{connector.cid}" type="male" name="{esc(connector.name)}">
      <description>{esc(connector.name)}</description>
      <views>
        <breadboardView><p layer="breadboard" svgId="{connector.cid}pin" terminalId="{connector.cid}terminal"/></breadboardView>
        <schematicView><p layer="schematic" svgId="{connector.cid}pin" terminalId="{connector.cid}terminal"/></schematicView>
        <pcbView><p layer="silkscreen" svgId="{connector.cid}pin" terminalId="{connector.cid}terminal"/></pcbView>
      </views>
    </connector>'''
        )
    if buses:
        bus_xml = ["  <buses>"]
        for bus_id, members in buses.items():
            bus_xml.append(f'    <bus id="{esc(bus_id)}">')
            for member in members:
                bus_xml.append(f'      <nodeMember connectorId="{esc(member)}"/>')
            bus_xml.append("    </bus>")
        bus_xml.append("  </buses>")
        buses_xml = "\n".join(bus_xml)
    else:
        buses_xml = "  <buses/>"

    fzp = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{module_id}">
  <version>1</version>
  <author>OpenAI Codex</author>
  <title>{esc(title)}</title>
  <label>{esc(label)}</label>
  <date>2026-05-29</date>
  <tags><tag>chef station</tag><tag>pot temperature</tag><tag>heat balance</tag><tag>esp32</tag></tags>
  <properties>
    <property name="family">Chef Station Pot Temperature Heat Balance</property>
{prop_xml}
  </properties>
  <description>{esc(title)}</description>
  <views>
    <iconView><layers image="icon/{module_id}.svg"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{module_id}.svg"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{module_id}.svg"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{module_id}.svg"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>
{chr(10).join(connector_xml)}
  </connectors>
{buses_xml}
</module>
'''
    return Part(
        key,
        module_id,
        f"part.{module_id}.fzp",
        fzp,
        {
            f"svg.icon.{module_id}.svg": svg_for("icon"),
            f"svg.breadboard.{module_id}.svg": svg_for("breadboard"),
            f"svg.schematic.{module_id}.svg": svg_for("schematic"),
            f"svg.pcb.{module_id}.svg": svg_for("silkscreen"),
        },
        {connector.cid: (connector.x, connector.y) for connector in connectors},
    )


def make_waveshare_esp32_p4_poe_eth_part() -> Part:
    module_id = "chef_pot_temp_waveshare_esp32_p4_poe_eth"
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
        if label == "GND":
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
    for side_pins, x, text_anchor, tx in [
        (left_pins, left_x, "end", left_x - 2),
        (right_pins, right_x, "start", right_x + 12),
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
    <text x="165" y="466" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="800" fill="#ffffff" text-anchor="middle">Local module</text>
    <text x="165" y="486" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#dbeafe" text-anchor="middle">encoder + WS2812 data</text>
    <text x="165" y="566" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">5V_LED powers LED strips</text>
    <text x="165" y="586" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">ESP32 pins provide data only</text>
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
    <property name="use">Chef Station standard PoE controller</property>
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


def make_label_part(
    key: str,
    lines: list[str],
    width: int = 280,
    size: int = 14,
    fill: str = "#fffefa",
    stroke: str = "#d0d7de",
) -> Part:
    height = max(36, 18 + len(lines) * (size + 5))
    body = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="5" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
    ]
    y = 19
    for index, line in enumerate(lines):
        line_fill = "#1f2933"
        if index == 0 and fill != "#fffefa":
            line_fill = "#7c2d12"
        body.append(text(9, y, line, size, line_fill, 700 if index == 0 else 500))
        y += size + 5
    return custom_part(key, lines[0], "TXT", width, height, "".join(body))


def make_waypoint_part() -> Part:
    body = '<circle id="pinmark" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/>'
    return custom_part("waypoint", "Wire waypoint", "WP", 6, 6, body, [Connector("pin", "waypoint", 3, 3)])


def make_resistor_part() -> Part:
    body = (
        '<line x1="0" y1="17" x2="30" y2="17" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="90" y1="17" x2="120" y2="17" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<rect x="30" y="4" width="60" height="26" rx="8" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>'
        '<rect x="39" y="5" width="4" height="24" fill="#f57c00"/>'
        '<rect x="50" y="5" width="4" height="24" fill="#f57c00"/>'
        '<rect x="61" y="5" width="4" height="24" fill="#6b4f1d"/>'
        '<rect x="72" y="5" width="4" height="24" fill="#c49a23"/>'
        + text(60, 48, "330-470 ohm", 13, "#1f2933", 700, "middle")
    )
    return custom_part(
        "resistor_330_data",
        "330-470 ohm LED data resistor",
        "R",
        120,
        58,
        body,
        [Connector("connector0", "lead A", 0, 17), Connector("connector1", "lead B", 120, 17)],
        properties={"Resistance": "330-470 ohm"},
    )


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 20) -> Part:
    width = 1060
    connectors = [Connector(f"tap{i}", f"{title} tap {i}", 35 + i * 52, 24) for i in range(tap_count)]
    circles = "".join(
        f'<circle cx="{35+i*52}" cy="24" r="4.2" fill="#ffffff" stroke="{color}" stroke-width="1.7"/>'
        for i in range(tap_count)
    )
    body = (
        f'<rect x="0" y="0" width="{width}" height="72" rx="8" fill="#ffffff" stroke="#9aa5b1" stroke-width="1.2"/>'
        f'<line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="8" stroke-linecap="round"/>'
        f'{circles}'
        f'{text(14, 58, note, 14, "#1f2933", 700)}'
    )
    return custom_part(key, title, "RAIL", width, 72, body, connectors, buses={key: [f"tap{i}" for i in range(tap_count)]})


def make_breadboard_part() -> Part:
    holes = []
    for x in range(42, 930, 24):
        for y in range(126, 850, 24):
            holes.append(f'<circle cx="{x}" cy="{y}" r="2.0" fill="#d9d2c3"/>')
    body = (
        '<rect x="0" y="0" width="1100" height="930" rx="10" fill="#f1ead7" stroke="#d8ccb0" stroke-width="2"/>'
        + text(24, 36, "Manhattan breadboard / power distribution", 23, "#52606d", 700)
        + text(24, 65, "Power rails stay horizontal; branches use clean 90-degree routes", 15, "#52606d", 500)
        + "".join(holes)
    )
    return custom_part("breadboard_backplane", "Breadboard and power rails area", "BB", 1100, 930, body)


def make_supply_part() -> Part:
    body = (
        '<rect x="0" y="0" width="260" height="135" rx="8" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(16, 25, "5V_LED input", 18, "#1f2933", 700)
        + text(16, 49, "from master rails", 18, WIRE["vplus"], 700)
        + text(16, 80, "+ to local 5V_LED rail", 14, "#1f2933", 600)
        + text(16, 102, "- to COMMON_GND", 14, "#1f2933", 600)
        + text(212, 52, "5V_LED", 13, WIRE["vplus"], 700, "end")
        + text(212, 97, "GND", 13, WIRE["gnd"], 700, "end")
    )
    return custom_part(
        "external_5v_supply",
        "5V_LED rail input from master power distribution",
        "5V_LED",
        260,
        135,
        body,
        [Connector("vcc", "5V_LED", 236, 48), Connector("gnd", "COMMON_GND", 236, 94)],
    )


def make_encoder_part() -> Part:
    pin_labels = [
        ("vcc", "VCC 3.3V", WIRE["v3"]),
        ("gnd", "GND", WIRE["gnd"]),
        ("clk", "A / CLK", WIRE["encoder"]),
        ("dt", "B / DT", WIRE["encoder"]),
        ("sw", "SW", WIRE["encoder"]),
    ]
    connectors = [Connector(cid, label, 34 + i * 48, 28, color) for i, (cid, label, color) in enumerate(pin_labels)]
    body = (
        '<rect x="0" y="0" width="260" height="230" rx="9" fill="#ecfeff" stroke="#0891b2" stroke-width="2"/>'
        '<circle cx="130" cy="126" r="62" fill="#1f2937" stroke="#111827" stroke-width="4"/>'
        '<circle cx="130" cy="126" r="33" fill="#64748b" stroke="#94a3b8" stroke-width="3"/>'
        '<line x1="130" y1="126" x2="160" y2="97" stroke="#f8fafc" stroke-width="5" stroke-linecap="round"/>'
        + text(130, 205, "Rotary encoder / KY-040", 17, "#164e63", 800, "middle")
        + text(130, 224, "CW increases heat, CCW decreases", 12, "#164e63", 600, "middle")
    )
    for i, (_cid, label, color) in enumerate(pin_labels):
        body += text(34 + i * 48, 52, label, 10, color, 800, "middle")
    return custom_part(
        "rotary_encoder_ky040",
        "Rotary encoder with optional KY-040 module VCC",
        "ENC",
        260,
        230,
        body,
        connectors,
        properties={"input mode": "ESP32 INPUT_PULLUP on A/CLK, B/DT, and SW"},
    )


def make_rgb_coil_part() -> Part:
    coils = []
    for r, color, width in [(132, "#b91c1c", 12), (104, "#ef4444", 10), (76, "#f97316", 9), (48, "#fb923c", 8)]:
        coils.append(f'<circle cx="205" cy="190" r="{r}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    leds = []
    for index in range(18):
        angle = math.radians(index * 20)
        leds.append(
            f'<circle cx="{205 + 122 * math.cos(angle):.1f}" cy="{190 + 122 * math.sin(angle):.1f}" '
            f'r="6" fill="#fed7aa" stroke="#f97316" stroke-width="1"/>'
        )
    body = (
        '<rect x="0" y="0" width="420" height="390" rx="12" fill="#20242a" stroke="#111827" stroke-width="2"/>'
        + "".join(coils)
        + "".join(leds)
        + text(22, 35, "+5V", 13, "#ffffff", 700)
        + text(22, 73, "DIN", 13, "#ffffff", 700)
        + text(22, 111, "GND", 13, "#ffffff", 700)
        + text(210, 348, "Red/orange cooktop heat coil", 18, "#ffffff", 700, "middle")
        + text(210, 371, "WS2812B style; brightness = heat setting", 12, "#ffffff", 500, "middle")
    )
    return custom_part(
        "cooktop_coil_strip",
        "Red/orange cooktop heat coil RGB strip",
        "LED",
        420,
        390,
        body,
        [
            Connector("vcc", "LED strip +5V", 20, 31),
            Connector("din", "LED strip DIN", 20, 69),
            Connector("gnd", "LED strip GND", 20, 107),
        ],
    )


def make_temp_indicator_part() -> Part:
    leds = []
    zone_colors = ["#2563eb"] * 6 + ["#f8fafc"] * 6 + ["#dc2626"] * 6
    for index, color in enumerate(zone_colors):
        angle = math.radians(-90 + index * 20)
        leds.append(
            f'<circle cx="{205 + 108 * math.cos(angle):.1f}" cy="{164 + 108 * math.sin(angle):.1f}" '
            f'r="9" fill="{color}" stroke="#334155" stroke-width="1.2"/>'
        )
    body = (
        '<rect x="0" y="0" width="420" height="340" rx="12" fill="#f8fafc" stroke="#94a3b8" stroke-width="2"/>'
        '<circle cx="205" cy="164" r="132" fill="#e2e8f0" stroke="#64748b" stroke-width="2"/>'
        '<circle cx="205" cy="164" r="82" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>'
        '<path d="M160 210 C158 162 252 162 250 210 Z" fill="#cbd5e1" stroke="#64748b" stroke-width="2"/>'
        '<rect x="150" y="205" width="110" height="22" rx="6" fill="#94a3b8" stroke="#64748b" stroke-width="2"/>'
        + "".join(leds)
        + text(22, 35, "+5V", 13, WIRE["vplus"], 700)
        + text(22, 73, "DIN", 13, WIRE["led_data"], 700)
        + text(22, 111, "GND", 13, WIRE["gnd"], 700)
        + text(210, 286, "Pot temperature indicator", 18, "#1f2933", 700, "middle")
        + text(210, 310, "BLUE cold  |  WHITE correct  |  RED hot", 13, "#1f2933", 700, "middle")
    )
    return custom_part(
        "pot_temperature_indicator",
        "Pot temperature LED strip or ring",
        "TEMP",
        420,
        340,
        body,
        [
            Connector("vcc", "Temperature indicator +5V", 20, 31),
            Connector("din", "Temperature indicator DIN", 20, 69),
            Connector("gnd", "Temperature indicator GND", 20, 107),
        ],
    )


def build_parts() -> dict[str, Part]:
    return {
        "esp32": make_waveshare_esp32_p4_poe_eth_part(),
        "cap1000": uniquify_svg_entries(
            read_stock_part(
                "cap1000",
                PARTS / "obsolete" / "electrolytic_capacitor_1000uF.fzp",
                {"connector0": (20.64, 97.26), "connector1": (30.64, 97.26)},
            )
        ),
        "r330": make_resistor_part(),
        "breadboard": make_breadboard_part(),
        "supply": make_supply_part(),
        "vrail": make_rail_part("local_5v_led_rail", "5V_LED rail", WIRE["vplus"], "5V_LED from master power: temp ring and 5V cooktop LED strips only"),
        "v3rail": make_rail_part("esp32_3v3_encoder_rail", "ESP32 3.3V encoder rail", WIRE["v3"], "Optional KY-040 VCC: 3.3V only, never external +5V"),
        "gndrail": make_rail_part("common_ground_rail", "COMMON_GND rail", WIRE["gnd"], "COMMON_GND: ESP32 + 5V_LED return + both LED strips + encoder"),
        "encoder": make_encoder_part(),
        "coil": make_rgb_coil_part(),
        "indicator": make_temp_indicator_part(),
        "waypoint": make_waypoint_part(),
    }


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
          <geometry z="{inst.z:.2f}" x="{inst.x:.2f}" y="{inst.y:.2f}"/>{connectors_block}
        </breadboardView>
      </views>
    </instance>'''


def wire_xml(wire: Wire, insts: dict[str, Instance], parts: dict[str, Part]) -> str:
    a, b = insts[wire.a], insts[wire.b]
    ax, ay = parts[a.part].pins[wire.ac]
    bx, by = parts[b.part].pins[wire.bc]
    x1, y1 = a.x + ax, a.y + ay
    x2, y2 = b.x + bx, b.y + by
    return f'''    <instance moduleIdRef="WireModuleID" modelIndex="{wire.idx}" path=":/resources/parts/core/wire.fzp">
      <title>{esc(wire.title)}</title>
      <views>
        <breadboardView layer="breadboardWire">
          <geometry z="9" x="{x1:.2f}" y="{y1:.2f}" x1="0" y1="0" x2="{x2 - x1:.2f}" y2="{y2 - y1:.2f}" wireFlags="64"/>
          <wireExtras mils="{wire.width:.2f}" color="{wire.color}" opacity="1" banded="0"/>
          <connectors>
            <connector connectorId="connector0" layer="breadboardWire"><geometry x="0" y="0"/><connects><connect connectorId="{wire.ac}" modelIndex="{a.idx}" layer="breadboard"/></connects></connector>
            <connector connectorId="connector1" layer="breadboardWire"><geometry x="0" y="0"/><connects><connect connectorId="{wire.bc}" modelIndex="{b.idx}" layer="breadboard"/></connects></connector>
          </connectors>
        </breadboardView>
      </views>
    </instance>'''


def build_instances(parts: dict[str, Part]) -> tuple[list[Instance], list[Wire]]:
    inst: list[Instance] = []
    wires: list[Wire] = []
    idx = 1000
    widx = 5000

    def add(key: str, part: str, title: str, x: float, y: float, props: dict[str, str] | None = None, z: float = 5) -> Instance:
        nonlocal idx
        idx += 1
        item = Instance(key, part, title, x, y, idx, props or {}, z=z)
        inst.append(item)
        return item

    def add_label(
        key: str,
        lines: list[str],
        x: float,
        y: float,
        width: int = 280,
        size: int = 14,
        fill: str = "#fffefa",
        stroke: str = "#d0d7de",
    ) -> Instance:
        parts_dynamic[key] = make_label_part(key, lines, width, size, fill, stroke)
        return add(key, key, lines[0], x, y, z=12)

    def add_waypoint(key: str, x: float, y: float) -> Instance:
        return add(key, "waypoint", key, x - 3, y - 3, z=8)

    def all_parts() -> dict[str, Part]:
        return {**parts, **parts_dynamic}

    def abs_pos(key: str, conn: str) -> tuple[float, float]:
        by_key = {item.key: item for item in inst}
        item = by_key[key]
        px, py = all_parts()[item.part].pins[conn]
        return item.x + px, item.y + py

    def wire(a: str, ac: str, b: str, bc: str, color: str, title: str, width: float = 9) -> None:
        nonlocal widx
        ax, ay = abs_pos(a, ac)
        bx, by = abs_pos(b, bc)
        if abs(ax - bx) < 0.01 and abs(ay - by) < 0.01:
            return
        widx += 1
        wires.append(Wire(widx, title, a, ac, b, bc, color, width))

    def routed_wire(
        a: str,
        ac: str,
        b: str,
        bc: str,
        points: list[tuple[float, float]],
        color: str,
        title: str,
        width: float = 9,
    ) -> None:
        prev_key, prev_conn = a, ac
        last_x, last_y = abs_pos(a, ac)
        end_x, end_y = abs_pos(b, bc)
        for point_index, (x, y) in enumerate(points):
            if abs(x - last_x) < 0.01 and abs(y - last_y) < 0.01:
                continue
            if abs(x - end_x) < 0.01 and abs(y - end_y) < 0.01:
                continue
            wp_key = f"wp_{len(wires)}_{point_index}_{len(inst)}"
            add_waypoint(wp_key, x, y)
            wire(prev_key, prev_conn, wp_key, "pin", color, f"{title} segment {point_index + 1}", width)
            prev_key, prev_conn = wp_key, "pin"
            last_x, last_y = x, y
        wire(prev_key, prev_conn, b, bc, color, title, width)

    def manhattan_wire(
        a: str,
        ac: str,
        b: str,
        bc: str,
        color: str,
        title: str,
        width: float = 9,
        mode: str = "hvh",
        lane: float | None = None,
    ) -> None:
        ax, ay = abs_pos(a, ac)
        bx, by = abs_pos(b, bc)
        if abs(ax - bx) < 0.01 or abs(ay - by) < 0.01:
            routed_wire(a, ac, b, bc, [], color, title, width)
            return
        if mode == "hvh":
            lane_x = lane if lane is not None else (ax + bx) / 2
            points = [(lane_x, ay), (lane_x, by)]
        elif mode == "vhv":
            lane_y = lane if lane is not None else (ay + by) / 2
            points = [(ax, lane_y), (bx, lane_y)]
        elif mode == "hv":
            points = [(bx, ay)]
        elif mode == "vh":
            points = [(ax, by)]
        else:
            raise ValueError(f"Unknown Manhattan route mode: {mode}")
        routed_wire(a, ac, b, bc, points, color, title, width)

    global parts_dynamic
    parts_dynamic = {}

    add_label(
        "title",
        [
            'Chef Station "Pot Temperature / Heat Balance" wiring',
            "Rotary heat control, red/orange cooktop coil, local pot temperature feedback",
        ],
        28,
        18,
        860,
        18,
    )
    add_label(
        "pin_table",
        [
            "Pin assignment summary",
            "GPIO32: Rotary encoder A / CLK",
            "GPIO33: Rotary encoder B / DT",
            "GPIO27: Rotary encoder pushbutton / SW",
            "GPIO23: Cooktop coil RGB strip data",
            "GPIO18: Pot temperature indicator data",
        ],
        28,
        105,
        430,
        13,
    )
    add_label(
        "controller_note",
        [
            "Controller note",
            "Drawn on the standard Chef Station Waveshare PoE board.",
            "The requested ESP32 GPIO map is preserved.",
            "Verify exact pins before harness fabrication.",
            "Do not feed external +5V into any 3.3V pin.",
        ],
        28,
        252,
        460,
        13,
    )
    add_label(
        "power_callout",
        [
            "Power callouts",
            "COMMON_GND is required for shared LED data/control.",
            "LED strips use 5V_LED from the master rails.",
            "If the cooktop coil is a 12V strip, use 12V_SHOW instead.",
            "ESP32 only provides LED data signals.",
            "PoE powers the ESP32 controller only.",
        ],
        34,
        1090,
        520,
        13,
        "#fff7ed",
        "#f59e0b",
    )
    add_label(
        "encoder_callout",
        [
            "Encoder notes",
            "Use ESP32 INPUT_PULLUP for A, B, and SW.",
            "Bare encoder common goes to GND.",
            "KY-040 VCC, if used, goes to ESP32 3.3V.",
            "Use software debounce and quadrature state tracking.",
            "Clamp heatSetting from 0-100 percent.",
            "Knob controls heat power, not direct temperature.",
        ],
        1040,
        1190,
        470,
        13,
        "#eff6ff",
        "#1e88e5",
    )
    add_label(
        "led_callout",
        [
            "LED behavior callouts",
            "Cooktop coil stays red/orange.",
            "Coil brightness maps directly to heatSetting.",
            "Pot indicator shows simulated potTemperature.",
            "BLUE = too cold, WHITE = correct, RED = too hot.",
            "Local LEDs must communicate gameplay without monitor.",
        ],
        1564,
        1090,
        570,
        13,
        "#fff7ed",
        "#f59e0b",
    )
    add_label(
        "game_logic_panel",
        [
            "Game logic side panel",
            "Fixed round duration, such as 30 or 60 seconds.",
            "heatSetting: 0.0 to 1.0; potTemp: 0.0 to 1.0.",
            "potTemp uses velocity and damping, not instant jumps.",
            "drift is a slow random walk so balance moves fairly.",
            "accel = (heatSetting - balancePoint + drift) * tuning.",
            "Cold: potTemp < 0.42; Correct: 0.42-0.58; Hot: > 0.58.",
            "scorePercent = correctZoneMs / totalGameMs * 100.",
            'Serial event: {"station":"chef","module":"pot_temp","event":"score","percent":73}',
        ],
        1290,
        38,
        850,
        13,
        "#fffbeb",
        "#f59e0b",
    )
    add_label(
        "resistor_labels",
        [
            "LED data protection",
            "R1: 330-470 ohm on GPIO23 -> cooktop DIN.",
            "R2: 330-470 ohm on GPIO18 -> temp indicator DIN.",
            "Place resistors near the first LED DIN when practical.",
        ],
        792,
        282,
        445,
        13,
    )
    add_label(
        "cap_note",
        [
            "1000uF capacitor",
            "Place across LED +5V and GND near strip power input.",
            "Observe electrolytic polarity.",
        ],
        1080,
        230,
        330,
        13,
        "#fff7ed",
        "#f59e0b",
    )

    add("esp", "esp32", "Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH", 70, 330)
    add("breadboard", "breadboard", "Manhattan breadboard and rails area", 385, 118, z=30)
    add("supply", "supply", "5V_LED input from master power rails", 930, 62)
    add("vrail", "vrail", "5V_LED local rail", 525, 152)
    add("v3rail", "v3rail", "ESP32 3.3V optional encoder rail", 525, 242)
    add("gndrail", "gndrail", "COMMON_GND rail", 525, 1000)
    add("r_coil", "r330", "R1 330-470 ohm cooktop coil data resistor", 884, 380, {"Resistance": "330-470 ohm"})
    add("r_indicator", "r330", "R2 330-470 ohm pot temperature data resistor", 884, 575, {"Resistance": "330-470 ohm"})
    add("encoder", "encoder", "Rotary encoder / KY-040 heat control", 750, 1190, z=7)
    add("coil", "coil", "Cooktop coil RGB strip: +5V / DIN / GND", 1530, 292, z=4)
    add("indicator", "indicator", "Pot temperature indicator strip/ring: +5V / DIN / GND", 1530, 710, z=4)
    add("c_led", "cap1000", "C1 1000uF electrolytic near LED power input", 1432, 300, {"Capacitance": "1000uF"}, z=8)

    # Main power rails.
    supply_vcc_x, _supply_vcc_y = abs_pos("supply", "vcc")
    vrail_tap8_x, _vrail_tap8_y = abs_pos("vrail", "tap8")
    routed_wire(
        "supply",
        "vcc",
        "vrail",
        "tap8",
        [(supply_vcc_x, 90), (vrail_tap8_x, 90)],
        WIRE["vplus"],
        "5V_LED input to local 5V_LED rail",
        11,
    )
    supply_gnd_x, _supply_gnd_y = abs_pos("supply", "gnd")
    _gnd_tap0_x, gnd_tap0_y = abs_pos("gndrail", "tap0")
    routed_wire(
        "supply",
        "gnd",
        "gndrail",
        "tap0",
        [(supply_gnd_x, 90), (440, 90), (440, gnd_tap0_y)],
        WIRE["gnd"],
        "5V_LED return to COMMON_GND rail",
        11,
    )
    manhattan_wire("esp", "gnd_r2", "gndrail", "tap1", WIRE["gnd"], "ESP32 GND reference to COMMON_GND rail", 10, "hvh", 430)
    manhattan_wire("esp", "3v3", "v3rail", "tap0", WIRE["v3"], "ESP32 3.3V to optional encoder VCC rail", 9, "hvh", 430)

    # LED strip power distribution.
    manhattan_wire("vrail", "tap18", "coil", "vcc", WIRE["vplus"], "Cooktop coil +5V to 5V_LED rail if using 5V strip", 10, "hvh", 1440)
    manhattan_wire("gndrail", "tap18", "coil", "gnd", WIRE["gnd"], "Cooktop coil GND to COMMON_GND rail", 10, "hvh", 1460)
    manhattan_wire("vrail", "tap19", "indicator", "vcc", WIRE["vplus"], "Temperature indicator +5V to 5V_LED rail", 10, "hvh", 1490)
    manhattan_wire("gndrail", "tap19", "indicator", "gnd", WIRE["gnd"], "Temperature indicator GND to COMMON_GND rail", 10, "hvh", 1510)
    manhattan_wire("c_led", "connector1", "coil", "vcc", WIRE["vplus"], "C1 positive across LED +5V", 8, "hvh", 1500)
    manhattan_wire("c_led", "connector0", "coil", "gnd", WIRE["gnd"], "C1 negative across LED GND", 8, "hvh", 1480)

    # LED data lines through 330-470 ohm resistors.
    manhattan_wire("esp", "gpio23", "r_coil", "connector0", WIRE["led_data"], "GPIO23 to cooktop LED data resistor", 9, "vhv", 438)
    manhattan_wire("r_coil", "connector1", "coil", "din", WIRE["led_data"], "R1 to cooktop coil DIN", 9, "vhv", 442)
    routed_wire(
        "esp",
        "gpio18",
        "r_indicator",
        "connector0",
        [(36, abs_pos("esp", "gpio18")[1]), (36, 620), (740, 620), (740, abs_pos("r_indicator", "connector0")[1])],
        WIRE["led_data"],
        "GPIO18 to pot temperature indicator data resistor",
        9,
    )
    manhattan_wire("r_indicator", "connector1", "indicator", "din", WIRE["led_data"], "R2 to temperature indicator DIN", 9, "vhv", 622)

    # Rotary encoder power and signals.
    manhattan_wire("v3rail", "tap5", "encoder", "vcc", WIRE["v3"], "Optional KY-040 VCC to ESP32 3.3V", 8, "hvh", 700)
    manhattan_wire("gndrail", "tap5", "encoder", "gnd", WIRE["gnd"], "Encoder common/GND to COMMON_GND rail", 9, "hvh", 730)
    manhattan_wire("esp", "gpio32", "encoder", "clk", WIRE["encoder"], "GPIO32 to encoder A / CLK", 9, "hvh", 560)
    manhattan_wire("esp", "gpio33", "encoder", "dt", WIRE["encoder"], "GPIO33 to encoder B / DT", 9, "hvh", 610)
    manhattan_wire("esp", "gpio27", "encoder", "sw", WIRE["encoder"], "GPIO27 to encoder pushbutton / SW", 9, "hvh", 660)

    by_key = {item.key: item for item in inst}
    for item in wires:
        by_key[item.a].connects.setdefault(item.ac, []).append((item.idx, "connector0"))
        by_key[item.b].connects.setdefault(item.bc, []).append((item.idx, "connector1"))

    return inst, wires


def write_fzz(parts: dict[str, Part], inst: list[Instance], wires: list[Wire]) -> None:
    all_parts = {**parts, **parts_dynamic}
    by_key = {item.key: item for item in inst}
    fz_instances = "\n".join([wire_xml(wire, by_key, all_parts) for wire in wires] + [instance_xml(item, all_parts) for item in inst])
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
    with zipfile.ZipFile(FZZ_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("chef_station_pot_temperature_heat_balance_editable.fz", fz)
        for part in all_parts.values():
            zf.writestr(part.fzp_name, part.fzp)
            for name, text_value in part.svg_entries.items():
                zf.writestr(name, text_value)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Pot Temperature / Heat Balance Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO32 | Rotary encoder A / CLK |
| GPIO33 | Rotary encoder B / DT |
| GPIO27 | Rotary encoder pushbutton / SW |
| GPIO23 | Cooktop coil RGB strip data through 330-470 ohm resistor |
| GPIO18 | Pot temperature indicator RGB strip/ring data through 330-470 ohm resistor |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power cooktop LEDs or indicator LEDs from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the temperature indicator and any 5V cooktop LED strip.
- `5V_LED` return connects to `COMMON_GND`.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data or encoder signals share external references.
- Cooktop coil strip +5V connects to `5V_LED` if it is a 5V strip. If it is a true 12V strip, connect it to `12V_SHOW` instead and keep only its data/control reference common.
- Cooktop coil strip GND connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to the cooktop coil strip DIN.
- Pot temperature indicator +5V connects to `5V_LED`.
- Pot temperature indicator GND connects to `COMMON_GND`.
- ESP32 GPIO18 connects through a 330-470 ohm resistor to the temperature indicator DIN.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip power input.
- Observe electrolytic capacitor polarity.
- Rotary encoder A / CLK connects to GPIO32.
- Rotary encoder B / DT connects to GPIO33.
- Rotary encoder SW connects to GPIO27.
- Rotary encoder common / GND connects to `COMMON_GND`.
- If using a KY-040 style encoder module, connect module VCC to ESP32 3.3V, not `5V_LED` or `12V_SHOW`.
- Use ESP32 `INPUT_PULLUP` for encoder A / CLK, B / DT, and SW.
- Do not feed external +5V into the ESP32 `3V3` pin.
- All grounds must be common where signals cross rails: ESP32, `5V_LED` return, cooktop coil strip, temperature indicator, and encoder.

## Callout Notes

- Common ground: the `5V_LED` return and ESP32 ground must be tied together where LED data crosses power domains.
- External LED power: LED strips use `5V_LED` or `12V_SHOW` by device rating; the ESP32 only provides data signals.
- Encoder INPUT_PULLUP wiring: A / CLK, B / DT, and SW should read HIGH idle and LOW when pulled to COMMON_GND.
- Cooktop coil brightness represents heat setting, not measured temperature.
- Temperature indicator represents simulated pot temperature, not a real sensor reading.
- Score is the percentage of total game time spent in the white/correct zone.

## Firmware Behavior Notes

- Use a fixed game duration, such as 30 or 60 seconds.
- Rotary encoder controls `heatSetting` from 0.0 to 1.0.
- Clockwise rotation increases heat; counterclockwise rotation decreases heat.
- Clamp heat setting from 0-100 percent.
- Cooktop coil color should remain red/orange and vary brightness from `heatSetting`.
- `potTemperature` is simulated, not directly measured.
- Model temperature with velocity/acceleration and damping so it feels physical.
- Higher `heatSetting` increases upward temperature acceleration.
- Lower `heatSetting` allows temperature to fall.
- Add random drift as a slow random walk so the balance point moves over time.
- Random drift should be slow and fair, not sudden or punitive.
- Suggested model: `acceleration = (heatSetting - balancePoint + drift) * tuningFactor`.
- Update `tempVelocity += acceleration * dt`, damp velocity, then update `potTemp += tempVelocity * dt`.
- Constrain `potTemp` to 0.0-1.0.
- `potTemp < 0.42` is TOO COLD / BLUE.
- `0.42 <= potTemp <= 0.58` is CORRECT / WHITE.
- `potTemp > 0.58` is TOO HOT / RED.
- Track milliseconds in the correct zone and total round milliseconds.
- At end of round, report `scorePercent = correctZoneMs / totalGameMs * 100`.
- Example Serial event: `{"station":"chef","module":"pot_temp","event":"score","percent":73}`.

## Game-State Notes

- IDLE: coil dim/off and temperature indicator idle glow.
- ACTIVE: encoder is live and temperature simulation runs.
- SCORING: freeze indicator and report score.
- RESET: clear score, recenter temperature, and recalibrate drift.
- The player should instantly understand that turning the knob changes heat.
- The pot temperature should not stay stable without input.
- The correct/white zone should be forgiving enough for public event use.
- Monitor graphics may show polish and score, but local LEDs should communicate the core gameplay.

## Assumptions And Part Notes

- Controller: diagram uses a custom Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH PoE helper part.
- The requested ESP32 GPIO function map is preserved on that PoE board helper. Verify exact pin availability before final harness fabrication.
- Accessory rail assumption: temperature LEDs use `5V_LED`; any actual 12V cooktop strip must move to `12V_SHOW`.
- LED strips/rings are represented as custom WS2812B-style helper parts so the +5V, DIN, and GND pins are explicit.
- Rotary encoder is represented as a custom KY-040/bare-encoder helper part so VCC, GND, A/CLK, B/DT, and SW are labeled clearly.
- 1000uF electrolytic capacitor uses the installed Fritzing stock part.
- Resistors, rails, supply, breadboard backplane, LED visuals, encoder, and callout notes are custom editable Fritzing helper parts for readability.
""",
        encoding="utf-8",
    )


def export_svg() -> Path:
    if EXPORT_DIR.exists():
        for old in EXPORT_DIR.iterdir():
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
            "--window-size=2600,1700",
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
    svg_path = export_svg()
    render_png(svg_path)
    print(f"Wrote {FZZ_PATH}")
    print(f"Wrote {svg_path}")
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {CHECKLIST_PATH}")
    print(f"Editable part instances: {len(inst)}")
    print(f"Editable wire segments: {len(wires)}")
    print(f"Diagonal wire segments: {count_diagonal_segments(inst, wires, parts)}")


if __name__ == "__main__":
    main()
