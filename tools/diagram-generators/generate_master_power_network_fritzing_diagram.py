from __future__ import annotations

import html
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "master-power-network"
FZZ_PATH = OUT_DIR / "chef_station_master_power_network_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_master_power_network_layout.png"
CHECKLIST_PATH = OUT_DIR / "master_power_network_tables_and_checklist.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


WIRE = {
    "ac": "#5b6472",
    "dc_misc": "#64748b",
    "ethernet": "#1e88e5",
    "v12": "#d71920",
    "gnd": "#111111",
    "v5": "#f59e0b",
    "gpio": "#178f46",
    "note": "#b45309",
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
    width: float = 8


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


def text_lines(
    x: float,
    y: float,
    lines: list[str],
    size: int = 14,
    fill: str = "#1f2933",
    first_weight: int = 800,
    weight: int = 560,
    anchor: str = "start",
    gap: int = 6,
) -> str:
    out = []
    step = size + gap
    for i, line in enumerate(lines):
        out.append(text(x, y + i * step, line, size, fill, first_weight if i == 0 else weight, anchor))
    return "".join(out)


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
    module_id = f"chef_master_power_{key}"

    def svg_for(layer: str) -> str:
        connector_svg = []
        for connector in connectors:
            connector_svg.append(
                f'<circle id="{connector.cid}pin" cx="{connector.x}" cy="{connector.y}" r="5.2" '
                f'fill="{connector.color}" stroke="#111111" stroke-width="1.35">'
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
  <tags><tag>chef station</tag><tag>master power</tag><tag>poe</tag><tag>network</tag></tags>
  <properties>
    <property name="family">Chef Station Master Power And Network Layout</property>
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


def make_label_part(
    key: str,
    lines: list[str],
    width: int = 420,
    size: int = 14,
    fill: str = "#fffefa",
    stroke: str = "#d0d7de",
    heading: str = "#1f2933",
    body_fill: str = "#1f2933",
) -> Part:
    height = max(42, 22 + len(lines) * (size + 6))
    body = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="6" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.35"/>'
    ]
    y = 22
    for index, line in enumerate(lines):
        body.append(
            text(
                12,
                y,
                line,
                size,
                heading if index == 0 else body_fill,
                820 if index == 0 else 560,
            )
        )
        y += size + 6
    return custom_part(key, lines[0], "TXT", width, height, "".join(body))


def make_waypoint_part() -> Part:
    body = '<circle id="pinmark" cx="3" cy="3" r="1.8" fill="#ffffff" stroke="#64748b" stroke-width="0.8"/>'
    return custom_part("waypoint", "Wire waypoint", "WP", 6, 6, body, [Connector("pin", "waypoint", 3, 3)])


def make_ac_strip_part() -> Part:
    y_values = {
        "ac_switch": 116,
        "ac_epson": 220,
        "ac_adapter_a": 478,
        "ac_adapter_b": 592,
        "ac_adapter_c": 706,
        "ac_adapter_d": 820,
    }
    connectors = [
        Connector(cid, name, 360, y, WIRE["ac"])
        for cid, name, y in [
            ("ac_switch", "AC to LS108GP adapter", y_values["ac_switch"]),
            ("ac_epson", "AC to Epson printer PSU", y_values["ac_epson"]),
            ("ac_adapter_a", "AC to 12V adapter A", y_values["ac_adapter_a"]),
            ("ac_adapter_b", "AC to 12V adapter B", y_values["ac_adapter_b"]),
            ("ac_adapter_c", "AC to 12V adapter C", y_values["ac_adapter_c"]),
            ("ac_adapter_d", "AC to 12V adapter D", y_values["ac_adapter_d"]),
        ]
    ]
    outlets = []
    for label, y in [
        ("PoE switch PSU", y_values["ac_switch"]),
        ("Epson PSU", y_values["ac_epson"]),
        ("12V Adapter A", y_values["ac_adapter_a"]),
        ("12V Adapter B", y_values["ac_adapter_b"]),
        ("12V Adapter C", y_values["ac_adapter_c"]),
        ("12V Adapter D", y_values["ac_adapter_d"]),
    ]:
        outlets.append(
            f'<rect x="38" y="{y-30}" width="240" height="58" rx="8" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.6"/>'
            f'<circle cx="78" cy="{y}" r="7" fill="#e2e8f0" stroke="#64748b"/>'
            f'<circle cx="112" cy="{y}" r="7" fill="#e2e8f0" stroke="#64748b"/>'
            f'<text x="144" y="{y+5}" font-family="Segoe UI, Arial, sans-serif" font-size="13" '
            f'font-weight="760" fill="#334155">{esc(label)}</text>'
        )
    body = (
        '<rect x="0" y="0" width="380" height="880" rx="12" fill="#eef2f7" stroke="#475569" stroke-width="2.2"/>'
        + text(26, 36, "AC POWER ENTRY", 24, "#0f172a", 850)
        + text(26, 66, "Power strip / IEC inlet", 15, "#334155", 680)
        + text(26, 94, "120 VAC: keep enclosed", 14, "#7c2d12", 820)
        + "".join(outlets)
        + text(26, 842, "Use strain relief. Do not expose AC terminals.", 13, "#7c2d12", 820)
    )
    return custom_part("ac_power_strip", "AC power entry / power strip", "AC", 380, 880, body, connectors)


def make_supply_part(
    key: str,
    title: str,
    subtitle: str,
    output_label: str,
    out_color: str = WIRE["dc_misc"],
    height: int = 118,
) -> Part:
    body = (
        f'<rect x="0" y="0" width="360" height="{height}" rx="9" fill="#f8fafc" stroke="#64748b" stroke-width="2"/>'
        + text(18, 30, title, 18, "#1f2933", 830)
        + text(18, 56, subtitle, 13, "#334155", 620)
        + text(18, 84, output_label, 13, out_color, 800)
        + text(336, 64, "DC OUT", 12, out_color, 820, "end")
    )
    return custom_part(
        key,
        title,
        "PSU",
        360,
        height,
        body,
        [
            Connector("ac_in", "AC input", 0, 60, WIRE["ac"]),
            Connector("out", output_label, 360, 60, out_color),
        ],
    )


def make_12v_adapter_part(key: str, title: str, branch: str) -> Part:
    body = (
        '<rect x="0" y="0" width="360" height="132" rx="10" fill="#fff7ed" stroke="#f97316" stroke-width="2"/>'
        + text(18, 30, title, 18, "#1f2933", 830)
        + text(18, 56, "Adjustable wall adapter", 13, "#334155", 620)
        + text(18, 82, "SET AND LOCK/TAPE AT 12V", 14, WIRE["v12"], 850)
        + text(18, 108, branch, 13, "#334155", 700)
        + text(332, 48, "+12V", 13, WIRE["v12"], 850, "end")
        + text(332, 98, "GND", 13, WIRE["gnd"], 850, "end")
    )
    return custom_part(
        key,
        title,
        "12V",
        360,
        132,
        body,
        [
            Connector("ac_in", "AC input", 0, 66, WIRE["ac"]),
            Connector("pos", "+12V output", 360, 44, WIRE["v12"]),
            Connector("gnd", "DC negative", 360, 96, WIRE["gnd"]),
        ],
    )


def make_buck_part(key: str, title: str, output_label: str, optional: bool = False) -> Part:
    note = "Optional auxiliary 5V rail" if optional else "Adjust to 5.0V-5.1V first"
    body = (
        '<rect x="0" y="0" width="320" height="148" rx="10" fill="#fffbeb" stroke="#d97706" stroke-width="2"/>'
        + text(160, 28, title, 18, "#1f2933", 850, "middle")
        + text(160, 54, "12V IN -> regulated 5V OUT", 13, "#334155", 700, "middle")
        + text(160, 80, output_label, 16, WIRE["v5"], 850, "middle")
        + text(160, 114, note, 12, "#7c2d12", 780, "middle")
        + text(20, 44, "IN+", 12, WIRE["v12"], 850)
        + text(20, 101, "IN-", 12, WIRE["gnd"], 850)
        + text(274, 44, "OUT+", 12, WIRE["v5"], 850, "end")
        + text(274, 101, "OUT-", 12, WIRE["gnd"], 850, "end")
    )
    return custom_part(
        key,
        title,
        "BUCK",
        320,
        148,
        body,
        [
            Connector("in_pos", "12V input positive", 0, 44, WIRE["v12"]),
            Connector("in_gnd", "12V input negative", 0, 100, WIRE["gnd"]),
            Connector("out_pos", f"{output_label} positive", 320, 44, WIRE["v5"]),
            Connector("out_gnd", f"{output_label} ground", 320, 100, WIRE["gnd"]),
        ],
    )


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 16, width: int = 1660) -> Part:
    spacing = (width - 76) / max(1, tap_count - 1)
    connectors = [Connector(f"tap{i}", f"{title} tap {i}", 38 + i * spacing, 28, "#ffffff") for i in range(tap_count)]
    circles = "".join(
        f'<circle cx="{38+i*spacing}" cy="28" r="4.1" fill="#ffffff" stroke="{color}" stroke-width="1.8"/>'
        for i in range(tap_count)
    )
    body = (
        f'<rect x="0" y="0" width="{width}" height="78" rx="8" fill="#ffffff" stroke="#94a3b8" stroke-width="1.4"/>'
        f'<line x1="18" y1="28" x2="{width-18}" y2="28" stroke="{color}" stroke-width="9" stroke-linecap="round"/>'
        f'{circles}'
        f'{text(14, 63, note, 14, "#1f2933", 760)}'
    )
    return custom_part(key, title, "RAIL", width, 78, body, connectors, buses={key: [f"tap{i}" for i in range(tap_count)]})


def make_poe_switch_part() -> Part:
    connectors = [
        Connector("dc_in", "53.5V DC input from TP-Link adapter", 0, 252, WIRE["dc_misc"]),
        Connector("p1", "Port 1 PoE to Simon ESP32", 560, 72, WIRE["ethernet"]),
        Connector("p2", "Port 2 PoE to Chopping ESP32", 560, 108, WIRE["ethernet"]),
        Connector("p3", "Port 3 PoE to Pan Motion ESP32", 560, 144, WIRE["ethernet"]),
        Connector("p4", "Port 4 PoE to Pot Temperature ESP32", 560, 180, WIRE["ethernet"]),
        Connector("p5", "Port 5 PoE to Garnish ESP32", 560, 216, WIRE["ethernet"]),
        Connector("p6", "Port 6 PoE to Master Controller ESP32", 160, 320, WIRE["ethernet"]),
        Connector("p7", "Port 7 Ethernet to Epson printer", 254, 320, WIRE["ethernet"]),
        Connector("p8", "Port 8 optional router/DHCP or spare", 426, 0, WIRE["ethernet"]),
    ]
    port_svg = []
    for i in range(8):
        x = 70 + i * 55
        port_svg.append(f'<rect x="{x}" y="112" width="38" height="30" rx="4" fill="#e2e8f0" stroke="#64748b"/>')
        port_svg.append(text(x + 19, 134, str(i + 1), 12, "#334155", 850, "middle"))
    body = (
        '<rect x="0" y="0" width="560" height="320" rx="14" fill="#f8fafc" stroke="#334155" stroke-width="2.4"/>'
        + text(280, 36, "TP-Link LiteWave LS108GP", 24, "#0f172a", 880, "middle")
        + text(280, 66, "8-port PoE switch", 18, "#1f2933", 820, "middle")
        + "".join(port_svg)
        + text(280, 178, "PoE budget: 62W total, 30W max per PoE port", 15, "#7c2d12", 850, "middle")
        + text(280, 206, "PoE powers ESP32 controller boards only", 15, "#1f2933", 790, "middle")
        + text(280, 238, "Powered by its own 53.5V DC adapter", 14, "#334155", 720, "middle")
        + text(280, 278, "Unmanaged switch: add router/DHCP or static IP plan", 13, "#334155", 720, "middle")
    )
    return custom_part("ls108gp_poe_switch", "TP-Link LiteWave LS108GP PoE switch", "SW", 560, 320, body, connectors)


def make_router_part() -> Part:
    body = (
        '<rect x="0" y="0" width="380" height="138" rx="10" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
        + text(190, 32, "Optional router / DHCP", 19, "#1e3a8a", 850, "middle")
        + text(190, 60, "Not required with static IPs", 13, "#1f2933", 700, "middle")
        + text(190, 86, "Do not rely on internet access", 13, "#7c2d12", 800, "middle")
        + text(190, 116, "Ethernet to switch port 8", 12, WIRE["ethernet"], 760, "middle")
    )
    return custom_part(
        "optional_router_dhcp",
        "Optional router / DHCP source",
        "DHCP",
        380,
        138,
        body,
        [Connector("eth", "Ethernet uplink to switch", 190, 138, WIRE["ethernet"])],
    )


def make_printer_part() -> Part:
    body = (
        '<rect x="0" y="0" width="430" height="176" rx="12" fill="#f8fafc" stroke="#475569" stroke-width="2.2"/>'
        + '<rect x="254" y="46" width="128" height="66" rx="8" fill="#e2e8f0" stroke="#94a3b8"/>'
        + '<path d="M274 100 L362 100 L350 144 L286 144 Z" fill="#ffffff" stroke="#94a3b8"/>'
        + text(184, 34, "Epson TM-T20IV / TM-T20V-family", 18, "#0f172a", 850, "middle")
        + text(184, 64, "Receipt printer", 15, "#1f2933", 760, "middle")
        + text(184, 94, "Ethernet to switch; addressed by IP", 13, "#1f2933", 690, "middle")
        + text(184, 124, "Uses Epson manufacturer PSU", 13, "#7c2d12", 830, "middle")
        + text(18, 58, "ETH", 12, WIRE["ethernet"], 850)
        + text(18, 126, "PWR", 12, WIRE["dc_misc"], 850)
        + text(350, 164, "Not powered by PoE", 12, "#7c2d12", 850, "middle")
    )
    return custom_part(
        "epson_receipt_printer",
        "Epson TM-T20IV / TM-T20V-family receipt printer",
        "PRN",
        430,
        176,
        body,
        [
            Connector("eth", "Ethernet to switch", 0, 55, WIRE["ethernet"]),
            Connector("pwr", "Epson PSU input", 0, 123, WIRE["dc_misc"]),
        ],
    )


def make_module_part(key: str, title: str) -> Part:
    body = (
        '<rect x="0" y="0" width="430" height="170" rx="12" fill="#f8fafc" stroke="#334155" stroke-width="2.2"/>'
        + '<rect x="54" y="28" width="190" height="92" rx="9" fill="#111827" stroke="#475569" stroke-width="2"/>'
        + '<rect x="96" y="122" width="106" height="28" rx="5" fill="#e2e8f0" stroke="#64748b"/>'
        + text(270, 30, title, 17, "#0f172a", 860)
        + text(270, 58, "Waveshare ESP32-P4-POE-ETH / NH", 13, "#1f2933", 700)
        + text(270, 84, "Ethernet carries network + PoE", 12, WIRE["ethernet"], 760)
        + text(270, 108, "PoE powers ESP32 controller only", 12, "#7c2d12", 830)
        + text(270, 132, "No LED/servo/audio load power from board", 12, "#7c2d12", 830)
        + text(62, 82, "ESP32", 18, "#ffffff", 850)
        + text(106, 142, "RJ45 + PoE", 11, "#334155", 850)
        + text(16, 56, "ETH", 12, WIRE["ethernet"], 850)
        + text(16, 142, "GND", 12, WIRE["gnd"], 850)
        + text(410, 103, "GPIO", 12, WIRE["gpio"], 850, "end")
    )
    return custom_part(
        key,
        title,
        "ESP32",
        430,
        170,
        body,
        [
            Connector("eth", "Ethernet + PoE input", 0, 52, WIRE["ethernet"]),
            Connector("gnd", "ESP32 GND reference to COMMON_GND", 0, 138, WIRE["gnd"]),
            Connector("gpio", "GPIO/data/control to accessory drivers", 430, 100, WIRE["gpio"]),
        ],
    )


def make_master_controller_part() -> Part:
    body = (
        '<rect x="0" y="0" width="430" height="190" rx="12" fill="#f8fafc" stroke="#334155" stroke-width="2.2"/>'
        + '<rect x="54" y="28" width="190" height="92" rx="9" fill="#111827" stroke="#475569" stroke-width="2"/>'
        + '<rect x="96" y="122" width="106" height="28" rx="5" fill="#e2e8f0" stroke="#64748b"/>'
        + text(270, 30, "Master Controller ESP32", 17, "#0f172a", 860)
        + text(270, 58, "Waveshare ESP32-P4-POE-ETH / NH", 13, "#1f2933", 700)
        + text(270, 84, "Ethernet carries network + PoE", 12, WIRE["ethernet"], 760)
        + text(270, 108, "GPIO5: Start Game button input", 12, WIRE["gpio"], 850)
        + text(270, 132, "Button uses INPUT_PULLUP", 12, "#7c2d12", 830)
        + text(270, 156, "Printer/modules use Ethernet, not GPIO", 12, "#1f2933", 760)
        + text(62, 82, "ESP32", 18, "#ffffff", 850)
        + text(106, 142, "RJ45 + PoE", 11, "#334155", 850)
        + text(16, 56, "ETH", 12, WIRE["ethernet"], 850)
        + text(16, 142, "GND", 12, WIRE["gnd"], 850)
        + text(410, 105, "GPIO5", 12, WIRE["gpio"], 850, "end")
        + text(410, 143, "GND", 12, WIRE["gnd"], 850, "end")
    )
    return custom_part(
        "master_controller_esp32_poe_node",
        "Master Controller ESP32 PoE board",
        "ESP32",
        430,
        190,
        body,
        [
            Connector("eth", "Ethernet + PoE input", 0, 52, WIRE["ethernet"]),
            Connector("gnd", "Master ESP32 GND reference to COMMON_GND", 0, 138, WIRE["gnd"]),
            Connector("gpio5", "GPIO5 Start Game button input", 430, 100, WIRE["gpio"]),
            Connector("gnd_btn", "GND pin for Start Game button", 430, 138, WIRE["gnd"]),
        ],
        buses={"gnd": ["gnd", "gnd_btn"]},
    )


def make_start_button_part() -> Part:
    body = (
        '<rect x="0" y="0" width="190" height="112" rx="9" fill="#ecfdf5" stroke="#047857" stroke-width="2"/>'
        + '<circle cx="150" cy="56" r="26" fill="#bbf7d0" stroke="#047857" stroke-width="3"/>'
        + '<circle cx="150" cy="56" r="14" fill="#22c55e" stroke="#166534" stroke-width="2"/>'
        + text(10, 25, "Start Game", 15, "#064e3b", 850)
        + text(10, 49, "Momentary NO", 11, "#1f2933", 700)
        + text(10, 72, "GPIO5 -> SIG", 11, WIRE["gpio"], 820)
        + text(10, 94, "GND -> GND", 11, WIRE["gnd"], 820)
        + text(178, 42, "SIG", 10, WIRE["gpio"], 850, "end")
        + text(178, 82, "GND", 10, WIRE["gnd"], 850, "end")
    )
    return custom_part(
        "master_start_game_button",
        "Master Controller Start Game button",
        "START",
        190,
        112,
        body,
        [
            Connector("sig", "Start button signal to GPIO5", 0, 38, WIRE["gpio"]),
            Connector("gnd", "Start button ground", 0, 78, WIRE["gnd"]),
        ],
    )


def make_accessory_block_part(key: str, title: str, lines: list[str]) -> Part:
    body_lines = text_lines(18, 54, lines, 11, "#1f2933", 720, 540, gap=4)
    body = (
        '<rect x="0" y="0" width="660" height="170" rx="10" fill="#ffffff" stroke="#94a3b8" stroke-width="1.8"/>'
        + text(330, 28, title, 17, "#0f172a", 850, "middle")
        + body_lines
        + text(18, 39, "CTRL", 10, WIRE["gpio"], 850)
        + text(18, 78, "12V_SHOW", 10, WIRE["v12"], 850)
        + text(18, 101, "5V_LED", 10, WIRE["v5"], 850)
        + text(18, 122, "5V_AUDIO_SERVO", 10, WIRE["v5"], 850)
        + text(18, 143, "5V_AUX", 10, WIRE["v5"], 850)
        + text(630, 150, "GND", 11, WIRE["gnd"], 850, "end")
    )
    return custom_part(
        key,
        title,
        "TERM",
        660,
        170,
        body,
        [
            Connector("ctrl", "GPIO/data/control from ESP32", 0, 36, WIRE["gpio"]),
            Connector("v12", "12V_SHOW input if module has 12V-rated loads", 0, 70, WIRE["v12"]),
            Connector("v5_led", "5V_LED input", 0, 96, WIRE["v5"]),
            Connector("v5_audio", "5V_AUDIO_SERVO input", 0, 120, WIRE["v5"]),
            Connector("v5_aux", "5V_AUX input", 0, 144, WIRE["v5"]),
            Connector("gnd", "Accessory load ground to COMMON_GND", 660, 146, WIRE["gnd"]),
        ],
    )


def build_parts() -> dict[str, Part]:
    modules = {
        "simon_esp": make_module_part("simon_esp32_poe_node", "Simon ESP32 PoE board"),
        "chop_esp": make_module_part("chopping_esp32_poe_node", "Chopping ESP32 PoE board"),
        "pan_esp": make_module_part("pan_motion_esp32_poe_node", "Pan Motion ESP32 PoE board"),
        "pot_esp": make_module_part("pot_temperature_esp32_poe_node", "Pot Temperature ESP32 PoE board"),
        "garnish_esp": make_module_part("garnish_placement_esp32_poe_node", "Garnish ESP32 PoE board"),
        "master_esp": make_master_controller_part(),
    }
    terminals = {
        "simon_term": make_accessory_block_part(
            "simon_local_accessory_terminal",
            "Simon local accessory terminal block",
            [
                "Button switches: GPIO/GND inputs.",
                "Button lamps: 5V_LED or 12V_SHOW by lamp rating.",
                "MOSFET sources return to COMMON_GND.",
                "Speaker/amp, if present: 5V_AUDIO_SERVO.",
            ],
        ),
        "chop_term": make_accessory_block_part(
            "chopping_local_accessory_terminal",
            "Chopping local accessory terminal block",
            [
                "Piezo can use ESP32 3.3V if suitable.",
                "I2C LCD backlight: 5V_AUX or 5V_LED.",
                "Use I2C level shifter for 5V I2C LCD.",
                "LCD/piezo grounds common with ESP32.",
            ],
        ),
        "pan_term": make_accessory_block_part(
            "pan_motion_local_accessory_terminal",
            "Pan Motion local accessory terminal block",
            [
                "Hall sensors: ESP32 3.3V logic.",
                "Cooktop LED: 5V_LED or 12V_SHOW by strip type.",
                "DFPlayer/audio: 5V_AUDIO_SERVO.",
                "ESP32 sends LED data and serial control only.",
            ],
        ),
        "pot_term": make_accessory_block_part(
            "pot_temperature_local_accessory_terminal",
            "Pot Temperature local accessory terminal block",
            [
                "Rotary encoder: ESP32 GPIO with INPUT_PULLUP.",
                "Cooktop LED: 5V_LED or 12V_SHOW by strip type.",
                "Temp ring/strip: 5V_LED.",
                "Common ground between ESP32 and LED rail.",
            ],
        ),
        "garnish_term": make_accessory_block_part(
            "garnish_local_accessory_terminal",
            "Garnish local accessory terminal block",
            [
                "Touch electrodes: ESP32 touch pins through 1k.",
                "RGB strip: 5V_LED.",
                "Servo: 5V_AUDIO_SERVO.",
                "DONE button: ESP32 GPIO/GND.",
            ],
        ),
    }
    return {
        "waypoint": make_waypoint_part(),
        "ac_strip": make_ac_strip_part(),
        "switch_psu": make_supply_part(
            "tplink_53v5_power_adapter",
            "LS108GP power adapter",
            "Manufacturer supply",
            "53.5V DC to switch only",
        ),
        "epson_psu": make_supply_part(
            "epson_manufacturer_power_supply",
            "Epson printer PSU",
            "Manufacturer supply",
            "Printer DC input only",
        ),
        "adapter_a": make_12v_adapter_part("adjustable_12v_adapter_a", "12V Adapter A", "12V_SHOW actual-load branch"),
        "adapter_b": make_12v_adapter_part("adjustable_12v_adapter_b", "12V Adapter B", "Feeds Buck #2 / 5V_LED"),
        "adapter_c": make_12v_adapter_part("adjustable_12v_adapter_c", "12V Adapter C", "Feeds Buck #3 / audio/servo"),
        "adapter_d": make_12v_adapter_part("adjustable_12v_adapter_d", "12V Adapter D", "Feeds Buck #1 / 5V_AUX"),
        "buck1": make_buck_part("buck_converter_1_aux", "Buck #1", "5V_AUX", optional=True),
        "buck2": make_buck_part("buck_converter_2_led", "Buck #2", "5V_LED"),
        "buck3": make_buck_part("buck_converter_3_audio_servo", "Buck #3", "5V_AUDIO_SERVO"),
        "switch": make_poe_switch_part(),
        "router": make_router_part(),
        "printer": make_printer_part(),
        "start_button": make_start_button_part(),
        "rail12": make_rail_part(
            "rail_12v_show_actual_loads",
            "12V_SHOW / 12V ACTUAL LOADS",
            WIRE["v12"],
            "12V_SHOW: only devices explicitly rated 12V. Do not connect to 5V devices.",
            tap_count=17,
        ),
        "rail5led": make_rail_part(
            "rail_5v_led",
            "5V_LED",
            WIRE["v5"],
            "5V_LED: WS2812/NeoPixel strips, cooktop coil LEDs, overhead LEDs, 5V Simon lamps.",
            tap_count=17,
        ),
        "rail5audio": make_rail_part(
            "rail_5v_audio_servo",
            "5V_AUDIO_SERVO",
            WIRE["v5"],
            "5V_AUDIO_SERVO: DFPlayer modules, small amps/speakers, servo timer, optional LCD backlights.",
            tap_count=17,
        ),
        "rail5aux": make_rail_part(
            "rail_5v_aux",
            "5V_AUX",
            WIRE["v5"],
            "5V_AUX: optional low-current peripherals, LCD backlights, status LEDs, small relay boards.",
            tap_count=17,
        ),
        "gndrail": make_rail_part(
            "rail_common_gnd",
            "COMMON_GND",
            WIRE["gnd"],
            "COMMON_GND terminal block: common only where GPIO/data/control signals cross power domains.",
            tap_count=22,
        ),
        **modules,
        **terminals,
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
    a = insts[wire.a]
    b = insts[wire.b]
    ax, ay = parts[a.part].pins[wire.ac]
    bx, by = parts[b.part].pins[wire.bc]
    x1, y1 = a.x + ax, a.y + ay
    x2, y2 = b.x + bx, b.y + by
    return f'''    <instance moduleIdRef="WireModuleID" modelIndex="{wire.idx}" path=":/resources/parts/core/wire.fzp">
      <title>{esc(wire.title)}</title>
      <views>
        <breadboardView layer="breadboardWire">
          <geometry z="4" x="{x1:.2f}" y="{y1:.2f}" x1="0" y1="0" x2="{x2-x1:.2f}" y2="{y2-y1:.2f}" wireFlags="64"/>
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
        width: int = 420,
        size: int = 14,
        fill: str = "#fffefa",
        stroke: str = "#d0d7de",
        heading: str = "#1f2933",
        body_fill: str = "#1f2933",
    ) -> Instance:
        parts_dynamic[key] = make_label_part(key, lines, width, size, fill, stroke, heading, body_fill)
        return add(key, key, lines[0], x, y, z=8)

    def add_waypoint(key: str, x: float, y: float) -> Instance:
        return add(key, "waypoint", key, x - 3, y - 3, z=4)

    def all_parts() -> dict[str, Part]:
        return {**parts, **parts_dynamic}

    def by_key() -> dict[str, Instance]:
        return {item.key: item for item in inst}

    def abs_pos(key: str, conn: str) -> tuple[float, float]:
        item = by_key()[key]
        px, py = all_parts()[item.part].pins[conn]
        return item.x + px, item.y + py

    def wire(a: str, ac: str, b: str, bc: str, color: str, title: str, width: float = 8) -> None:
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
        width: float = 8,
    ) -> None:
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

    global parts_dynamic
    parts_dynamic = {}

    add_label(
        "title",
        [
            "Chef Station Master Power And Network Layout",
            "Four adjustable adapters set to 12V feed 12V_SHOW and three local buck converters.",
        ],
        40,
        24,
        1370,
        20,
        "#f8fafc",
        "#94a3b8",
    )
    add_label(
        "legend",
        [
            "Wire color legend",
            "Blue: Ethernet / PoE network cables",
            "Red: thick 12V positive branches",
            "Black: thick DC ground / COMMON_GND",
            "Orange: 5V accessory rails from buck converters",
            "Green: GPIO / data / control signals only",
            "Gray: AC or manufacturer DC supply leads",
        ],
        1460,
        22,
        620,
        13,
        "#ffffff",
        "#cbd5e1",
    )

    add("ac", "ac_strip", "AC power entry / power strip", 40, 250)
    add("switch_psu", "switch_psu", "LS108GP manufacturer power adapter", 450, 250)
    add("epson_psu", "epson_psu", "Epson manufacturer printer PSU", 450, 390)
    add("adapter_a", "adapter_a", "Adjustable 12V adapter A", 450, 1040)
    add("adapter_d", "adapter_d", "Adjustable 12V adapter D", 450, 1125)
    add("adapter_b", "adapter_b", "Adjustable 12V adapter B", 450, 1245)
    add("adapter_c", "adapter_c", "Adjustable 12V adapter C", 450, 1390)

    add("switch", "switch", "TP-Link LiteWave LS108GP 8-port PoE switch", 850, 250)
    add("router", "router", "Optional router / DHCP source", 1040, 92)
    add("master_esp", "master_esp", "Master Controller ESP32 PoE board", 850, 640)
    add("start_button", "start_button", "Start Game button", 1288, 660)
    add("printer", "printer", "Epson receipt printer", 850, 845)

    add("buck1", "buck1", "Buck #1 optional 5V_AUX", 850, 1080)
    add("buck2", "buck2", "Buck #2 5V_LED", 850, 1260)
    add("buck3", "buck3", "Buck #3 5V_AUDIO_SERVO", 850, 1440)

    add("rail12", "rail12", "12V_SHOW / 12V ACTUAL LOADS terminal block", 1260, 1315)
    add("rail5led", "rail5led", "5V_LED terminal block", 1260, 1425)
    add("rail5audio", "rail5audio", "5V_AUDIO_SERVO terminal block", 1260, 1535)
    add("rail5aux", "rail5aux", "5V_AUX terminal block", 1260, 1645)
    add("gndrail", "gndrail", "COMMON_GND distribution terminal block", 1260, 1775)

    row_y = {
        "simon": 170,
        "chop": 380,
        "pan": 590,
        "pot": 800,
        "garnish": 1010,
    }
    for name, y in row_y.items():
        add(f"{name}_esp", f"{name}_esp", f"{name.title()} ESP32 PoE board", 1740, y)
        add(f"{name}_term", f"{name}_term", f"{name.title()} local accessory terminal block", 2215, y)

    add_label(
        "poe_budget",
        [
            "PoE budget table",
            "Simon ESP32 board: PoE",
            "Chop ESP32 board: PoE",
            "Pan ESP32 board: PoE",
            "Pot ESP32 board: PoE",
            "Garnish ESP32 board: PoE",
            "Master Controller ESP32 board: PoE",
            "Epson printer: Ethernet only, separate PSU",
            "Keep total PoE load under 62W switch budget.",
        ],
        3030,
        115,
        800,
        13,
        "#ffffff",
        "#cbd5e1",
    )
    add_label(
        "power_source_table",
        [
            "Power-source table",
            "PoE switch adapter: powers LS108GP.",
            "LS108GP PoE: powers ESP32 controller boards only.",
            "Epson PSU: powers receipt printer.",
            "12V Adapter A: 12V_SHOW actual loads.",
            "12V Adapter B: Buck #2 / 5V_LED.",
            "12V Adapter C: Buck #3 / 5V_AUDIO_SERVO.",
            "12V Adapter D: Buck #1 / 5V_AUX.",
            "Buck #1: optional 5V_AUX. Buck #2: 5V_LED. Buck #3: 5V_AUDIO_SERVO.",
        ],
        3030,
        395,
        800,
        13,
        "#ffffff",
        "#cbd5e1",
    )
    add_label(
        "safety_callouts",
        [
            "Safety and separation callouts",
            "Keep AC wiring enclosed and strain-relieved.",
            "Use manufacturer supplies for switch and Epson.",
            "Do not expose AC terminals.",
            "Do not use the open-frame 5V/60A supply unless fused distribution is added.",
            "Do not power LEDs, servos, lamps, or amps from ESP32 PoE boards.",
            "Do not tie buck 5V positives together.",
            "Do not tie separate 12V adapter positives together.",
            "Verify adjustable adapters with a multimeter.",
        ],
        3030,
        675,
        800,
        13,
        "#fff7ed",
        "#fb923c",
        "#7c2d12",
        "#1f2933",
    )
    add_label(
        "grounding_callout",
        [
            "Grounding rule",
            "All grounds must be common where GPIO/data/control signals cross between PoE ESP32 boards and external 5V/12V accessories.",
            "Do not route high-current LED/servo/audio return current through ESP32 ground pins.",
            "Use the COMMON_GND terminal block or a proper ground bus.",
        ],
        3030,
        985,
        800,
        13,
        "#f8fafc",
        "#111111",
    )
    add_label(
        "network_notes",
        [
            "Network behavior",
            "ESP32 modules receive IPs from router/DHCP or use static IPs.",
            "Master Controller ESP32 communicates with modules over Ethernet.",
            "Printer is addressed by IP.",
            "PoE switch may be unmanaged.",
            "No router: static IP plan required.",
            "Do not rely on internet access during the event.",
        ],
        3030,
        1195,
        800,
        13,
        "#eff6ff",
        "#60a5fa",
        "#1e3a8a",
        "#1f2933",
    )
    add_label(
        "setup_notes",
        [
            "Setup checklist highlights",
            "Label both ends of every power cable.",
            "Do not connect 12V to 5V devices.",
            "Do not connect 5V to ESP32 3.3V pins.",
            "Use proper wire gauge; avoid breadboards for multi-amp loads.",
            "Add 1000uF near LEDs, 470uF-1000uF near servo/audio.",
            "Add 330-470 ohm resistor on WS2812 data lines.",
        ],
        3030,
        1435,
        800,
        13,
        "#ffffff",
        "#cbd5e1",
    )

    # AC distribution.
    routed_wire("ac", "ac_switch", "switch_psu", "ac_in", [(420, 366), (420, 310)], WIRE["ac"], "AC power to LS108GP adapter", 5)
    routed_wire("ac", "ac_epson", "epson_psu", "ac_in", [(420, 470), (420, 450)], WIRE["ac"], "AC power to Epson printer PSU", 5)
    routed_wire("ac", "ac_adapter_a", "adapter_a", "ac_in", [(420, 728), (420, 1106)], WIRE["ac"], "AC power to 12V Adapter A", 5)
    routed_wire("ac", "ac_adapter_d", "adapter_d", "ac_in", [(410, 1070), (410, 1191)], WIRE["ac"], "AC power to 12V Adapter D", 5)
    routed_wire("ac", "ac_adapter_b", "adapter_b", "ac_in", [(402, 842), (402, 1311)], WIRE["ac"], "AC power to 12V Adapter B", 5)
    routed_wire("ac", "ac_adapter_c", "adapter_c", "ac_in", [(394, 956), (394, 1456)], WIRE["ac"], "AC power to 12V Adapter C", 5)

    # Manufacturer DC supplies and network host/printer power.
    routed_wire("switch_psu", "out", "switch", "dc_in", [(780, 310), (780, 502)], WIRE["dc_misc"], "53.5V DC adapter output to LS108GP", 7)
    routed_wire("epson_psu", "out", "printer", "pwr", [(780, 450), (780, 968)], WIRE["dc_misc"], "Epson manufacturer PSU to printer", 7)

    # Ethernet and PoE network.
    module_map = [
        ("p1", "simon_esp", 1490),
        ("p2", "chop_esp", 1518),
        ("p3", "pan_esp", 1546),
        ("p4", "pot_esp", 1574),
        ("p5", "garnish_esp", 1602),
    ]
    for port, module_key, lane_x in module_map:
        _, port_y = abs_pos("switch", port)
        _, module_y = abs_pos(module_key, "eth")
        routed_wire(
            "switch",
            port,
            module_key,
            "eth",
            [(lane_x, port_y), (lane_x, module_y)],
            WIRE["ethernet"],
            f"Ethernet + PoE from LS108GP {port} to {module_key}",
            8,
        )
    routed_wire("switch", "p6", "master_esp", "eth", [(1010, 610), (820, 610), (820, 692)], WIRE["ethernet"], "Ethernet + PoE from switch to Master Controller ESP32", 8)
    routed_wire("switch", "p7", "printer", "eth", [(1104, 610), (810, 610), (810, 900)], WIRE["ethernet"], "Ethernet from switch to Epson printer", 8)
    routed_wire("switch", "p8", "router", "eth", [(1276, 210), (1230, 210)], WIRE["ethernet"], "Optional router/DHCP source to switch port 8", 8)

    # Master Controller local GPIO.
    routed_wire(
        "master_esp",
        "gpio5",
        "start_button",
        "sig",
        [(1284, abs_pos("master_esp", "gpio5")[1]), (1284, abs_pos("start_button", "sig")[1])],
        WIRE["gpio"],
        "Master Controller GPIO5 to Start Game button signal",
        7,
    )
    routed_wire(
        "master_esp",
        "gnd",
        "gndrail",
        "tap16",
        [(abs_pos("master_esp", "gnd")[0], abs_pos("gndrail", "tap16")[1])],
        WIRE["gnd"],
        "Master Controller ESP32 GND reference to COMMON_GND",
        8,
    )
    routed_wire(
        "master_esp",
        "gnd_btn",
        "start_button",
        "gnd",
        [(1284, abs_pos("master_esp", "gnd_btn")[1]), (1284, abs_pos("start_button", "gnd")[1])],
        WIRE["gnd"],
        "Start Game button GND to Master Controller GND pin",
        8,
    )

    # 12V adapters, buck converters, and accessory rails.
    routed_wire("adapter_a", "pos", "rail12", "tap0", [(830, 1084), (1180, 1084), (1180, 1343)], WIRE["v12"], "Adapter A +12V to 12V_SHOW / actual loads terminal block", 12)
    routed_wire("adapter_d", "pos", "buck1", "in_pos", [(830, 1169), (830, 1124)], WIRE["v12"], "Adapter D +12V to Buck #1 input", 10)
    routed_wire("adapter_b", "pos", "buck2", "in_pos", [(830, 1289), (830, 1304)], WIRE["v12"], "Adapter B +12V to Buck #2 input", 10)
    routed_wire("adapter_c", "pos", "buck3", "in_pos", [(830, 1434), (830, 1484)], WIRE["v12"], "Adapter C +12V to Buck #3 input", 10)

    routed_wire("buck1", "out_pos", "rail5aux", "tap0", [(1200, 1124), (1200, 1673)], WIRE["v5"], "Buck #1 output to 5V_AUX rail", 10)
    routed_wire("buck2", "out_pos", "rail5led", "tap0", [(1208, 1304), (1208, 1453)], WIRE["v5"], "Buck #2 output to 5V_LED rail", 10)
    routed_wire("buck3", "out_pos", "rail5audio", "tap0", [(1216, 1484), (1216, 1563)], WIRE["v5"], "Buck #3 output to 5V_AUDIO_SERVO rail", 10)

    ground_sources = [
        ("adapter_a", "gnd", "tap0", 815),
        ("adapter_b", "gnd", "tap1", 805),
        ("adapter_c", "gnd", "tap2", 795),
        ("adapter_d", "gnd", "tap3", 785),
        ("buck1", "in_gnd", "tap4", 840),
        ("buck1", "out_gnd", "tap5", 1210),
        ("buck2", "in_gnd", "tap6", 850),
        ("buck2", "out_gnd", "tap7", 1222),
        ("buck3", "in_gnd", "tap8", 860),
        ("buck3", "out_gnd", "tap9", 1234),
    ]
    for source, conn, tap, lane_x in ground_sources:
        sx, _ = abs_pos(source, conn)
        _, gy = abs_pos("gndrail", tap)
        routed_wire(source, conn, "gndrail", tap, [(lane_x, abs_pos(source, conn)[1]), (lane_x, gy)], WIRE["gnd"], f"{source} ground to COMMON_GND", 11)

    # Per-module GPIO/data/control branches.
    module_order = [
        ("simon", "simon_esp", "simon_term", "tap10", "tap11"),
        ("chop", "chop_esp", "chop_term", "tap11", "tap12"),
        ("pan", "pan_esp", "pan_term", "tap12", "tap13"),
        ("pot", "pot_esp", "pot_term", "tap13", "tap14"),
        ("garnish", "garnish_esp", "garnish_term", "tap14", "tap15"),
    ]
    for _name, esp_key, term_key, esp_gnd_tap, term_gnd_tap in module_order:
        gpio_lane_x = abs_pos(esp_key, "gpio")[0] + 24
        routed_wire(
            esp_key,
            "gpio",
            term_key,
            "ctrl",
            [(gpio_lane_x, abs_pos(esp_key, "gpio")[1]), (gpio_lane_x, abs_pos(term_key, "ctrl")[1])],
            WIRE["gpio"],
            f"{esp_key} GPIO/data/control to local accessory drivers",
            7,
        )
        routed_wire(
            esp_key,
            "gnd",
            "gndrail",
            esp_gnd_tap,
            [(abs_pos(esp_key, "gnd")[0], abs_pos("gndrail", esp_gnd_tap)[1])],
            WIRE["gnd"],
            f"{esp_key} GND reference to COMMON_GND",
            8,
        )
        routed_wire(
            term_key,
            "gnd",
            "gndrail",
            term_gnd_tap,
            [(abs_pos(term_key, "gnd")[0], abs_pos("gndrail", term_gnd_tap)[1])],
            WIRE["gnd"],
            f"{term_key} accessory return to COMMON_GND",
            10,
        )

    # Accessory rail branches. Only connect branches that are expected or plausible for each module.
    branch_specs = [
        ("rail12", "tap9", "simon_term", "v12", 2182, WIRE["v12"], 10, "Optional 12V Simon lamps/show loads if lamps are rated 12V"),
        ("rail5led", "tap9", "simon_term", "v5_led", 2195, WIRE["v5"], 9, "5V_LED to Simon 5V lamps if used"),
        ("rail5audio", "tap9", "simon_term", "v5_audio", 2208, WIRE["v5"], 9, "5V_AUDIO_SERVO to Simon audio if used"),
        ("rail5aux", "tap8", "chop_term", "v5_aux", 2208, WIRE["v5"], 8, "5V_AUX to Chopping LCD backlight / low-current peripherals"),
        ("rail12", "tap11", "pan_term", "v12", 2182, WIRE["v12"], 10, "Optional 12V_SHOW to Pan cooktop LED if strip is 12V"),
        ("rail5led", "tap11", "pan_term", "v5_led", 2195, WIRE["v5"], 9, "5V_LED to Pan cooktop LED if strip is 5V"),
        ("rail5audio", "tap11", "pan_term", "v5_audio", 2208, WIRE["v5"], 9, "5V_AUDIO_SERVO to Pan DFPlayer/audio"),
        ("rail12", "tap13", "pot_term", "v12", 2182, WIRE["v12"], 10, "Optional 12V_SHOW to Pot cooktop LED if strip is 12V"),
        ("rail5led", "tap13", "pot_term", "v5_led", 2195, WIRE["v5"], 9, "5V_LED to Pot temp indicator ring/strip"),
        ("rail5aux", "tap13", "pot_term", "v5_aux", 2208, WIRE["v5"], 8, "Optional 5V_AUX to Pot low-current accessories"),
        ("rail5led", "tap15", "garnish_term", "v5_led", 2195, WIRE["v5"], 9, "5V_LED to Garnish RGB strip"),
        ("rail5audio", "tap15", "garnish_term", "v5_audio", 2208, WIRE["v5"], 9, "5V_AUDIO_SERVO to Garnish servo"),
    ]
    for rail, tap, term_key, term_conn, lane_x, color, width, title in branch_specs:
        routed_wire(
            rail,
            tap,
            term_key,
            term_conn,
            [(lane_x, abs_pos(rail, tap)[1]), (lane_x, abs_pos(term_key, term_conn)[1])],
            color,
            title,
            width,
        )

    keyed = by_key()
    for item in wires:
        keyed[item.a].connects.setdefault(item.ac, []).append((item.idx, "connector0"))
        keyed[item.b].connects.setdefault(item.bc, []).append((item.idx, "connector1"))

    return inst, wires


def write_fzz(parts: dict[str, Part], inst: list[Instance], wires: list[Wire]) -> None:
    all_parts = {**parts, **parts_dynamic}
    keyed = {item.key: item for item in inst}
    fz_instances = "\n".join([wire_xml(wire, keyed, all_parts) for wire in wires] + [instance_xml(item, all_parts) for item in inst])
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
        zf.writestr("chef_station_master_power_network_editable.fz", fz)
        for part in all_parts.values():
            zf.writestr(part.fzp_name, part.fzp)
            for name, svg_text in part.svg_entries.items():
                zf.writestr(name, svg_text)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Master Power And Network Tables / Checklist

## Power Rail Table

| Rail | Source | Voltage | Use | Hard rule |
|---|---|---:|---|---|
| PoE | LS108GP switch ports | PoE | ESP32 controller boards only | Do not power LED strips, servos, lamps, or amplifiers from ESP32 PoE boards. |
| 12V_SHOW | 12V Adapter A | 12V DC | Actual 12V LED strips, 12V amplifier, fans, monitor accessory if rated 12V | Only connect devices explicitly rated for 12V. Do not tie to other adapter positives. |
| 5V_LED | 12V Adapter B -> Buck #2 | 5.0V-5.1V DC | WS2812/NeoPixel strips, cooktop coil LEDs, overhead strip, 5V Simon button lamps | Do not parallel with another buck output. |
| 5V_AUDIO_SERVO | 12V Adapter C -> Buck #3 | 5.0V-5.1V DC | DFPlayer modules, small amplifiers, small speakers, servo timer, optional LCD backlights | Do not feed from ESP32 5V/PoE board power. |
| 5V_AUX | 12V Adapter D -> Buck #1 | 5.0V-5.1V DC | Optional LCD backlights, small non-PoE accessories, low-current status LEDs, small relay boards | Keep low-current and isolated from other 5V positives. |
| COMMON_GND | Ground terminal block / bus | 0V reference | Shared reference where GPIO/data/control crosses rails | Do not route load return current through ESP32 ground pins. |

## Network Port Table

| LS108GP port | Device | Cable behavior | Power behavior |
|---|---|---|---|
| 1 | Simon ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 2 | Chopping ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 3 | Pan Motion ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 4 | Pot Temperature ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 5 | Garnish Placement ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 6 | Master Controller ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 7 | Epson TM-T20IV / TM-T20V-family printer | Ethernet network | Separate Epson manufacturer power supply. Not PoE. |
| 8 | Optional router/DHCP source or spare | DHCP/network management if needed | Router uses its own power if used. |

## Per-Module Accessory Power Table

| Module | ESP32 power/network | Accessory power | Control/ground notes |
|---|---|---|---|
| Simon | PoE over Ethernet | Button lamps from 5V_LED or 12V_SHOW by lamp rating; audio if present from 5V_AUDIO_SERVO | Button switches to ESP32 GPIO/GND. Lamp MOSFET sources to COMMON_GND. ESP32 GPIOs drive MOSFET gates only. |
| Chopping | PoE over Ethernet | Piezo from ESP32 3.3V if suitable; I2C LCD backlight from 5V_AUX or 5V_LED | Use optional I2C level shifter for 5V I2C LCD. LCD/piezo ground common with ESP32. |
| Pan Motion | PoE over Ethernet | Hall sensors from ESP32 3.3V; cooktop LED from 5V_LED or 12V_SHOW by strip type; DFPlayer/audio from 5V_AUDIO_SERVO | ESP32 sends LED data and serial to DFPlayer. All grounds common. |
| Pot Temperature | PoE over Ethernet | Encoder on ESP32 GPIO; cooktop LED from 5V_LED or 12V_SHOW; temp strip/ring from 5V_LED | Encoder uses INPUT_PULLUP. ESP32 and LED rail grounds common. |
| Garnish Placement | PoE over Ethernet | Touch electrodes only to ESP32 touch pins through 1k resistors; RGB strip from 5V_LED; servo from 5V_AUDIO_SERVO | DONE button to ESP32 GPIO/GND. ESP32, servo, and LED grounds common. |
| Master Controller | PoE over Ethernet | Start Game button only; Epson printer is Ethernet | GPIO5 to one side of the Start Game button, other side to GND. Configure GPIO5 with INPUT_PULLUP. |

## Master Controller ESP32 Pin Map

| Function | Master Controller ESP32 connection | Destination | Notes |
|---|---|---|---|
| Power/network | RJ45 Ethernet / PoE | LS108GP port 6 | PoE powers the ESP32 controller only. |
| Start Game button signal | GPIO5 | One side of momentary normally-open Start Game button | `INPUT_PULLUP`; unpressed = HIGH, pressed = LOW. |
| Start Game button ground | GND | Other side of Start Game button / COMMON_GND | This is the only local GPIO wiring on the Master Controller ESP32. |
| Module commands and score replies | Ethernet UDP port 42100 | Simon, chopping, pan, pot-temp, and garnish ESP32 boards | No GPIO start/reset harness between controller and modules. |
| Receipt printer | Ethernet TCP port 9100 | Epson TM-T20IV / TM-T20V-family printer | Printer uses its own Epson power supply; no ESP32 GPIO pins. |

## Grounding Notes

- All grounds must be common where GPIO/data/control signals cross between PoE ESP32 boards and external 5V/12V accessories.
- Connect Adapter A/B/C/D negatives, Buck #1/#2/#3 grounds, LED strip ground, DFPlayer/audio ground, servo ground, Simon lamp ground, and any relevant ESP32 GND pins to COMMON_GND.
- Module commands travel over Ethernet, so no separate GPIO sync harness is required for module start/reset.
- Do not route high-current LED, servo, or audio return current through ESP32 ground pins. Use a ground terminal block or bus.
- Grounds may be common; separate 12V positives and separate buck 5V positives must not be tied together.

## Setup Checklist

- Verify every adapter output with a multimeter before connecting electronics.
- Tape or lock adjustable adapter selector dials at 12V.
- Adjust buck converters to 5.0V-5.1V before connecting 5V electronics.
- Label both ends of every power cable.
- Confirm 12V_SHOW never touches 5V devices.
- Confirm 5V rails never touch ESP32 3.3V pins.
- Keep each 12V adapter as its own limited-current branch.
- Do not parallel separate wall adapter outputs.
- Do not parallel separate buck converter outputs.
- Use proper wire gauge for LED, servo, and audio currents.
- Avoid breadboard rails for multi-amp loads.
- Add 1000uF across LED strip 5V/GND near strip input.
- Add 470uF-1000uF near servo power.
- Add 470uF-1000uF near DFPlayer/audio modules.
- Add 0.1uF near Hall, piezo, and small sensor modules.
- Add a 330-470 ohm resistor on each WS2812 data line.
- If no fuses are available, avoid the 5V/60A open-frame supply in this temporary build.

## Warning Callouts

- PoE budget: keep total ESP32 PoE load under the LS108GP 62W budget and 30W per-port max.
- Common ground: required wherever GPIO/data/control signals cross between ESP32 boards and external accessory power rails.
- 12V vs 5V separation: only 12V-rated devices connect to 12V_SHOW; 5V devices connect only to named buck-derived 5V rails.
- No high-current loads from ESP32 PoE boards: ESP32 GPIOs send signals only.
- No unfused 60A supply in the temporary build: add fused distribution before using any large open-frame supply.
- Do not parallel buck outputs.
- Verify adjustable adapters with a multimeter.

## Network Behavior Notes

- ESP32 modules can receive IP addresses from a router/DHCP source or use static IPs.
- If there is no router, create and label a static IP plan before the event.
- The Master Controller ESP32 communicates with modules over Ethernet.
- The Epson printer is addressed by IP.
- The LS108GP may be unmanaged; use an optional router/DHCP source if network management is needed.
- Do not rely on internet access during the event.

## Assumptions And Substitutions

- The master controller in this build is a Waveshare ESP32-P4-POE-ETH / NH board.
- Hardware START_SYNC / RESET_SYNC wiring is intentionally omitted. Module start/reset/score traffic is planned over Ethernet.
- Exact LS108GP and Waveshare ESP32-P4-POE-ETH/NH Fritzing parts were not available in the installed library, so the sketch embeds custom editable helper parts with labeled connectors.
- No third-party parts were downloaded.
- The diagram is a master power/network layout, not a PCB fabrication footprint.
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
            "--window-size=3920,2200",
            svg_path.as_uri(),
        ],
        check=True,
    )


def count_diagonal_segments(inst: list[Instance], wires: list[Wire], parts: dict[str, Part]) -> int:
    all_parts = {**parts, **parts_dynamic}
    keyed = {item.key: item for item in inst}
    diagonal = 0
    for wire in wires:
        a = keyed[wire.a]
        b = keyed[wire.b]
        ax, ay = all_parts[a.part].pins[wire.ac]
        bx, by = all_parts[b.part].pins[wire.bc]
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
