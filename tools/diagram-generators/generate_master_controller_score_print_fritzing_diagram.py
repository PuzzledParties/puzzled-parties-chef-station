from __future__ import annotations

import html
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "master-controller-score-print"
FZZ_PATH = OUT_DIR / "chef_station_master_controller_score_print_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_master_controller_score_print_wiring_diagram.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_master_controller_score_print.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


WIRE = {
    "v5": "#d71920",
    "gnd": "#111111",
    "control": "#1e88e5",
    "ethernet": "#1e88e5",
    "led": "#178f46",
    "usb": "#5b6472",
    "v3": "#db2777",
    "note": "#f59e0b",
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
    module_id = f"chef_master_{key}"

    def svg_for(layer: str) -> str:
        connector_svg = []
        for connector in connectors:
            connector_svg.append(
                f'<circle id="{connector.cid}pin" cx="{connector.x}" cy="{connector.y}" r="5.2" '
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
  <tags><tag>chef station</tag><tag>master controller</tag><tag>score</tag><tag>receipt printer</tag></tags>
  <properties>
    <property name="family">Chef Station Master Controller / Score + Print Layer</property>
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
    width: int = 300,
    size: int = 14,
    fill: str = "#fffefa",
    stroke: str = "#d0d7de",
    heading_fill: str = "#1f2933",
) -> Part:
    height = max(38, 20 + len(lines) * (size + 5))
    body = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="6" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
    ]
    y = 21
    for index, line in enumerate(lines):
        body.append(text(10, y, line, size, heading_fill if index == 0 else "#1f2933", 750 if index == 0 else 500))
        y += size + 5
    return custom_part(key, lines[0], "TXT", width, height, "".join(body))


def make_waypoint_part() -> Part:
    body = '<circle id="pinmark" cx="3" cy="3" r="1.8" fill="#ffffff" stroke="#6b7280" stroke-width="0.7"/>'
    return custom_part("waypoint", "Wire waypoint", "WP", 6, 6, body, [Connector("pin", "waypoint", 3, 3)])


def make_breadboard_part() -> Part:
    holes = []
    for x in range(42, 930, 24):
        for y in range(128, 1010, 24):
            holes.append(f'<circle cx="{x}" cy="{y}" r="1.9" fill="#d9d2c3"/>')
    body = (
        '<rect x="0" y="0" width="980" height="1120" rx="10" fill="#f1ead7" stroke="#d8ccb0" stroke-width="2"/>'
        + text(24, 36, "Breadboard / terminal block field", 24, "#52606d", 750)
        + text(24, 66, "Manhattan rails and labeled signal terminal blocks", 15, "#52606d", 500)
        + "".join(holes)
    )
    return custom_part("breadboard_field", "Breadboard / terminal block field", "BB", 980, 1120, body)


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 18, width: int = 900) -> Part:
    spacing = (width - 70) / max(1, tap_count - 1)
    connectors = [Connector(f"tap{i}", f"{title} tap {i}", 35 + i * spacing, 24) for i in range(tap_count)]
    circles = "".join(
        f'<circle cx="{35+i*spacing}" cy="24" r="4.0" fill="#ffffff" stroke="{color}" stroke-width="1.7"/>'
        for i in range(tap_count)
    )
    body = (
        f'<rect x="0" y="0" width="{width}" height="72" rx="8" fill="#ffffff" stroke="#9aa5b1" stroke-width="1.3"/>'
        f'<line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="8" stroke-linecap="round"/>'
        f'{circles}'
        f'{text(14, 58, note, 14, "#1f2933", 750)}'
    )
    return custom_part(key, title, "RAIL", width, 72, body, connectors, buses={key: [f"tap{i}" for i in range(tap_count)]})


def make_resistor_part(key: str, title: str, value_label: str, band3: str = "#6b4f1d") -> Part:
    body = (
        '<line x1="0" y1="18" x2="30" y2="18" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="90" y1="18" x2="120" y2="18" stroke="#6b4f1d" stroke-width="4" stroke-linecap="round"/>'
        '<rect x="30" y="5" width="60" height="26" rx="8" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>'
        '<rect x="39" y="6" width="4" height="24" fill="#f57c00"/>'
        '<rect x="50" y="6" width="4" height="24" fill="#f57c00"/>'
        f'<rect x="61" y="6" width="4" height="24" fill="{band3}"/>'
        '<rect x="72" y="6" width="4" height="24" fill="#c49a23"/>'
        + text(60, 50, value_label, 13, "#1f2933", 750, "middle")
    )
    return custom_part(
        key,
        title,
        "R",
        120,
        60,
        body,
        [Connector("a", "lead A", 0, 18), Connector("b", "lead B", 120, 18)],
        properties={"Resistance": value_label},
    )


def make_capacitor_part(key: str, title: str, value_label: str, large: bool = False) -> Part:
    body = (
        '<line x1="0" y1="42" x2="43" y2="42" stroke="#4b5563" stroke-width="3"/>'
        '<line x1="77" y1="42" x2="120" y2="42" stroke="#4b5563" stroke-width="3"/>'
        '<rect x="43" y="14" width="34" height="56" rx="8" fill="#1f2937" stroke="#111827" stroke-width="2"/>'
        '<rect x="50" y="19" width="7" height="46" fill="#e5e7eb" opacity="0.8"/>'
        + text(18, 92 if large else 88, value_label, 13, "#1f2933", 750)
        + text(48, 36, "+", 17, "#ffffff", 800)
        + text(66, 36, "-", 17, "#ffffff", 800)
    )
    return custom_part(
        key,
        title,
        "C",
        120,
        102 if large else 96,
        body,
        [Connector("pos", "positive", 0, 42), Connector("neg", "negative", 120, 42)],
        properties={"Capacitance": value_label},
    )


def make_pi_part() -> Part:
    pins = [
        ("pwr_usb", "Official USB-C power in", 18, 78, WIRE["usb"]),
        ("usb_printer", "USB to Epson printer", 368, 86, WIRE["usb"]),
        ("eth_modules", "Ethernet to module network", 368, 151, WIRE["ethernet"]),
        ("usb_audio", "USB audio dongle / powered speaker", 368, 216, WIRE["usb"]),
        ("gnd", "GND to common logic ground", 368, 304, WIRE["gnd"]),
        ("pin_3v3", "3.3V logic rail", 368, 339, WIRE["v3"]),
        ("gpio2", "GPIO2 / SDA to ADS1115", 368, 379, WIRE["control"]),
        ("gpio3", "GPIO3 / SCL to ADS1115", 368, 419, WIRE["control"]),
        ("gpio5", "GPIO5 Start Game input", 368, 464, WIRE["control"]),
        ("gpio18", "GPIO18 LED data", 368, 509, WIRE["led"]),
    ]
    connectors = [Connector(cid, name, x, y, color) for cid, name, x, y, color in pins]
    pin_labels = "".join(text(210, y + 4, name.split(" to ")[0], 12, color, 750) for _cid, name, _x, y, color in pins[4:])
    usb_labels = (
        text(192, 91, "USB: Epson receipt printer", 12, "#f8fafc", 750)
        + text(192, 156, "ETH: module UDP commands", 12, "#bfdbfe", 750)
        + text(192, 221, "USB: controller speaker", 12, "#f8fafc", 750)
    )
    body = (
        '<rect x="54" y="18" width="282" height="650" rx="18" fill="#136f63" stroke="#064e3b" stroke-width="3"/>'
        '<rect x="82" y="46" width="118" height="82" rx="10" fill="#111827" stroke="#374151" stroke-width="2"/>'
        + text(141, 79, "Raspberry Pi", 18, "#ffffff", 850, "middle")
        + text(141, 103, "4/5/Zero 2 W host", 12, "#d1fae5", 700, "middle")
        + '<rect x="84" y="184" width="84" height="72" rx="7" fill="#e5e7eb" stroke="#9ca3af"/>'
        + text(126, 226, "SoC", 18, "#374151", 800, "middle")
        + '<rect x="78" y="302" width="96" height="38" rx="5" fill="#111827"/>'
        + text(126, 327, "40-pin GPIO", 12, "#f8fafc", 800, "middle")
        + '<rect x="52" y="64" width="32" height="28" rx="5" fill="#cbd5e1" stroke="#64748b"/>'
        + text(88, 82, "USB-C power only", 11, "#d1fae5", 700)
        + '<rect x="318" y="68" width="28" height="36" rx="5" fill="#cbd5e1" stroke="#64748b"/>'
        + '<rect x="318" y="133" width="28" height="36" rx="5" fill="#cbd5e1" stroke="#64748b"/>'
        + '<rect x="318" y="198" width="28" height="36" rx="5" fill="#cbd5e1" stroke="#64748b"/>'
        + usb_labels
        + pin_labels
        + text(195, 634, "Pi is not powered from the breadboard 5V rail", 12, "#fef3c7", 800, "middle")
    )
    return custom_part("raspberry_pi_master", "Raspberry Pi master score/print host", "PI", 386, 684, body, connectors)


def make_pi_power_part() -> Part:
    body = (
        '<rect x="0" y="0" width="305" height="120" rx="10" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(18, 30, "Raspberry Pi official PSU", 18, "#1f2933", 800)
        + text(18, 58, "USB-C or micro-USB as required", 13, "#1f2933", 600)
        + text(18, 86, "Do not backfeed from breadboard 5V", 13, "#7c2d12", 800)
        + text(270, 64, "USB power", 12, WIRE["usb"], 800, "end")
    )
    return custom_part("pi_official_power_supply", "Official Raspberry Pi power supply", "PSU", 305, 120, body, [Connector("out", "USB-C/micro-USB output", 286, 62, WIRE["usb"])])


def make_led_supply_part() -> Part:
    body = (
        '<rect x="0" y="0" width="282" height="136" rx="9" fill="#fff7ed" stroke="#f59e0b" stroke-width="2"/>'
        + text(16, 27, "External regulated 5V", 19, "#1f2933", 800)
        + text(16, 54, "LED strip supply", 21, WIRE["v5"], 850)
        + text(16, 84, "+5V to LED rail", 13, "#1f2933", 700)
        + text(16, 106, "GND to common rail", 13, "#1f2933", 700)
        + text(238, 54, "+5V", 13, WIRE["v5"], 800, "end")
        + text(238, 101, "GND", 13, WIRE["gnd"], 800, "end")
    )
    return custom_part(
        "external_5v_led_supply",
        "External regulated 5V LED supply",
        "5V",
        282,
        136,
        body,
        [Connector("vcc", "+5V", 260, 50, WIRE["v5"]), Connector("gnd", "GND", 260, 98, WIRE["gnd"])],
    )


def make_epson_power_part() -> Part:
    body = (
        '<rect x="0" y="0" width="260" height="92" rx="9" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(16, 28, "Epson manufacturer PSU", 17, "#1f2933", 800)
        + text(16, 55, "Powers printer only", 13, "#1f2933", 700)
        + text(220, 55, "DC out", 12, WIRE["usb"], 800, "end")
    )
    return custom_part("epson_manufacturer_power_supply", "Epson manufacturer power supply", "PSU", 260, 92, body, [Connector("out", "printer power output", 238, 52, WIRE["usb"])])


def make_printer_part() -> Part:
    body = (
        '<rect x="0" y="0" width="380" height="200" rx="13" fill="#f8fafc" stroke="#475569" stroke-width="2.4"/>'
        '<rect x="32" y="42" width="316" height="96" rx="10" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>'
        '<rect x="74" y="70" width="232" height="24" rx="5" fill="#ffffff" stroke="#94a3b8"/>'
        '<path d="M88 124 L292 124 L276 176 L104 176 Z" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>'
        + text(190, 31, "Epson TM-T20IV / TM-T20V-family", 17, "#1f2933", 850, "middle")
        + text(190, 112, "ESC/POS receipt printer", 14, "#334155", 800, "middle")
        + text(24, 177, "USB", 12, WIRE["usb"], 800)
        + text(333, 177, "PWR", 12, WIRE["usb"], 800)
        + text(190, 190, "Optional Ethernet if networked model", 12, "#334155", 700, "middle")
    )
    return custom_part(
        "epson_receipt_printer",
        "Epson TM-T20IV / TM-T20V-family receipt printer",
        "PRN",
        380,
        200,
        body,
        [
            Connector("usb", "USB from Raspberry Pi", 20, 174, WIRE["usb"]),
            Connector("pwr", "Epson power input", 360, 174, WIRE["usb"]),
            Connector("eth", "Optional Ethernet", 190, 198, WIRE["usb"]),
        ],
    )


def make_receipt_part() -> Part:
    lines = [
        ("R + B GRILL", 28, 800),
        ("[384 px monochrome logo bitmap]", 13, 700),
        ("CHEF SCORE RECEIPT", 18, 800),
        ("TOTAL SCORE: 084 / 100", 15, 800),
        ("Simon:        092", 14, 650),
        ("Chop Speed:   085", 14, 650),
        ("Pan Motion:   078", 14, 650),
        ("Pot Temp:     073", 14, 650),
        ("Garnish:      080", 14, 650),
        ("Result:", 14, 650),
        ("LINE COOK LEGEND", 17, 800),
        ("Thank you for dining", 13, 650),
        ("at R + B Grill", 13, 650),
    ]
    body = [
        '<rect x="0" y="0" width="330" height="430" rx="8" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>',
        '<rect x="52" y="54" width="226" height="66" rx="5" fill="#f8fafc" stroke="#cbd5e1"/>',
        '<path d="M86 102 L118 70 L146 98 L176 74 L222 106" fill="none" stroke="#111111" stroke-width="4"/>',
    ]
    y = 38
    for value, size, weight in lines:
        body.append(text(165, y, value, size, "#111827", weight, "middle"))
        if value == "[384 px monochrome logo bitmap]":
            y += 60
        else:
            y += size + 10
    body.append(text(165, 414, "ESC/POS raster logo + text + cut", 12, "#475569", 700, "middle"))
    return custom_part("receipt_printout_preview", "Receipt printout preview with R + B Grill logo placeholder", "RCT", 330, 430, "".join(body))


def make_usb_speaker_part() -> Part:
    body = (
        '<rect x="0" y="0" width="280" height="160" rx="10" fill="#eef2ff" stroke="#64748b" stroke-width="2"/>'
        '<circle cx="192" cy="82" r="52" fill="#1f2937" stroke="#111827" stroke-width="4"/>'
        '<circle cx="192" cy="82" r="34" fill="#334155" stroke="#94a3b8" stroke-width="2"/>'
        '<circle cx="192" cy="82" r="14" fill="#94a3b8"/>'
        + text(22, 34, "USB powered speaker", 17, "#1f2933", 800)
        + text(22, 61, "or USB audio dongle", 13, "#1f2933", 650)
        + text(22, 91, "3-2-1-GO beeps", 13, "#1f2933", 750)
        + text(22, 114, "victory jingle", 13, "#1f2933", 750)
        + text(22, 142, "software volume", 12, "#1f2933", 650)
    )
    return custom_part("usb_audio_speaker", "Local controller USB audio speaker", "SPK", 280, 160, body, [Connector("usb", "USB audio from Raspberry Pi", 20, 132, WIRE["usb"])])


def make_ads1115_part() -> Part:
    body = (
        '<rect x="0" y="0" width="250" height="220" rx="10" fill="#ecfdf5" stroke="#059669" stroke-width="2"/>'
        '<rect x="69" y="62" width="110" height="72" rx="8" fill="#064e3b" stroke="#047857"/>'
        + text(124, 93, "ADS1115", 18, "#ffffff", 850, "middle")
        + text(124, 117, "I2C ADC", 13, "#d1fae5", 750, "middle")
        + text(20, 35, "VDD 3.3V", 12, WIRE["v3"], 800)
        + text(20, 65, "GND", 12, WIRE["gnd"], 800)
        + text(20, 98, "SDA", 12, WIRE["control"], 800)
        + text(20, 131, "SCL", 12, WIRE["control"], 800)
        + text(205, 98, "A0", 12, WIRE["control"], 800)
        + text(195, 139, "ADDR", 12, WIRE["gnd"], 800)
        + text(124, 190, "ADDR to GND = 0x48", 12, "#065f46", 800, "middle")
    )
    return custom_part(
        "ads1115_adc",
        "ADS1115 I2C ADC for master volume",
        "ADC",
        250,
        220,
        body,
        [
            Connector("vdd", "VDD 3.3V", 20, 32, WIRE["v3"]),
            Connector("gnd", "GND", 20, 62, WIRE["gnd"]),
            Connector("sda", "SDA to GPIO2", 20, 95, WIRE["control"]),
            Connector("scl", "SCL to GPIO3", 20, 128, WIRE["control"]),
            Connector("a0", "A0 volume pot wiper", 230, 95, WIRE["control"]),
            Connector("addr", "ADDR to GND", 230, 136, WIRE["gnd"]),
        ],
    )


def make_pot_part() -> Part:
    body = (
        '<rect x="0" y="0" width="260" height="170" rx="10" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
        '<circle cx="178" cy="86" r="55" fill="#1e293b" stroke="#0f172a" stroke-width="4"/>'
        '<circle cx="178" cy="86" r="31" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>'
        '<line x1="178" y1="86" x2="205" y2="57" stroke="#f8fafc" stroke-width="5" stroke-linecap="round"/>'
        + text(24, 33, "10k linear pot", 16, "#1f2933", 800)
        + text(24, 60, "Master Volume", 18, "#1d4ed8", 850)
        + text(26, 91, "3.3V", 12, WIRE["v3"], 800)
        + text(26, 122, "WIPER", 12, WIRE["control"], 800)
        + text(26, 151, "GND", 12, WIRE["gnd"], 800)
    )
    return custom_part(
        "master_volume_pot",
        "Master Volume 10k linear potentiometer",
        "POT",
        260,
        170,
        body,
        [
            Connector("vcc", "outer lug 1 to 3.3V", 22, 88, WIRE["v3"]),
            Connector("wiper", "center wiper to ADS1115 A0", 22, 119, WIRE["control"]),
            Connector("gnd", "outer lug 2 to GND", 22, 148, WIRE["gnd"]),
        ],
    )


def make_start_button_part() -> Part:
    body = (
        '<rect x="0" y="0" width="280" height="170" rx="10" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
        '<circle cx="190" cy="82" r="54" fill="#1e88e5" stroke="#0f5fa8" stroke-width="5"/>'
        '<circle cx="190" cy="82" r="34" fill="#73b7ff" stroke="#e0f2fe" stroke-width="2"/>'
        + text(190, 88, "START", 18, "#ffffff", 850, "middle")
        + text(24, 39, "Start Game", 18, "#1f2933", 850)
        + text(24, 73, "GPIO5", 13, WIRE["control"], 800)
        + text(24, 108, "GND", 13, WIRE["gnd"], 800)
        + text(24, 141, "INPUT_PULLUP", 12, "#1f2933", 800)
    )
    return custom_part(
        "start_game_button",
        "Start Game momentary pushbutton",
        "START",
        280,
        170,
        body,
        [
            Connector("sig", "GPIO5 button input, active LOW", 24, 70, WIRE["control"]),
            Connector("gnd", "button GND", 24, 105, WIRE["gnd"]),
        ],
    )


def make_level_shifter_part() -> Part:
    body = (
        '<rect x="0" y="0" width="270" height="185" rx="10" fill="#f0fdf4" stroke="#16a34a" stroke-width="2"/>'
        '<rect x="77" y="48" width="116" height="76" rx="8" fill="#14532d" stroke="#166534"/>'
        + text(135, 82, "74AHCT125", 16, "#ffffff", 850, "middle")
        + text(135, 105, "3.3V to 5V data", 12, "#dcfce7", 750, "middle")
        + text(24, 38, "A1 in", 12, WIRE["led"], 800)
        + text(24, 86, "/OE to GND", 12, WIRE["gnd"], 800)
        + text(24, 145, "GND", 12, WIRE["gnd"], 800)
        + text(203, 38, "VCC 5V", 12, WIRE["v5"], 800)
        + text(208, 96, "Y1 out", 12, WIRE["led"], 800)
    )
    return custom_part(
        "ahct_level_shifter",
        "74AHCT125 / 74HCT245 LED data level shifter",
        "AHCT",
        270,
        185,
        body,
        [
            Connector("a1", "A1 input from Raspberry Pi GPIO18", 22, 35, WIRE["led"]),
            Connector("oe", "OE tied to GND", 22, 83, WIRE["gnd"]),
            Connector("gnd", "GND", 22, 142, WIRE["gnd"]),
            Connector("vcc", "VCC 5V", 248, 35, WIRE["v5"]),
            Connector("y1", "Y1 5V data output", 248, 93, WIRE["led"]),
        ],
    )


def make_led_strip_part() -> Part:
    leds = []
    for index in range(10):
        x = 120 + index * 28
        leds.append(f'<rect x="{x}" y="32" width="19" height="19" rx="3" fill="#f8fafc" stroke="#aab3bd"/>')
        leds.append(f'<circle cx="{x+9.5}" cy="41.5" r="4.2" fill="#ffd166" opacity="0.7"/>')
    body = (
        '<rect x="0" y="0" width="430" height="150" rx="10" fill="#2f343b" stroke="#111111" stroke-width="2"/>'
        '<rect x="104" y="22" width="300" height="40" rx="5" fill="#111111" stroke="#8d99a6"/>'
        + "".join(leds)
        + text(22, 36, "+5V", 13, "#ffffff", 800)
        + text(22, 75, "DIN", 13, "#ffffff", 800)
        + text(22, 116, "GND", 13, "#ffffff", 800)
        + text(214, 98, "Overhead cooktop light", 18, "#ffffff", 850, "middle")
        + text(214, 123, "WS2812B / NeoPixel strip", 13, "#ffffff", 700, "middle")
    )
    return custom_part(
        "cooktop_overhead_led_strip",
        "Cooktop overhead WS2812B / NeoPixel LED strip",
        "LED",
        430,
        150,
        body,
        [
            Connector("vcc", "+5V from external LED supply", 22, 34, WIRE["v5"]),
            Connector("din", "LED DIN from level shifter through resistor", 22, 73, WIRE["led"]),
            Connector("gnd", "GND to common rail", 22, 114, WIRE["gnd"]),
        ],
    )


def make_debounce_cap_part() -> Part:
    body = (
        '<line x1="20" y1="10" x2="20" y2="80" stroke="#4b5563" stroke-width="3"/>'
        '<line x1="45" y1="10" x2="45" y2="80" stroke="#4b5563" stroke-width="3"/>'
        '<line x1="0" y1="45" x2="20" y2="45" stroke="#4b5563" stroke-width="3"/>'
        '<line x1="45" y1="45" x2="65" y2="45" stroke="#4b5563" stroke-width="3"/>'
        + text(32, 100, "0.1uF debounce", 12, "#1f2933", 750, "middle")
        + text(32, 116, "optional", 11, "#1f2933", 600, "middle")
    )
    return custom_part("button_debounce_cap", "Optional 0.1uF hardware debounce capacitor", "C", 65, 122, body, [Connector("a", "button signal side", 0, 45), Connector("b", "button GND side", 65, 45)])


def make_module_bus_part() -> Part:
    modules = [
        ("simon", "Simon Module", 306),
        ("chop", "Chopping Module", 406),
        ("pan", "Pan Motion Module", 506),
        ("pot_temp", "Pot Temperature Module", 606),
        ("garnish", "Garnish Placement Module", 706),
    ]
    connectors = [
        Connector("eth_in", "Ethernet from Pi/switch module network", 24, 90, WIRE["ethernet"]),
    ]
    bus_members = {"ETHERNET_UDP": ["eth_in"]}
    branch_svg = []
    for key, label, base_y in modules:
        cid = f"{key}_eth"
        connectors.append(Connector(cid, f"{label} Ethernet/UDP branch", 448, base_y, WIRE["ethernet"]))
        bus_members["ETHERNET_UDP"].append(cid)
        branch_svg.append(
            f'<line x1="132" y1="{base_y}" x2="448" y2="{base_y}" '
            f'stroke="{WIRE["ethernet"]}" stroke-width="5" stroke-linecap="round"/>'
        )
        branch_svg.append(text(286, base_y + 5, label, 12, "#1f2933", 750))
    bus_lanes = (
        f'<line x1="132" y1="90" x2="132" y2="706" stroke="{WIRE["ethernet"]}" stroke-width="8"/>'
    )
    input_stubs = (
        f'<line x1="24" y1="90" x2="132" y2="90" stroke="{WIRE["ethernet"]}" stroke-width="6"/>'
    )
    body = (
        '<rect x="0" y="0" width="470" height="840" rx="10" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
        + text(24, 32, "MODULE ETHERNET / UDP NETWORK", 19, "#1e3a8a", 850)
        + text(24, 54, "Commands and scores use UDP port 42100", 12, "#1e3a8a", 700)
        + bus_lanes
        + input_stubs
        + "".join(branch_svg)
        + text(50, 90, "ETH", 12, WIRE["ethernet"], 850)
        + text(286, 790, "No hardware START/RESET/DONE terminals", 12, "#1e3a8a", 750)
    )
    return custom_part("module_ethernet_udp_network", "MODULE ETHERNET / UDP NETWORK", "NET", 470, 840, body, connectors, buses=bus_members)


def make_module_connector_part(key: str, title: str) -> Part:
    body = (
        '<rect x="0" y="0" width="335" height="126" rx="9" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>'
        + text(26, 24, title, 17, "#1f2933", 850)
        + text(26, 52, "Ethernet / PoE to LS108GP", 12, WIRE["ethernet"], 800)
        + text(26, 76, "UDP 42100: START/RESET/SCORE", 12, "#1e3a8a", 800)
        + text(26, 101, "Local module wiring is shown on each station diagram", 12, "#475569", 650)
    )
    return custom_part(
        f"module_connector_{key}",
        f"{title} bus connector",
        "MOD",
        335,
        126,
        body,
        [
            Connector("eth", "Ethernet / UDP module command link", 0, 58, WIRE["ethernet"]),
        ],
    )


def build_parts() -> dict[str, Part]:
    return {
        "waypoint": make_waypoint_part(),
        "breadboard": make_breadboard_part(),
        "pi": make_pi_part(),
        "pi_power": make_pi_power_part(),
        "led_supply": make_led_supply_part(),
        "epson_power": make_epson_power_part(),
        "printer": make_printer_part(),
        "receipt": make_receipt_part(),
        "speaker": make_usb_speaker_part(),
        "ads1115": make_ads1115_part(),
        "pot": make_pot_part(),
        "button": make_start_button_part(),
        "level": make_level_shifter_part(),
        "ledstrip": make_led_strip_part(),
        "debounce": make_debounce_cap_part(),
        "v5rail": make_rail_part("external_5v_led_rail", "+5V LED rail", WIRE["v5"], "External +5V rail for LED strip and AHCT VCC only"),
        "v3rail": make_rail_part("pi_3v3_logic_rail", "3.3V logic rail", WIRE["v3"], "3.3V logic rail from Raspberry Pi, for ADS1115 and volume pot"),
        "gndrail": make_rail_part("common_logic_gnd_rail", "Common logic GND rail", WIRE["gnd"], "Common GND: Pi, ADC, LED supply, and local controls"),
        "r330": make_resistor_part("resistor_330_led_data", "330-470 ohm LED data resistor", "330-470 ohm"),
        "cap1000": make_capacitor_part("capacitor_1000uf_led", "1000uF capacitor near LED strip", "1000uF", True),
        "modulebus": make_module_bus_part(),
        "mod_simon": make_module_connector_part("simon", "Simon Module"),
        "mod_chop": make_module_connector_part("chop", "Chopping Module"),
        "mod_pan": make_module_connector_part("pan", "Pan Motion Module"),
        "mod_pot_temp": make_module_connector_part("pot_temp", "Pot Temperature Module"),
        "mod_garnish": make_module_connector_part("garnish", "Garnish Placement Module"),
    }


def connector_instance_xml(inst: Instance) -> str:
    chunks = []
    for connector_id, wires in inst.connects.items():
        chunks.append(f'          <connector connectorId="{connector_id}" layer="breadboard"><geometry x="0" y="0"/><connects>')
        for wire_idx, wire_connector in wires:
            chunks.append(f'            <connect connectorId="{wire_connector}" modelIndex="{wire_idx}" layer="breadboardWire"/>')
        chunks.append("          </connects></connector>")
    return "\n".join(chunks)


def instance_xml(inst: Instance, parts: dict[str, Part]) -> str:
    part = parts[inst.part]
    props = "\n".join(f'      <property name="{esc(name)}" value="{esc(value)}"/>' for name, value in inst.props.items())
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
        width: int = 300,
        size: int = 14,
        fill: str = "#fffefa",
        stroke: str = "#d0d7de",
        heading_fill: str = "#1f2933",
    ) -> Instance:
        parts_dynamic[key] = make_label_part(key, lines, width, size, fill, stroke, heading_fill)
        return add(key, key, lines[0], x, y, z=12)

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
        end_x, end_y = abs_pos(b, bc)
        for point_index, (x, y) in enumerate(points):
            if abs(x - last_x) < 0.01 and abs(y - last_y) < 0.01:
                continue
            if abs(x - end_x) < 0.01 and abs(y - end_y) < 0.01:
                continue
            waypoint_key = f"wp_{len(wires)}_{point_index}_{len(inst)}"
            add_waypoint(waypoint_key, x, y)
            wire(prev_key, prev_conn, waypoint_key, "pin", color, f"{title} segment {point_index + 1}", width)
            prev_key, prev_conn = waypoint_key, "pin"
            last_x, last_y = x, y
        wire(prev_key, prev_conn, b, bc, color, title, width)

    def manhattan_wire(
        a: str,
        ac: str,
        b: str,
        bc: str,
        color: str,
        title: str,
        width: float = 8,
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
            'Chef Station "Master Controller / Score + Print Layer"',
            "Pi owns game session, module scoring, cooktop light cue, volume command, and receipt printing",
        ],
        28,
        18,
        1040,
        18,
    )
    add_label(
        "state_machine",
        [
            "Master software state machine",
            "IDLE -> COUNTDOWN -> ACTIVE -> SCORING -> PRINTING -> RESET",
            "Countdown plays beeps and pulses LED strip.",
            "At GO: broadcast START_GAME over Ethernet UDP.",
            "Scores are collated, receipt prints, then reset returns to IDLE.",
        ],
        1110,
        18,
        690,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "pin_summary",
        [
            "Raspberry Pi pin summary",
            "GPIO2 / SDA: ADS1115 SDA",
            "GPIO3 / SCL: ADS1115 SCL",
            "GPIO5: Start Game button active LOW",
            "GPIO18: LED data through AHCT level shifter",
            "Ethernet: module commands and score/status UDP",
            "USB: Epson printer and local speaker",
        ],
        26,
        1000,
        430,
        13,
    )
    add_label(
        "front_edge",
        ["FRONT / OPERATOR CONTROL EDGE", "Start button and master volume are mounted here."],
        560,
        1302,
        650,
        16,
        "#eff6ff",
        "#2563eb",
        "#1d4ed8",
    )
    add_label(
        "volume_callout",
        [
            "Master volume is a software control signal",
            "Pi reads the 10k knob through ADS1115 A0.",
            "Pi broadcasts VOLUME_SET 0-30 over Ethernet UDP.",
            "Modules apply that as a local software volume cap.",
            "It cannot physically limit a module that ignores volume commands.",
        ],
        560,
        1548,
        625,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "led_level_callout",
        [
            "LED data level shifting",
            "Pi GPIO is 3.3V.",
            "74AHCT/74HCT drives reliable 5V WS2812B DIN.",
            "Add 330-470 ohm series resistor before LED DIN.",
        ],
        1210,
        512,
        430,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "led_power_callout",
        [
            "External 5V LED power",
            "LED strip +5V comes from regulated external supply.",
            "1000uF capacitor sits across strip +5V/GND near strip.",
            "Do not route LED current through the Pi ground jumper.",
        ],
        1438,
        68,
        520,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "common_gnd_callout",
        [
            "Common ground",
            "All logic grounds must be common.",
            "Pi GND, LED supply GND, ADS1115 GND,",
            "button GND, LED strip GND, and level-shifter GND tie here.",
        ],
        1210,
        1535,
        630,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "module_network_callout",
        [
            "Ethernet module communication",
            "Master sends START_GAME / RESET_GAME over UDP 42100.",
            "Modules return JSON score/status over the same UDP link.",
            "Use the LS108GP switch/module Ethernet network.",
            "No separate serial adapter, A/B bus, or termination is needed.",
        ],
        1528,
        546,
        500,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "no_sync_callout",
        [
            "No hardware sync terminals",
            "Do not wire START_IN, RESET_IN, or DONE_OUT buses.",
            "The master issues START_GAME, RESET_GAME, FORCE_END,",
            "REQUEST_SCORE, and VOLUME_SET over Ethernet.",
        ],
        2050,
        820,
        505,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "printer_callout",
        [
            "Epson printer connection",
            "Preferred: Pi USB to Epson USB.",
            "Optional: Ethernet if printer model is networked.",
            "Printer uses its manufacturer power supply.",
            "Print with ESC/POS from Raspberry Pi, not ESP32 GPIO.",
        ],
        1970,
        40,
        520,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "speaker_callout",
        [
            "Local controller speaker",
            "Only global 3-2-1-GO and victory jingle play here.",
            "Module speakers remain local and obey VOLUME_SET commands.",
        ],
        30,
        1200,
        430,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "receipt_logo_callout",
        [
            "R + B Grill thermal-printer logo",
            "Preprocess logo to black-and-white before printing.",
            "Use 384 px wide or printer-compatible raster width.",
            "Send with ESC/POS raster image command.",
        ],
        2290,
        724,
        450,
        13,
        "#fffbeb",
        WIRE["note"],
        "#7c2d12",
    )
    add_label(
        "module_messages",
        [
            "Score/status messages over Ethernet UDP 42100",
            '{"module":"simon","event":"complete","score":92}',
            '{"module":"chop","event":"complete","seconds":18.42,"score":85}',
            '{"module":"pan","event":"complete","motion_ms":4200,"score":78}',
            '{"module":"pot_temp","event":"score","percent":73,"score":73}',
            '{"module":"garnish","event":"score","zone":"GOOD","score":80}',
            "Master commands: START_GAME, RESET_GAME, VOLUME_SET,",
            "REQUEST_SCORE, FORCE_END",
        ],
        2050,
        1520,
        700,
        12,
        "#eff6ff",
        WIRE["ethernet"],
        "#1e3a8a",
    )

    add("pi_power", "pi_power", "Official Raspberry Pi power supply", 50, 142)
    add("pi", "pi", "Raspberry Pi master score/print host", 58, 286)
    add("speaker", "speaker", "USB powered local controller speaker", 82, 790)
    add("v5rail", "v5rail", "+5V LED rail", 565, 320, z=2)
    add("v3rail", "v3rail", "3.3V logic rail", 565, 420, z=2)
    add("gndrail", "gndrail", "Common logic ground rail", 565, 1168, z=2)
    add("led_supply", "led_supply", "External regulated 5V LED supply", 1090, 150)
    add("ads", "ads1115", "ADS1115 I2C ADC for master volume", 690, 604)
    add("pot", "pot", "Master Volume 10k linear potentiometer", 605, 1378)
    add("button", "button", "Start Game momentary pushbutton", 905, 1370)
    add("debounce", "debounce", "Optional C1 0.1uF debounce capacitor across Start button", 840, 1388, {"Capacitance": "0.1uF"})
    add("level", "level", "74AHCT125 LED data level shifter", 932, 508)
    add("r_led", "r330", "R1 330-470 ohm LED data resistor", 1250, 560, {"Resistance": "330-470 ohm"})
    add("cap_led", "cap1000", "C2 1000uF electrolytic across LED strip +5V/GND", 1466, 244, {"Capacitance": "1000uF"})
    add("ledstrip", "ledstrip", "Cooktop overhead WS2812B / NeoPixel LED strip", 1580, 220)
    add("modulebus", "modulebus", "Module Ethernet / UDP network", 1565, 682)
    add("mod_simon", "mod_simon", "Simon Module Ethernet connector", 2184, 968)
    add("mod_chop", "mod_chop", "Chopping Module Ethernet connector", 2184, 1068)
    add("mod_pan", "mod_pan", "Pan Motion Module Ethernet connector", 2184, 1168)
    add("mod_pot_temp", "mod_pot_temp", "Pot Temperature Module Ethernet connector", 2184, 1268)
    add("mod_garnish", "mod_garnish", "Garnish Placement Module Ethernet connector", 2184, 1368)
    add("printer", "printer", "Epson TM-T20IV / TM-T20V receipt printer", 1710, 170)
    add("epson_power", "epson_power", "Epson manufacturer printer power supply", 2170, 180)
    add("receipt", "receipt", "R + B Grill score receipt preview", 2240, 280)
    add("breadboard", "breadboard", "Breadboard and terminal block field", 505, 250, z=0)

    # USB and independent power connections.
    manhattan_wire("pi_power", "out", "pi", "pwr_usb", WIRE["usb"], "Official PSU to Raspberry Pi USB-C power input", 9, "hvh", 32)
    manhattan_wire("pi", "usb_audio", "speaker", "usb", WIRE["usb"], "Pi USB to local controller speaker / USB audio", 8, "hvh", 36)
    manhattan_wire("pi", "usb_printer", "printer", "usb", WIRE["usb"], "Pi USB to Epson receipt printer", 8, "vhv", 145)
    manhattan_wire("epson_power", "out", "printer", "pwr", WIRE["usb"], "Epson manufacturer supply powers printer only", 8, "vhv", 305)
    manhattan_wire("pi", "eth_modules", "modulebus", "eth_in", WIRE["ethernet"], "Pi Ethernet to module UDP command/status network", 8, "vhv", 870)

    # Power rails and common ground.
    manhattan_wire("led_supply", "vcc", "v5rail", "tap12", WIRE["v5"], "External regulated +5V supply to LED +5V rail", 11, "hvh", 1330)
    manhattan_wire("led_supply", "gnd", "gndrail", "tap12", WIRE["gnd"], "External LED supply GND to common logic GND rail", 11, "hvh", 1350)
    manhattan_wire("pi", "gnd", "gndrail", "tap0", WIRE["gnd"], "Raspberry Pi GND to common logic GND rail", 10, "hvh", 470)
    manhattan_wire("pi", "pin_3v3", "v3rail", "tap0", WIRE["v3"], "Raspberry Pi 3.3V to local logic rail", 9, "hvh", 490)

    # ADS1115 and volume pot wiring.
    manhattan_wire("v3rail", "tap3", "ads", "vdd", WIRE["v3"], "ADS1115 VDD to Pi 3.3V rail", 8, "hvh", 675)
    manhattan_wire("gndrail", "tap3", "ads", "gnd", WIRE["gnd"], "ADS1115 GND to common rail", 8, "hvh", 700)
    manhattan_wire("pi", "gpio2", "ads", "sda", WIRE["control"], "GPIO2 / SDA to ADS1115 SDA", 8, "hvh", 520)
    manhattan_wire("pi", "gpio3", "ads", "scl", WIRE["control"], "GPIO3 / SCL to ADS1115 SCL", 8, "hvh", 540)
    manhattan_wire("ads", "addr", "gndrail", "tap4", WIRE["gnd"], "ADS1115 ADDR to GND for address 0x48", 7, "hvh", 910)
    manhattan_wire("v3rail", "tap2", "pot", "vcc", WIRE["v3"], "Pot outer lug 1 to 3.3V", 8, "hvh", 640)
    manhattan_wire("pot", "gnd", "gndrail", "tap2", WIRE["gnd"], "Pot outer lug 2 to GND", 8, "hvh", 662)
    manhattan_wire("pot", "wiper", "ads", "a0", WIRE["control"], "Pot wiper to ADS1115 A0", 8, "hvh", 968)

    # Start button and debounce.
    manhattan_wire("pi", "gpio5", "button", "sig", WIRE["control"], "GPIO5 to Start Game button, active LOW", 8, "hvh", 585)
    manhattan_wire("button", "gnd", "gndrail", "tap6", WIRE["gnd"], "Start Game button other side to GND", 8, "hvh", 1020)
    manhattan_wire("debounce", "a", "button", "sig", WIRE["control"], "Optional 0.1uF debounce capacitor signal side", 7, "vhv", 1442)
    manhattan_wire("debounce", "b", "button", "gnd", WIRE["gnd"], "Optional 0.1uF debounce capacitor GND side", 7, "vhv", 1480)

    # LED strip through level shifter.
    manhattan_wire("pi", "gpio18", "level", "a1", WIRE["led"], "GPIO18 LED data to 74AHCT125 input", 8, "hvh", 610)
    manhattan_wire("v5rail", "tap7", "level", "vcc", WIRE["v5"], "74AHCT125 VCC to external +5V rail", 8, "hvh", 1010)
    manhattan_wire("level", "gnd", "gndrail", "tap7", WIRE["gnd"], "74AHCT125 GND to common rail", 8, "hvh", 1032)
    manhattan_wire("level", "oe", "gndrail", "tap8", WIRE["gnd"], "74AHCT125 OE tied to GND to enable output", 7, "hvh", 1055)
    manhattan_wire("level", "y1", "r_led", "a", WIRE["led"], "74AHCT125 output to LED data resistor", 8, "vhv", 600)
    manhattan_wire("r_led", "b", "ledstrip", "din", WIRE["led"], "LED data resistor to strip DIN", 8, "vhv", 610)
    manhattan_wire("v5rail", "tap15", "ledstrip", "vcc", WIRE["v5"], "LED strip +5V to external +5V rail", 10, "hvh", 1498)
    manhattan_wire("gndrail", "tap15", "ledstrip", "gnd", WIRE["gnd"], "LED strip GND to common GND rail", 10, "hvh", 1520)
    manhattan_wire("cap_led", "pos", "ledstrip", "vcc", WIRE["v5"], "C2 positive across LED +5V near strip", 8, "vhv", 280)
    manhattan_wire("cap_led", "neg", "ledstrip", "gnd", WIRE["gnd"], "C2 negative across LED GND near strip", 8, "vhv", 344)

    # Module command/status network. START/RESET/DONE wires are intentionally omitted.
    module_pairs = [
        ("simon", "mod_simon"),
        ("chop", "mod_chop"),
        ("pan", "mod_pan"),
        ("pot_temp", "mod_pot_temp"),
        ("garnish", "mod_garnish"),
    ]
    for bus_key, module_key in module_pairs:
        manhattan_wire(
            "modulebus",
            f"{bus_key}_eth",
            module_key,
            "eth",
            WIRE["ethernet"],
            f"{module_key} Ethernet/UDP branch from module network",
            7,
        )

    keyed = by_key()
    for item in wires:
        keyed[item.a].connects.setdefault(item.ac, []).append((item.idx, "connector0"))
        keyed[item.b].connects.setdefault(item.bc, []).append((item.idx, "connector1"))

    return inst, wires


def write_fzz(parts: dict[str, Part], inst: list[Instance], wires: list[Wire]) -> None:
    all_parts = {**parts, **parts_dynamic}
    keyed = {item.key: item for item in inst}
    fz_instances = "\n".join([wire_xml(item, keyed, all_parts) for item in wires] + [instance_xml(item, all_parts) for item in inst])
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
        zf.writestr("chef_station_master_controller_score_print_editable.fz", fz)
        for part in all_parts.values():
            zf.writestr(part.fzp_name, part.fzp)
            for name, svg_text in part.svg_entries.items():
                zf.writestr(name, svg_text)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Master Controller / Score + Print Layer Wiring Checklist

## Brief Wiring Checklist

- Power the Raspberry Pi from its official USB-C or micro-USB power supply. Do not power the Pi from the breadboard +5V rail.
- Power the Epson TM-T20IV / TM-T20V-family printer from its manufacturer supply. The printer does not power the Raspberry Pi.
- Power the WS2812B / NeoPixel overhead cooktop LED strip from an external regulated +5V supply sized for the LED count.
- Tie all low-voltage logic grounds together for the local controller wiring: Raspberry Pi GND, ADS1115 GND, external LED supply GND, LED strip GND, button GND, and level-shifter GND.
- Do not route high-current LED return current through a delicate Raspberry Pi ground jumper; use proper power distribution for the LED strip.
- Connect Start Game button one side to Raspberry Pi GPIO5 and the other side to GND. Configure GPIO5 with an internal pullup: unpressed = HIGH, pressed = LOW.
- Optionally place a 0.1uF capacitor across the Start Game button terminals, and still use software debounce.
- Wire ADS1115 VDD to Pi 3.3V, GND to common GND, SDA to GPIO2, SCL to GPIO3, ADDR to GND for address 0x48, and A0 to the volume pot wiper.
- Wire the 10k master volume potentiometer outer lugs to 3.3V and GND, with the center wiper to ADS1115 A0.
- Connect Raspberry Pi GPIO18 to a 74AHCT125 or 74HCT245 input. Power the level shifter from +5V and common GND.
- Connect the level-shifter output through a 330-470 ohm resistor to LED strip DIN.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip input. Observe polarity.
- Connect Raspberry Pi USB to the Epson printer USB port, or use Ethernet if the Epson model is networked.
- Connect Raspberry Pi Ethernet to the same module Ethernet network/switch as the ESP32-P4 boards.
- Do not wire separate START_SYNC, RESET_SYNC, DONE_OUT, or serial A/B terminals for game commands.
- Configure the master software to send `START_GAME`, `RESET_GAME`, `FORCE_END`, `REQUEST_SCORE`, and `VOLUME_SET` over UDP port 42100.
- Connect a USB powered speaker or USB audio dongle to the Raspberry Pi for global countdown and victory audio.

## Pin Assignment Table

| Raspberry Pi pin | Signal | Destination | Notes |
|---|---|---|---|
| GPIO2 / SDA | I2C SDA | ADS1115 SDA | Volume ADC bus |
| GPIO3 / SCL | I2C SCL | ADS1115 SCL | Volume ADC bus |
| GPIO5 | START_BUTTON | Start Game button to GND | Internal pullup; active LOW |
| GPIO18 | LED_DATA_3V3 | 74AHCT125 input | Level shifted before LED strip |
| Ethernet | MODULE_NET | LS108GP / module network | UDP port 42100 command/status link |
| 3.3V | PI_3V3_LOGIC | ADS1115 VDD and pot outer lug | Do not use for LED strip |
| GND | COMMON_GND | Logic ground rail | Must be common with shared signals |
| USB | PRINTER_USB | Epson receipt printer | Preferred printer connection |
| USB/audio | CONTROLLER_AUDIO | USB speaker or audio dongle | Global beeps/jingle only |

## Module Network Connector Table

| Module connector terminal | Wire color | Connects to | Required? | Notes |
|---|---|---|---|---|
| Ethernet / UDP | Blue | LS108GP switch and ESP32-P4 Ethernet ports | Yes | UDP port 42100 carries commands and score/status messages |
| Local accessory GND | Black | Shown on each station diagram | As needed | Common ground is still required where GPIO/data crosses local accessory power domains |

Connected branches shown:

| Branch | Expected module behavior |
|---|---|
| Simon Module | Reports complete/score events over Ethernet UDP |
| Chopping Module | Reports completion time and normalized score |
| Pan Motion Module | Reports motion timing and normalized score |
| Pot Temperature Module | Reports percent-in-zone and score |
| Garnish Placement Module | Reports zone result and score |

## Receipt-Printing Architecture Notes

- Raspberry Pi is the master score/print host because Epson receipt printers are easiest to control from Linux over USB or Ethernet using ESC/POS.
- Do not wire a USB-only Epson printer directly to ESP32 GPIO.
- Preprocess the fictional `R + B Grill` logo as a monochrome bitmap, about 384 px wide or the printer-compatible width for the model.
- Print the logo with an ESC/POS raster image command, then print concise text fields so the receipt is fast and theatrical.
- Print player total score, itemized module scores, a result line, a thank-you line, and cut paper if the printer supports it.
- If a module fails to report before timeout, print `NO REPORT` for that module and either average only valid scores or assign 0, depending on operator preference.
- Keep a cached last receipt so the operator can reprint after a paper jam or dramatic flourish failure.

Example receipt:

```text
R + B GRILL
[graphic logo]

CHEF SCORE RECEIPT

TOTAL SCORE: 084 / 100

Simon:        092
Chop Speed:   085
Pan Motion:   078
Pot Temp:     073
Garnish:      080

Result:
LINE COOK LEGEND

Thank you for dining
at R + B Grill
```

## Module Data Behavior

Modules send score/status JSON lines or compact messages over Ethernet UDP port 42100:

```text
{"module":"simon","event":"complete","score":92}
{"module":"chop","event":"complete","seconds":18.42,"score":85}
{"module":"pan","event":"complete","motion_ms":4200,"score":78}
{"module":"pot_temp","event":"score","percent":73,"score":73}
{"module":"garnish","event":"score","zone":"GOOD","score":80}
```

Master sends commands:

```text
START_GAME
RESET_GAME
VOLUME_SET 0-30
REQUEST_SCORE
FORCE_END
```

## Controller Software Notes

- IDLE: LED strip off or dim warm glow; wait for Start Game button; optionally poll modules for READY.
- COUNTDOWN: play 3-2-1-GO beeps on controller speaker and pulse overhead LED strip.
- At GO: broadcast Ethernet UDP `START_GAME`.
- ACTIVE: record `masterStartTime`, keep overhead LED strip on, read master volume knob repeatedly, broadcast `VOLUME_SET` only when changed, collect score/progress events.
- SCORING: send `FORCE_END` or `REQUEST_SCORE`, wait with timeout, compute itemized breakdown and total score, play victory jingle, run LED victory flourish.
- PRINTING: send ESC/POS print job to Epson: logo, total score, module breakdown, result line, thank-you line, and cut command when supported.
- RESET: broadcast Ethernet UDP `RESET_GAME`, clear score state, return to IDLE.
- Operator override options should include force start, force end, reprint last receipt, mute all, and reset all.

## Callout Notes

- Common ground: all shared logic grounds must be common.
- USB/Ethernet Epson printer connection: use Pi USB by default, Ethernet only for networked models.
- Ethernet module communication: UDP port 42100 carries module commands and score/status events.
- No hardware sync terminals: START/RESET/DONE wires are intentionally omitted.
- Master volume: the knob is a software volume cap signal, not an analog audio bus.
- External 5V LED power: LED strip current comes from the external regulated supply.
- LED data level shifting: use 74AHCT/74HCT for reliable 5V WS2812B data.
- Local controller speaker: only global countdown and victory sounds play here.
- R + B Grill thermal-printer logo: use a preprocessed monochrome raster logo.

## Assumptions And Substitutions

- Diagram chooses Raspberry Pi as the required master score/print host and draws a Pi 4/5/Zero 2 W-compatible 40-pin host helper part.
- ADS1115 is chosen for the volume ADC path. MCP3008 would also work but would use SPI pins and different wiring.
- Printer connection is drawn as USB preferred, with Ethernet noted as an option for networked Epson models.
- All visual parts are custom editable Fritzing helper parts embedded in the `.fzz`; no third-party parts were downloaded.
- The helper art is not a mechanical footprint for fabrication. It is a clean Fritzing-style wiring layout for build communication.
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
            "--window-size=2920,2000",
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
