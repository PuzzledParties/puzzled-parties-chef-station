from __future__ import annotations

import html
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from module_protocol_helpers import make_protocol_esp32_poe_part


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "chopping-module"
FZZ_PATH = OUT_DIR / "chef_station_chopping_module_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_chopping_module_wiring_diagram.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_chopping_module.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


WIRE = {
    "v5": "#f59e0b",
    "gnd": "#111111",
    "v3": "#7c3aed",
    "ethernet": "#1e88e5",
    "piezo": "#f59e0b",
    "piezo_alt": "#f97316",
    "sda": "#1e88e5",
    "scl": "#2563eb",
    "start": "#178f46",
    "reset": "#7e3fb2",
    "done": "#8b5cf6",
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


def read_esp32_part() -> Part:
    raw = {
        "connector0": (156, 72),   # 3V3 header pin
        "connector1": (156, 96),   # GND header pin
        "connector10": (22, 148),  # SDA / GPIO7
        "connector13": (22, 132),  # SCL / GPIO8
        "connector18": (22, 72),   # GPIO16 / ADC1_CH0
        "connector28": (22, 164),  # GND header pin
    }
    labels = {
        "connector0": "3V3 sensor rail",
        "connector1": "GND",
        "connector10": "SDA/GPIO7",
        "connector13": "SCL/GPIO8",
        "connector18": "GPIO16 / ADC1_CH0",
        "connector28": "GND",
    }
    return make_protocol_esp32_poe_part(
        custom_part=custom_part,
        connector_cls=Connector,
        key="waveshare_esp32_poe_eth",
        title="Waveshare ESP32-P4-ETH / ESP32-P4-POE-ETH",
        pins=raw,
        labels=labels,
        wire=WIRE,
        family="Chef Station Chopping Module",
        extra_note="Piezo/LCD signals only; LCD backlight uses 5V_AUX.",
    )


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
    module_id = f"chef_chop_{key}"

    def svg_for(layer: str) -> str:
        connector_svg = []
        for connector in connectors:
            connector_svg.append(
                f'<circle id="{connector.cid}pin" cx="{connector.x}" cy="{connector.y}" r="5.1" '
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
  <tags><tag>chef station</tag><tag>chopping module</tag><tag>esp32</tag><tag>piezo</tag></tags>
  <properties>
    <property name="family">Chef Station Chopping Module</property>
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


def make_label_part(key: str, lines: list[str], width: int = 300, size: int = 14) -> Part:
    height = max(38, 18 + len(lines) * (size + 5))
    body = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="5" '
        f'fill="#fffefa" stroke="#d0d7de" stroke-width="1.2"/>'
    ]
    y = 20
    for index, line in enumerate(lines):
        body.append(text(10, y, line, size, "#1f2933", 700 if index == 0 else 500))
        y += size + 5
    return custom_part(key, lines[0], "TXT", width, height, "".join(body))


def make_waypoint_part() -> Part:
    body = '<circle id="pinmark" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/>'
    return custom_part("waypoint", "Wire waypoint", "WP", 6, 6, body, [Connector("pin", "waypoint", 3, 3)])


def make_resistor_part(key: str, title: str, value_label: str, bands: list[str]) -> Part:
    body = (
        '<line x1="0" y1="17" x2="30" y2="17" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="90" y1="17" x2="120" y2="17" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<rect x="30" y="4" width="60" height="26" rx="8" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>'
        f'<rect x="39" y="5" width="4" height="24" fill="{bands[0]}"/>'
        f'<rect x="50" y="5" width="4" height="24" fill="{bands[1]}"/>'
        f'<rect x="61" y="5" width="4" height="24" fill="{bands[2]}"/>'
        f'<rect x="72" y="5" width="4" height="24" fill="{bands[3]}"/>'
        + text(60, 48, value_label, 13, "#1f2933", 700, "middle")
    )
    return custom_part(
        key,
        title,
        "R",
        120,
        58,
        body,
        [Connector("connector0", "lead A", 0, 17), Connector("connector1", "lead B", 120, 17)],
        properties={"Resistance": value_label},
    )


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 18) -> Part:
    width = 990
    connectors = [Connector(f"tap{i}", f"{title} tap {i}", 35 + i * 54, 24) for i in range(tap_count)]
    circles = "".join(
        f'<circle cx="{35+i*54}" cy="24" r="4.2" fill="#ffffff" stroke="{color}" stroke-width="1.7"/>'
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
    for x in range(42, 900, 24):
        for y in range(122, 880, 24):
            holes.append(f'<circle cx="{x}" cy="{y}" r="2.0" fill="#d9d2c3"/>')
    body = (
        '<rect x="0" y="0" width="1060" height="980" rx="10" fill="#f1ead7" stroke="#d8ccb0" stroke-width="2"/>'
        + text(24, 36, "Manhattan breadboard / power distribution", 23, "#52606d", 700)
        + text(24, 65, "Straight 90-degree wire lanes; rails are shared buses", 15, "#52606d", 500)
        + "".join(holes)
    )
    return custom_part("breadboard_backplane", "Breadboard and power rails area", "BB", 1060, 980, body)


def make_supply_part() -> Part:
    body = (
        '<rect x="0" y="0" width="270" height="136" rx="8" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(16, 25, "5V_AUX input", 18, "#1f2933", 700)
        + text(16, 49, "from master rails", 18, WIRE["v5"], 700)
        + text(16, 80, "+ to local 5V_AUX rail", 14, "#1f2933", 600)
        + text(16, 103, "- to COMMON_GND", 14, "#1f2933", 600)
        + text(218, 52, "5V_AUX", 13, WIRE["v5"], 700, "end")
        + text(218, 97, "GND", 13, WIRE["gnd"], 700, "end")
    )
    return custom_part(
        "external_5v_supply",
        "5V_AUX rail input from master power distribution",
        "5V_AUX",
        270,
        136,
        body,
        [Connector("vcc", "5V_AUX", 244, 48), Connector("gnd", "COMMON_GND", 244, 94)],
    )


def make_piezo_module_part() -> Part:
    body = (
        '<rect x="0" y="0" width="360" height="182" rx="8" fill="#fff7ed" stroke="#f97316" stroke-width="2"/>'
        '<circle cx="250" cy="92" r="52" fill="#fef3c7" stroke="#b45309" stroke-width="3"/>'
        '<circle cx="250" cy="92" r="21" fill="#fde68a" stroke="#b45309" stroke-width="2"/>'
        '<rect x="28" y="26" width="84" height="132" rx="7" fill="#0f172a" stroke="#111827" stroke-width="2"/>'
        + text(41, 50, "VCC", 13, WIRE["v3"], 700)
        + text(41, 83, "GND", 13, WIRE["gnd"], 700)
        + text(41, 116, "AO", 13, WIRE["piezo"], 700)
        + text(41, 149, "DO", 13, "#64748b", 700)
        + text(180, 30, "Piezo knock/vibration module", 18, "#9a3412", 700, "middle")
        + text(180, 157, "Use AO for scoring; DO optional debug only", 13, "#1f2933", 600, "middle")
    )
    return custom_part(
        "piezo_module",
        "Piezo knock/vibration sensor module",
        "PIEZO",
        360,
        182,
        body,
        [
            Connector("vcc", "VCC 3.3V", 18, 44),
            Connector("gnd", "GND", 18, 78),
            Connector("ao", "AO analog output", 18, 112),
            Connector("do", "DO optional debug, not main input", 18, 146),
        ],
        properties={"sensor": "Piezo module powered at 3.3V; use AO analog output"},
    )


def make_lcd_part() -> Part:
    screen_lines = [
        "CHOP FASTER",
        "KEEP GOING",
        "[=======-------------]",
        "Chops: 037/100",
    ]
    line_svg = []
    y = 82
    for line in screen_lines:
        line_svg.append(
            f'<text x="292" y="{y}" font-family="Consolas, monospace" font-size="23" '
            f'font-weight="700" fill="#d1fae5" text-anchor="middle">{esc(line)}</text>'
        )
        y += 39
    body = (
        '<rect x="0" y="0" width="610" height="270" rx="9" fill="#334155" stroke="#0f172a" stroke-width="3"/>'
        '<rect x="68" y="38" width="502" height="194" rx="8" fill="#0f5132" stroke="#051f14" stroke-width="4"/>'
        + "".join(line_svg)
        + text(306, 254, "20x4 I2C LCD backpack, progress = chopCount / 100", 14, "#ffffff", 700, "middle")
        + text(26, 48, "GND", 12, "#ffffff", 700)
        + text(26, 84, "VCC", 12, "#ffffff", 700)
        + text(26, 120, "SDA", 12, "#ffffff", 700)
        + text(26, 156, "SCL", 12, "#ffffff", 700)
    )
    return custom_part(
        "i2c_lcd",
        "20x4 I2C character LCD",
        "LCD",
        610,
        270,
        body,
        [
            Connector("gnd", "LCD GND", 18, 44),
            Connector("vcc", "LCD VCC 5V or confirmed 3.3V", 18, 80),
            Connector("sda", "LCD SDA", 18, 116),
            Connector("scl", "LCD SCL", 18, 152),
        ],
    )


def make_i2c_shifter_part() -> Part:
    body = (
        '<rect x="0" y="0" width="280" height="216" rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
        + text(140, 28, "4-channel I2C level shifter", 18, "#1e3a8a", 700, "middle")
        + text(68, 58, "LV 3.3V", 13, WIRE["v3"], 700, "middle")
        + text(68, 92, "LV1 SDA", 13, WIRE["sda"], 700, "middle")
        + text(68, 126, "LV2 SCL", 13, WIRE["scl"], 700, "middle")
        + text(68, 180, "GND", 13, WIRE["gnd"], 700, "middle")
        + text(212, 58, "HV 5V", 13, WIRE["v5"], 700, "middle")
        + text(212, 92, "HV1 SDA", 13, WIRE["sda"], 700, "middle")
        + text(212, 126, "HV2 SCL", 13, WIRE["scl"], 700, "middle")
        + text(212, 180, "GND", 13, WIRE["gnd"], 700, "middle")
        + text(140, 204, "LV1/HV1 and LV2/HV2 are matching channels", 12, "#1f2933", 600, "middle")
    )
    return custom_part(
        "i2c_level_shifter",
        "Optional bidirectional I2C level shifter",
        "I2C LVL",
        280,
        216,
        body,
        [
            Connector("lv", "LV 3.3V", 18, 52),
            Connector("lv_sda", "LV1 SDA from ESP32 SDA/GPIO7", 18, 86),
            Connector("lv_scl", "LV2 SCL from ESP32 SCL/GPIO8", 18, 120),
            Connector("gnd_l", "GND", 18, 174),
            Connector("hv", "HV 5V", 262, 52),
            Connector("hv_sda", "HV1 SDA to LCD", 262, 86),
            Connector("hv_scl", "HV2 SCL to LCD", 262, 120),
            Connector("gnd_h", "GND", 262, 174),
        ],
    )


def make_cutting_board_part() -> Part:
    body = (
        '<rect x="0" y="0" width="720" height="500" rx="14" fill="#e8d7b0" stroke="#8b5a2b" stroke-width="4"/>'
        '<rect x="55" y="54" width="610" height="354" rx="12" fill="#f2dfb7" stroke="#b7791f" stroke-width="3"/>'
        '<rect x="126" y="112" width="310" height="34" rx="11" transform="rotate(-22 126 112)" fill="#cbd5e1" stroke="#475569" stroke-width="2"/>'
        '<rect x="384" y="4" width="64" height="26" rx="8" transform="rotate(-22 384 4)" fill="#111827" stroke="#020617" stroke-width="2"/>'
        '<path d="M121 118 L433 0 L456 19 L145 139 Z" fill="#e5e7eb" stroke="#64748b" stroke-width="2" opacity="0.65"/>'
        '<circle cx="360" cy="390" r="70" fill="#fef3c7" stroke="#b45309" stroke-width="4" stroke-dasharray="7 5"/>'
        '<circle cx="360" cy="390" r="27" fill="#fde68a" stroke="#b45309" stroke-width="2"/>'
        '<rect x="72" y="435" width="70" height="26" rx="12" fill="#111827"/>'
        '<rect x="578" y="435" width="70" height="26" rx="12" fill="#111827"/>'
        + text(360, 38, "CUTTING BOARD PROP", 24, "#5b3416", 800, "middle")
        + text(360, 432, "piezo mechanically coupled underneath, protected from direct strikes", 15, "#5b3416", 700, "middle")
        + text(360, 480, "Damped rubber feet reduce table vibration", 14, "#1f2933", 700, "middle")
    )
    return custom_part("cutting_board_layout", "Cutting board physical layout", "BOARD", 720, 500, body)


def make_raw_piezo_alt_part() -> Part:
    body = "".join(
        [
            '<rect x="0" y="0" width="560" height="258" rx="8" fill="#fff7ed" stroke="#ea580c" stroke-width="2" stroke-dasharray="8 6"/>',
            text(18, 29, "Raw piezo disc alternative", 20, "#9a3412", 700),
            text(18, 55, "Use instead of the module above, not at the same time.", 13, "#1f2933", 600),
            '<circle cx="108" cy="146" r="48" fill="#fef3c7" stroke="#b45309" stroke-width="3"/>',
            '<circle cx="108" cy="146" r="19" fill="#fde68a" stroke="#b45309" stroke-width="2"/>',
            '<line x1="156" y1="130" x2="228" y2="130" stroke="#111827" stroke-width="3"/>',
            '<rect x="228" y="117" width="92" height="26" rx="8" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>',
            '<line x1="320" y1="130" x2="420" y2="130" stroke="#111827" stroke-width="3"/>',
            '<line x1="156" y1="162" x2="420" y2="162" stroke="#111827" stroke-width="3"/>',
            '<rect x="205" y="150" width="42" height="23" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>',
            '<line x1="348" y1="130" x2="348" y2="88" stroke="#111827" stroke-width="3"/>',
            '<path d="M334 97 L362 97 L348 77 Z" fill="#bfdbfe" stroke="#1e3a8a" stroke-width="2"/>',
            '<line x1="334" y1="76" x2="362" y2="76" stroke="#1e3a8a" stroke-width="3"/>',
            text(274, 111, "10k-100k", 12, "#1f2933", 700, "middle"),
            text(226, 192, "1M bleed/reference", 12, "#1f2933", 700, "middle"),
            text(384, 83, "Schottky clamp to 3.3V", 12, "#1e3a8a", 700),
            text(430, 135, "to GPIO16 ADC", 13, WIRE["piezo_alt"], 700),
            text(430, 168, "to GND", 13, WIRE["gnd"], 700),
            text(18, 235, "Do not connect raw piezo directly without input protection.", 14, "#9a3412", 800),
        ]
    )
    return custom_part(
        "raw_piezo_alternative",
        "Raw piezo input protection alternative",
        "RAW",
        560,
        258,
        body,
    )


def build_parts() -> dict[str, Part]:
    return {
        "esp32": read_esp32_part(),
        "waypoint": make_waypoint_part(),
        "breadboard": make_breadboard_part(),
        "supply": make_supply_part(),
        "v5rail": make_rail_part("local_5v_aux_rail", "5V_AUX rail", WIRE["v5"], "5V_AUX from master power: LCD/backlight and level-shifter HV only"),
        "v3rail": make_rail_part("esp32_3v3_sensor_rail", "ESP32 3.3V rail", WIRE["v3"], "3.3V rail: piezo module VCC and level-shifter LV"),
        "gndrail": make_rail_part("common_ground_rail", "COMMON_GND rail", WIRE["gnd"], "COMMON_GND: ESP32 + LCD + piezo + 5V_AUX return"),
        "r_piezo": make_resistor_part("resistor_piezo_series", "1k-10k piezo AO series resistor", "1k-10k", ["#6b4f1d", "#111111", "#d71920", "#c49a23"]),
        "piezo": make_piezo_module_part(),
        "lcd": make_lcd_part(),
        "shifter": make_i2c_shifter_part(),
        "board": make_cutting_board_part(),
        "raw_alt": make_raw_piezo_alt_part(),
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

    def add_label(key: str, lines: list[str], x: float, y: float, width: int = 300, size: int = 14) -> Instance:
        parts_dynamic[key] = make_label_part(key, lines, width, size)
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
            'Chef Station "Chopping Module" wiring',
            "Waveshare ESP32-P4-ETH/POE-ETH, piezo impact sensing, local 20x4 I2C LCD feedback, Ethernet commands",
        ],
        28,
        18,
        950,
        18,
    )
    add_label(
        "pin_table",
        [
            "Pin assignment summary",
            "GPIO16 / ADC1_CH0: Piezo AO through 1k-10k",
            "SDA/GPIO7: I2C SDA to shifter LV1",
            "SCL/GPIO8: I2C SCL to shifter LV2",
            "Ethernet UDP 42100: START_GAME / RESET_GAME / score",
        ],
        28,
        108,
        520,
        13,
    )
    add_label(
        "power_callout",
        [
            "Power and common ground",
            "ESP32 is powered/networked by PoE from LS108GP.",
            "PoE powers the controller only.",
            "5V_AUX is for LCD/backlight and shifter HV.",
            "Do not feed +5V into ESP32 3V3.",
            "COMMON_GND is required for shared signals.",
        ],
        28,
        1048,
        470,
        13,
    )
    add_label(
        "piezo_callout",
        [
            "Piezo protection and thresholding",
            "Use AO analog output for scoring.",
            "Power piezo module from 3.3V so AO is ESP32-safe.",
            "AO runs through 1k-10k before GPIO16 / ADC1_CH0.",
            "Piezo detects impacts, not static pressure.",
            "Tune threshold only after mounted in final board.",
        ],
        1340,
        1048,
        560,
        13,
    )
    add_label(
        "debounce_callout",
        [
            "Chop debounce",
            "Start around 100-150 ms refractory period.",
            "If fast chopping is required, test 60-100 ms.",
            "Reject ringing so one chop counts once.",
            "Track max hit strength for debugging.",
        ],
        1950,
        1048,
        430,
        13,
    )
    add_label(
        "lcd_callout",
        [
            "LCD I2C notes",
            "Common addresses: 0x27 or 0x3F.",
            "If powered at +5V, many backpacks pull SDA/SCL to +5V.",
            "ESP32 GPIO is not 5V tolerant.",
            "Use the level shifter shown unless the LCD works at 3.3V.",
            "Adjust contrast pot if characters are invisible.",
        ],
        1460,
        382,
        610,
        13,
    )
    add_label(
        "network_callout",
        [
            "No hardware sync terminals",
            "Master sends START_GAME / RESET_GAME",
            "and FORCE_END / REQUEST_SCORE over Ethernet.",
            "Use the RJ45/PoE cable for command and score traffic.",
            "No START_IN, RESET_IN, or DONE_OUT wires are required.",
            "The LCD gives local feedback even if",
            "the monitor is not visible.",
        ],
        2130,
        96,
        440,
        12,
    )
    add_label(
        "firmware_callout",
        [
            "Firmware behavior",
            "IDLE: LCD shows READY TO CHOP and empty bar.",
            "ACTIVE: count valid impacts, update LCD immediately.",
            "COMPLETE: show elapsed time and send score JSON.",
            'Ethernet complete event: {"station":"chef","module":"chop","event":"complete","chops":100,"seconds":18.42}',
            "Primary score is seconds from master START to 100th valid chop.",
        ],
        525,
        1048,
        770,
        13,
    )

    add("esp", "esp32", "Waveshare ESP32-P4-ETH / ESP32-P4-POE-ETH", 94, 402)
    add("supply", "supply", "5V_AUX input from master power rails", 1005, 105, z=60)
    add("v5rail", "v5rail", "5V_AUX local accessory rail", 420, 176, z=60)
    add("v3rail", "v3rail", "ESP32 3.3V sensor rail", 420, 270, z=60)
    add("gndrail", "gndrail", "COMMON_GND local reference rail", 420, 965, z=60)
    add("r_piezo", "r_piezo", "R1 piezo AO 1k-10k series resistor", 860, 590, {"Resistance": "1k-10k"}, z=60)
    add("shifter", "shifter", "Optional bidirectional I2C level shifter", 1010, 420, z=60)
    add("lcd", "lcd", "20x4 I2C LCD above cutting board", 1505, 92, z=8)
    add("piezo", "piezo", "Piezo knock/vibration sensor module", 1422, 700, z=9)
    add("board", "board", "Cutting board physical layout with protected piezo", 1620, 520, z=4)
    add("raw_alt", "raw_alt", "Raw piezo disc alternative protection circuit", 760, 1230, z=8)

    # Power rails and grounds.
    manhattan_wire("supply", "vcc", "v5rail", "tap11", WIRE["v5"], "5V_AUX input to local 5V_AUX rail", 11, "vhv", 150)
    manhattan_wire("supply", "gnd", "gndrail", "tap11", WIRE["gnd"], "5V_AUX return to COMMON_GND rail", 11, "hvh", 1185)
    manhattan_wire("esp", "connector0", "v3rail", "tap0", WIRE["v3"], "ESP32 3V3 to 3.3V rail", 9, "hvh", 285)
    manhattan_wire("esp", "connector1", "gndrail", "tap0", WIRE["gnd"], "ESP32 GND reference to COMMON_GND rail", 10, "hvh", 300)

    # Piezo module power and analog path.
    manhattan_wire("v3rail", "tap16", "piezo", "vcc", WIRE["v3"], "3.3V rail to piezo module VCC", 9, "hvh", 1326)
    manhattan_wire("gndrail", "tap16", "piezo", "gnd", WIRE["gnd"], "Piezo module GND to COMMON_GND rail", 9, "hvh", 1350)
    manhattan_wire("piezo", "ao", "r_piezo", "connector1", WIRE["piezo"], "Piezo AO to R1 series resistor", 9, "vhv", 650)
    manhattan_wire("r_piezo", "connector0", "esp", "connector18", WIRE["piezo"], "R1 to GPIO16 / ADC1_CH0", 9, "vhv", 560)

    # LCD and optional I2C level shifter. The shifter is wired because LCD VCC is shown on +5V.
    manhattan_wire("v5rail", "tap15", "lcd", "vcc", WIRE["v5"], "LCD VCC to 5V_AUX rail", 10, "hvh", 1410)
    manhattan_wire("gndrail", "tap15", "lcd", "gnd", WIRE["gnd"], "LCD GND to COMMON_GND rail", 10, "hvh", 1392)
    manhattan_wire("v3rail", "tap10", "shifter", "lv", WIRE["v3"], "3.3V rail to shifter LV", 8, "hvh", 960)
    manhattan_wire("v5rail", "tap12", "shifter", "hv", WIRE["v5"], "5V_AUX rail to shifter HV", 8, "hvh", 1110)
    manhattan_wire("gndrail", "tap10", "shifter", "gnd_l", WIRE["gnd"], "COMMON_GND to shifter LV GND", 8, "hvh", 1000)
    manhattan_wire("gndrail", "tap12", "shifter", "gnd_h", WIRE["gnd"], "COMMON_GND to shifter HV GND", 8, "hvh", 1120)
    manhattan_wire("esp", "connector10", "shifter", "lv_sda", WIRE["sda"], "SDA/GPIO7 to shifter LV1", 9, "hvh", 520)
    manhattan_wire("esp", "connector13", "shifter", "lv_scl", WIRE["scl"], "SCL/GPIO8 to shifter LV2", 9, "hvh", 500)
    manhattan_wire("shifter", "hv_sda", "lcd", "sda", WIRE["sda"], "Shifter HV1 to LCD SDA", 9, "hvh", 1418)
    manhattan_wire("shifter", "hv_scl", "lcd", "scl", WIRE["scl"], "Shifter HV2 to LCD SCL", 9, "hvh", 1442)

    add("breadboard", "breadboard", "Manhattan breadboard and rails area", 315, 108, z=100)

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
        zf.writestr("chef_station_chopping_module_editable.fz", fz)
        for part in all_parts.values():
            zf.writestr(part.fzp_name, part.fzp)
            for name, text_value in part.svg_entries.items():
                zf.writestr(name, text_value)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Chopping Module Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO16 / ADC1_CH0 | Piezo AO analog input through 1k-10k series resistor |
| SDA / GPIO7 | I2C SDA to LCD through level shifter LV1/HV1 if LCD is powered at 5V |
| SCL / GPIO8 | I2C SCL to LCD through level shifter LV2/HV2 if LCD is powered at 5V |
| Ethernet UDP 42100 | START_GAME, FORCE_END, REQUEST_SCORE, RESET_GAME, and score JSON |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power LCD backlights or other accessories from the ESP32 PoE board.
- ESP32 `GND` connects to the `COMMON_GND` rail wherever LCD or piezo signals cross to externally powered accessories.
- `5V_AUX` positive from the master power distribution connects to the local `5V_AUX` rail for the LCD/backlight and optional I2C level shifter HV side.
- `5V_AUX` ground/return connects to `COMMON_GND`.
- Do not feed +5V into the ESP32 `3V3` pin.
- Piezo module `VCC` connects to ESP32 3.3V, not +5V.
- Piezo module `GND` connects to `COMMON_GND`.
- Piezo module `AO` connects through a 1k-10k series resistor to GPIO16 / ADC1_CH0.
- Piezo module `DO` is left disconnected unless used as an optional debug input.
- Use `AO` analog output for scoring. Do not use `DO` as the main chop input.
- LCD `GND` connects to `COMMON_GND`.
- LCD `VCC` connects to `5V_AUX`, or to 3.3V only if the LCD/backpack works reliably at 3.3V.
- ESP32 SDA / GPIO7 connects to level shifter `LV1`; matching `HV1` connects to LCD `SDA`.
- ESP32 SCL / GPIO8 connects to level shifter `LV2`; matching `HV2` connects to LCD `SCL`.
- If the LCD backpack is powered at +5V, use the bidirectional I2C level shifter shown.
- Level shifter LV connects to ESP32 3.3V, HV connects to `5V_AUX`, and GND connects to `COMMON_GND`.
- Master game commands arrive over Ethernet; do not wire separate START_SYNC, RESET_SYNC, or DONE_OUT terminals.

## Piezo And Cutting Board Notes

- Piezo detects impacts, not static pressure.
- Mechanically couple the piezo disc or module to the underside of the cutting board.
- Protect the piezo from direct knife strikes.
- Put the cutting board on damped/rubber feet to reduce table vibration.
- Tune the analog threshold only after the piezo is mounted in the final board.
- Start with debounce/refractory period around 100-150 ms.
- If fast chopping is required, allow shorter debounce such as 60-100 ms after testing.
- Use threshold above vibration/noise baseline.
- Do not count multiple ringing peaks from one chop.
- Use forgiving thresholds because public users will chop inconsistently.

## Raw Piezo Disc Alternative

- Use the raw piezo circuit instead of the piezo module, not in parallel with it.
- One piezo lead goes to GPIO16 / ADC through a 10k-100k series resistor.
- The other piezo lead goes to GND.
- Add a 1M resistor across the piezo leads as bleed/reference.
- Add an optional 3.3V clamp diode or Schottky protection to protect the ESP32 ADC.
- Do not connect a raw piezo directly to the ESP32 ADC without input protection.

## LCD Behavior Notes

- LCD line 1: `CHOP FASTER`
- LCD line 2: `KEEP GOING`
- LCD line 3: progress bar fills as `chopCount / 100`
- LCD line 4: `Chops: 037/100` or `Time: 12.4s`
- Common I2C LCD addresses are `0x27` and `0x3F`.
- Adjust the LCD contrast potentiometer if characters are invisible.
- Mount the LCD above or behind the board so players do not need to look straight down.

## Firmware Behavior Notes

- IDLE: LCD may show `READY TO CHOP` with an empty progress bar.
- START: on Ethernet `START_GAME phase=main`, set `chopCount = 0` and `startTimeMs = millis()`.
- ACTIVE: sample GPIO16 frequently and count one valid chop when the analog value exceeds threshold.
- ACTIVE: update the LCD progress bar immediately after every valid chop.
- ACTIVE: reject ringing using the debounce/refractory period.
- COMPLETE: when `chopCount` reaches 100, set `finishTimeMs = millis()`.
- COMPLETE: compute `elapsedSeconds = (finishTimeMs - startTimeMs) / 1000.0`.
- COMPLETE: show completion time locally on the LCD and send score JSON.
- RESET: on Ethernet `RESET_GAME`, clear count and return to IDLE.
- Ethernet complete event: `{"station":"chef","module":"chop","event":"complete","chops":100,"seconds":18.42}`
- If the game ends before 100 chops, report partial score: `{"station":"chef","module":"chop","event":"incomplete","chops":72,"seconds":30.00}`

## Scoring

- Primary score is elapsed time from Ethernet `START_GAME` to the 100th valid chop.
- Lower time is better.
- The master clock may decide final ranking later.
- The chopping module measures local elapsed time and chop count.
- The monitor or central controller can add polish, but core gameplay should work locally.

## Assumptions And Part Notes

- Controller assumption: Waveshare ESP32-P4-ETH / ESP32-P4-POE-ETH module powered from the LS108GP over Ethernet.
- ESP32-P4 pinout basis: Waveshare exposes SDA/GPIO7 and SCL/GPIO8 on the 40-pin header; ESP32-P4 ADC pins are different from classic ESP32 DevKit GPIO34-style ADC pins.
- ESP32 part: custom editable ESP32-P4 helper part with the module's functional GPIO labels; verify exact board pinout before final harness fabrication.
- Accessory rail assumption: LCD/backlight power comes from `5V_AUX`, not from the ESP32 PoE board.
- Piezo module, LCD, level shifter, rails, physical board layout, raw piezo alternative, and callouts are custom editable Fritzing helper parts for readability.
- LCD is shown powered from +5V, so the diagram includes the optional level shifter in the active I2C path.
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
