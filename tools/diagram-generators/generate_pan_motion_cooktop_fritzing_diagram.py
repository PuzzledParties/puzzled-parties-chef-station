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
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "pan-motion-cooktop"
FZZ_PATH = OUT_DIR / "chef_station_pan_motion_cooktop_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_pan_motion_cooktop_wiring_diagram.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_pan_motion_cooktop.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")


WIRE = {
    "vplus": "#f59e0b",
    "gnd": "#111111",
    "hall_vcc": "#7c3aed",
    "ethernet": "#1e88e5",
    "hall1": "#f4b400",
    "hall2": "#f57c00",
    "led_data": "#178f46",
    "serial": "#7e3fb2",
    "speaker_a": "#2563eb",
    "speaker_b": "#64748b",
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


def read_esp32_part() -> Part:
    s = 72 / 1000
    raw = {
        "connector0": (1054.542, 1637.4242),   # 3V3
        "connector1": (1054.7252, 1537.4241),  # GND
        "connector5": (1054.542, 1137.424),    # GPIO27 / UART2 RX
        "connector6": (1054.542, 1037.424),    # GPIO26 / UART2 TX
        "connector14": (1054.542, 237.16118),  # GPIO23
        "connector16": (55.833435, 337.42172), # GPIO20 / ADC1_CH4
        "connector17": (54.500019, 437.4238),  # GPIO21 / ADC1_CH5
        "connector28": (54.500015, 1537.4241), # GND
    }
    pins = {connector: (x * s, y * s) for connector, (x, y) in raw.items()}
    labels = {
        "connector0": "3V3 Hall rail",
        "connector1": "GND",
        "connector5": "GPIO27 / DF TX",
        "connector6": "GPIO26 / DF RX",
        "connector14": "GPIO23 / LED DATA",
        "connector16": "GPIO20 / HALL1 AO",
        "connector17": "GPIO21 / HALL2 AO",
        "connector28": "GND",
    }
    return make_protocol_esp32_poe_part(
        custom_part=custom_part,
        connector_cls=Connector,
        key="waveshare_esp32_poe_eth",
        title="Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH",
        pins=pins,
        labels=labels,
        wire=WIRE,
        family="Chef Station Pan Motion Cooktop",
        extra_note="LED data/serial only; LEDs/audio use external 5V rails.",
    )


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
    module_id = f"chef_pan_{key}"

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
  <tags><tag>chef station</tag><tag>pan motion</tag><tag>cooktop</tag><tag>esp32</tag></tags>
  <properties>
    <property name="family">Chef Station Pan Motion Cooktop</property>
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


def make_label_part(key: str, lines: list[str], width: int = 280, size: int = 14) -> Part:
    height = max(36, 18 + len(lines) * (size + 5))
    body = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="5" '
        f'fill="#fffefa" stroke="#d0d7de" stroke-width="1.2"/>'
    ]
    y = 19
    for index, line in enumerate(lines):
        body.append(text(9, y, line, size, "#1f2933", 700 if index == 0 else 500))
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


def make_ceramic_cap_part() -> Part:
    body = (
        '<line x1="12" y1="74" x2="12" y2="44" stroke="#4b5563" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="72" y1="74" x2="72" y2="44" stroke="#4b5563" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M19 44 C19 15 65 15 65 44 Z" fill="#f59e0b" stroke="#92400e" stroke-width="2"/>'
        + text(42, 34, "0.1uF", 13, "#1f2933", 700, "middle")
        + text(42, 91, "near Hall", 12, "#1f2933", 600, "middle")
    )
    return custom_part(
        "cap_0_1uf",
        "0.1uF Hall decoupling capacitor",
        "C",
        84,
        102,
        body,
        [Connector("neg", "GND side", 12, 74), Connector("pos", "3.3V side", 72, 74)],
        properties={"Capacitance": "0.1uF"},
    )


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 19) -> Part:
    width = 1010
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
    for x in range(42, 900, 24):
        for y in range(120, 890, 24):
            holes.append(f'<circle cx="{x}" cy="{y}" r="2.0" fill="#d9d2c3"/>')
    body = (
        '<rect x="0" y="0" width="1040" height="970" rx="10" fill="#f1ead7" stroke="#d8ccb0" stroke-width="2"/>'
        + text(24, 36, "Manhattan breadboard / power distribution", 23, "#52606d", 700)
        + text(24, 65, "Power rails stay horizontal; component branches use 90-degree routes", 15, "#52606d", 500)
        + "".join(holes)
    )
    return custom_part("breadboard_backplane", "Breadboard and power rails area", "BB", 1040, 970, body)


def make_supply_part() -> Part:
    body = (
        '<rect x="0" y="0" width="260" height="135" rx="8" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(16, 25, "Named 5V rail input", 18, "#1f2933", 700)
        + text(16, 49, "from master rails", 20, WIRE["vplus"], 700)
        + text(16, 80, "+ to matching local rail", 14, "#1f2933", 600)
        + text(16, 102, "- to COMMON_GND", 14, "#1f2933", 600)
        + text(212, 52, "+5V", 13, WIRE["vplus"], 700, "end")
        + text(212, 97, "GND", 13, WIRE["gnd"], 700, "end")
    )
    return custom_part(
        "external_5v_supply",
        "Named 5V accessory rail input",
        "5V IN",
        260,
        135,
        body,
        [Connector("vcc", "+5V rail input", 236, 48), Connector("gnd", "COMMON_GND", 236, 94)],
    )


def make_hall_sensor_part(key: str, title: str) -> Part:
    body = (
        '<rect x="0" y="0" width="220" height="132" rx="8" fill="#eef2ff" stroke="#7c3aed" stroke-width="2"/>'
        '<rect x="128" y="31" width="58" height="62" rx="8" fill="#1f2937" stroke="#111827" stroke-width="2"/>'
        '<circle cx="157" cy="62" r="12" fill="#374151" stroke="#9ca3af" stroke-width="1.5"/>'
        + text(24, 34, "VCC 3.3V", 13, WIRE["hall_vcc"], 700)
        + text(24, 66, "AO analog", 13, "#92400e", 700)
        + text(24, 98, "GND", 13, WIRE["gnd"], 700)
        + text(110, 24, title, 18, "#1f2933", 700, "middle")
        + text(110, 117, "SS49E / OH49E / 49E", 13, "#1f2933", 600, "middle")
    )
    return custom_part(
        key,
        f"{title} analog linear Hall sensor",
        "HALL",
        220,
        132,
        body,
        [
            Connector("vcc", "3.3V VCC", 18, 31),
            Connector("out", "AO analog output", 18, 63),
            Connector("gnd", "GND", 18, 95),
        ],
        properties={"sensor": "Analog linear Hall sensor, use AO not DO"},
    )


def make_rgb_coil_part() -> Part:
    coils = []
    for r, color, width in [(132, "#b91c1c", 12), (104, "#ef4444", 10), (76, "#f97316", 9), (48, "#fb923c", 8)]:
        coils.append(f'<circle cx="200" cy="190" r="{r}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    leds = []
    for index in range(18):
        angle = index * 20
        leds.append(
            f'<circle cx="{200 + 122 * __import__("math").cos(__import__("math").radians(angle)):.1f}" '
            f'cy="{190 + 122 * __import__("math").sin(__import__("math").radians(angle)):.1f}" '
            f'r="6" fill="#fed7aa" stroke="#f97316" stroke-width="1"/>'
        )
    body = (
        '<rect x="0" y="0" width="410" height="390" rx="12" fill="#20242a" stroke="#111827" stroke-width="2"/>'
        + "".join(coils)
        + "".join(leds)
        + text(22, 35, "+5V", 13, "#ffffff", 700)
        + text(22, 73, "DIN", 13, "#ffffff", 700)
        + text(22, 111, "GND", 13, "#ffffff", 700)
        + text(205, 352, "Cooktop coil RGB strip", 18, "#ffffff", 700, "middle")
        + text(205, 374, "+5V / DIN / GND, WS2812B style", 12, "#ffffff", 500, "middle")
    )
    return custom_part(
        "rgb_coil_strip",
        "Cooktop coil RGB strip: +5V / DIN / GND",
        "LED",
        410,
        390,
        body,
        [
            Connector("vcc", "LED strip +5V", 20, 31),
            Connector("din", "LED strip DIN", 20, 69),
            Connector("gnd", "LED strip GND", 20, 107),
        ],
    )


def make_cooktop_part() -> Part:
    optional = (
        '<circle cx="370" cy="145" r="18" fill="#ffffff" fill-opacity="0.35" stroke="#64748b" stroke-dasharray="4 4"/>'
        '<circle cx="265" cy="330" r="18" fill="#ffffff" fill-opacity="0.35" stroke="#64748b" stroke-dasharray="4 4"/>'
        '<circle cx="475" cy="330" r="18" fill="#ffffff" fill-opacity="0.35" stroke="#64748b" stroke-dasharray="4 4"/>'
    )
    body = (
        '<rect x="0" y="0" width="740" height="660" rx="14" fill="#e5e7eb" fill-opacity="0.45" stroke="#64748b" stroke-width="2"/>'
        + text(24, 34, "Fake cooktop surface", 24, "#1f2933", 700)
        + text(24, 62, "Thin non-metallic top over Hall sensors", 15, "#1f2933", 600)
        + '<circle cx="370" cy="310" r="235" fill="#f8fafc" fill-opacity="0.24" stroke="#111827" stroke-width="3"/>'
        + '<circle cx="370" cy="310" r="190" fill="none" stroke="#94a3b8" stroke-width="4"/>'
        + '<circle cx="370" cy="310" r="154" fill="none" stroke="#cbd5e1" stroke-width="3"/>'
        + '<circle cx="370" cy="310" r="103" fill="none" stroke="#e2e8f0" stroke-width="3"/>'
        + '<circle cx="370" cy="310" r="246" fill="none" stroke="#334155" stroke-dasharray="8 8" stroke-width="2"/>'
        + text(370, 96, "8-inch pan/burner area", 16, "#1f2933", 700, "middle")
        + '<circle cx="370" cy="310" r="205" fill="#d1d5db" fill-opacity="0.32" stroke="#475569" stroke-width="2"/>'
        + '<rect x="435" y="238" width="66" height="28" rx="6" fill="#7f1d1d" stroke="#450a0a" stroke-width="2"/>'
        + text(468, 232, "magnet", 12, "#450a0a", 700, "middle")
        + text(525, 256, "offset 1.5-2.5 in", 13, "#450a0a", 700)
        + optional
        + text(370, 602, "HALL 1 left and HALL 2 right, spaced about 2.5-3.5 in", 15, "#1f2933", 700, "middle")
        + text(370, 627, "Target magnet-to-sensor gap: 1/4-1/2 in; avoid stainless or thick metal", 13, "#1f2933", 600, "middle")
    )
    return custom_part("cooktop_physical_layout", "Cooktop physical layout", "TOP", 740, 660, body)


def build_parts() -> dict[str, Part]:
    return {
        "esp32": read_esp32_part(),
        "dfplayer": read_stock_part(
            "dfplayer",
            PARTS / "core" / "DFRobot-DFPlayer-Mini.fzp",
            {
                "connector0": (3.6, 3.6),   # VCC
                "connector1": (3.6, 10.8),  # RX
                "connector2": (3.6, 18.0),  # TX
                "connector5": (3.6, 39.6),  # SPK1
                "connector6": (3.6, 46.8),  # GND
                "connector7": (3.6, 54.0),  # SPK2
                "connector9": (54.0, 46.8), # GND
            },
        ),
        "speaker": read_stock_part(
            "speaker",
            PARTS / "core" / "loudspeaker.fzp",
            {"connector0": (36.073, 110.255), "connector1": (43.301, 110.255)},
        ),
        "cap1000": uniquify_svg_entries(
            read_stock_part(
                "cap1000",
                PARTS / "obsolete" / "electrolytic_capacitor_1000uF.fzp",
                {"connector0": (20.64, 97.26), "connector1": (30.64, 97.26)},
            )
        ),
        "cap470": uniquify_svg_entries(
            read_stock_part(
                "cap470",
                PARTS / "obsolete" / "electrolytic_capacitor_470uF.fzp",
                {"connector0": (14.73, 82.15), "connector1": (24.73, 82.15)},
            )
        ),
        "r1k": make_resistor_part("resistor_1k_series", "1k series resistor", "1k", ["#6b4f1d", "#111111", "#d71920", "#c49a23"]),
        "r330": make_resistor_part("resistor_330_data", "330-470 ohm LED data resistor", "330 ohm", ["#f57c00", "#f57c00", "#6b4f1d", "#c49a23"]),
        "cap01": make_ceramic_cap_part(),
        "breadboard": make_breadboard_part(),
        "supply": make_supply_part(),
        "vrail": make_rail_part("local_5v_led_rail", "5V_LED rail", WIRE["vplus"], "5V_LED from master power: RGB/cooktop LED strip only"),
        "audiorail": make_rail_part("local_5v_audio_servo_rail", "5V_AUDIO_SERVO rail", WIRE["vplus"], "5V_AUDIO_SERVO from master power: DFPlayer/audio only"),
        "v3rail": make_rail_part("esp32_3v3_hall_rail", "ESP32 3.3V Hall rail", WIRE["hall_vcc"], "Hall sensors only: 3.3V from ESP32 3V3 pin"),
        "gndrail": make_rail_part("common_ground_rail", "COMMON_GND rail", WIRE["gnd"], "COMMON_GND: ESP32 + 5V_LED + 5V_AUDIO_SERVO + RGB strip + DFPlayer + Hall sensors"),
        "hall1": make_hall_sensor_part("hall_sensor_1", "HALL 1"),
        "hall2": make_hall_sensor_part("hall_sensor_2", "HALL 2"),
        "coil": make_rgb_coil_part(),
        "cooktop": make_cooktop_part(),
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

    def add_label(key: str, lines: list[str], x: float, y: float, width: int = 280, size: int = 14) -> Instance:
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
            'Chef Station "Pan Motion / Cooktop" wiring',
            "Waveshare ESP32-P4 PoE controller, analog Hall sensors, RGB coil, separately powered audio",
        ],
        28,
        18,
        760,
        18,
    )
    add_label(
        "pin_table",
        [
            "Pin assignment summary",
            "GPIO20 / ADC1_CH4: HALL 1 AO",
            "GPIO21 / ADC1_CH5: HALL 2 AO",
            "GPIO23: Cooktop RGB strip data",
            "GPIO26 / UART2 TX: ESP32 TX to DFPlayer RX through 1k",
            "GPIO27 / UART2 RX: ESP32 RX from DFPlayer TX",
        ],
        28,
        105,
        460,
        13,
    )
    add_label(
        "controller_note",
        [
            "Controller note",
            "ESP32 is powered/networked by PoE from LS108GP.",
            "PoE powers the controller only.",
            "ESP32-P4 ADC1 pins on this header are GPIO16-GPIO23.",
            "Do not feed external +5V into ESP32 3V3.",
        ],
        28,
        252,
        430,
        13,
    )
    add_label(
        "power_callout",
        [
            "Power callouts",
            "COMMON_GND is required for shared data/control.",
            "LED strip uses 5V_LED.",
            "DFPlayer/audio uses 5V_AUDIO_SERVO.",
            "Hall sensors use ESP32 3.3V only.",
            "Do not tie 5V_LED and 5V_AUDIO_SERVO positives together.",
        ],
        28,
        1085,
        500,
        13,
    )
    add_label(
        "rail_names",
        [
            "Rail labels",
            "5V_LED rail: cooktop RGB strip only",
            "5V_AUDIO_SERVO rail: DFPlayer/audio only",
            "3.3V rail: ESP32 3V3 for Hall sensors only",
            "COMMON_GND rail: all signal references",
        ],
        720,
        142,
        440,
        13,
    )
    add_label(
        "hall_notes",
        [
            "Hall sensing notes",
            "Use AO analog output, not DO.",
            "Do not use digital-only A3144 / KY-003 sensors.",
            "motionScore = abs(H1_now - H1_last) + abs(H2_now - H2_last)",
            "Pan present = readings differ from no-pan baseline.",
            "V1 detects motion, not exact pan position.",
        ],
        1398,
        42,
        590,
        13,
    )
    add_label(
        "minimum_hall_note",
        [
            "Minimum viable Hall layout",
            "V1 uses two analog Hall sensors under the burner.",
            "Optional expansion: add HALL 3-5 if pan motion is unreliable.",
            "Place HALL 1 left of center and HALL 2 right of center.",
        ],
        1660,
        720,
        500,
        13,
    )
    add_label(
        "firmware_notes",
        [
            "Firmware behavior",
            "At boot or round start, sample no-pan baseline.",
            "Sample Hall sensors around 30-100 Hz.",
            "Repeated motionScore above threshold = pan moving.",
            "Pan present but low motionScore = stationary.",
            "Stationary pan increases sizzle/burning volume.",
            "RGB coil reacts immediately to presence and movement.",
            "Use forgiving thresholds; no precision gesture tracking.",
        ],
        560,
        1085,
        560,
        13,
    )
    add_label(
        "audio_notes",
        [
            "DFPlayer audio behavior",
            "microSD track 001: low/normal sizzle loop.",
            "microSD track 002: burning/crackle loop.",
            "ESP32 controls volume over serial.",
            "Pan present + moving: sizzle low/medium.",
            "Pan present + stationary: ramp volume or switch to burn.",
            "Pan absent: stop or reduce audio.",
            "Audio is local and immediate; monitor not required.",
        ],
        1425,
        1045,
        560,
        13,
    )
    add_label(
        "speaker_note",
        [
            "Speaker connection",
            "Speaker connects only to DFPlayer SPK1 and SPK2.",
            "Do not connect either speaker terminal to GND.",
        ],
        1718,
        920,
        410,
        13,
    )
    add_label(
        "led_note",
        [
            "RGB coil note",
            "Set LEDs red/orange in firmware.",
            "Brighten/react when pan is present and moving.",
            "Put 1000uF capacitor near strip +5V/GND.",
        ],
        1352,
        705,
        300,
        13,
    )

    add("esp", "esp32", "Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH", 92, 338)
    add("breadboard", "breadboard", "Manhattan breadboard and rails area", 315, 94, z=30)
    add("supply_led", "supply", "5V_LED input from master power rails", 410, 70)
    add("supply_audio", "supply", "5V_AUDIO_SERVO input from master power rails", 410, 404)
    add("vrail", "vrail", "5V_LED local rail", 430, 152)
    add("v3rail", "v3rail", "ESP32 3.3V Hall rail", 430, 242)
    add("audiorail", "audiorail", "5V_AUDIO_SERVO local rail", 430, 332)
    add("gndrail", "gndrail", "COMMON_GND rail", 430, 1006)

    add("r_led", "r330", "R3 330 ohm LED data resistor (330-470 ohm OK)", 820, 326, {"Resistance": "330 ohm"})
    add("r_h1", "r1k", "R1 1k HALL 1 AO series resistor", 990, 448, {"Resistance": "1k"})
    add("r_h2", "r1k", "R2 1k HALL 2 AO series resistor", 990, 528, {"Resistance": "1k"})
    add("r_df", "r1k", "R4 1k ESP32 TX to DFPlayer RX", 895, 835, {"Resistance": "1k"})
    add_label(
        "resistor_labels",
        [
            "Series resistors",
            "R1/R2: optional 1k Hall AO protection.",
            "R3: 330-470 ohm LED DIN resistor.",
            "R4: 1k on ESP32 TX -> DFPlayer RX.",
        ],
        800,
        250,
        390,
        13,
    )

    add("cooktop", "cooktop", "Fake cooktop and pan physical layout", 1320, 170, z=30)
    add("coil", "coil", "Cooktop coil RGB strip: +5V / DIN / GND", 1482, 272, z=3)
    add("hall1", "hall1", "HALL 1 analog Hall sensor left of burner center", 1390, 574, z=7)
    add("hall2", "hall2", "HALL 2 analog Hall sensor right of burner center", 1670, 574, z=7)
    add("cap_h1", "cap01", "C1 0.1uF near HALL 1", 1458, 705, {"Capacitance": "0.1uF"}, z=8)
    add("cap_h2", "cap01", "C2 0.1uF near HALL 2", 1738, 705, {"Capacitance": "0.1uF"}, z=8)

    add("c_led", "cap1000", "C3 1000uF electrolytic near RGB strip", 1408, 255, {"Capacitance": "1000uF"}, z=7)
    add("dfplayer", "dfplayer", "DFPlayer Mini with microSD card", 1426, 852, z=7)
    add("c_df", "cap470", "C4 470uF-1000uF electrolytic near DFPlayer", 1328, 856, {"Capacitance": "470uF-1000uF"}, z=7)
    add("speaker", "speaker", "4 or 8 ohm speaker, 2-3W", 1732, 796, z=7)
    add_label(
        "dfplayer_label",
        [
            "DFPlayer Mini",
            "VCC: 5V_AUDIO_SERVO",
            "RX: from GPIO26 through 1k",
            "TX: to GPIO27",
            "SPK1/SPK2: floating speaker pair",
        ],
        1390,
        760,
        320,
        12,
    )

    # Main power rails.
    manhattan_wire("supply_led", "vcc", "vrail", "tap0", WIRE["vplus"], "5V_LED input to 5V_LED rail", 11, "vhv", 138)
    manhattan_wire("supply_led", "gnd", "gndrail", "tap0", WIRE["gnd"], "5V_LED return to COMMON_GND rail", 11, "hvh", 665)
    manhattan_wire("supply_audio", "vcc", "audiorail", "tap0", WIRE["vplus"], "5V_AUDIO_SERVO input to audio rail", 11, "vhv", 318)
    manhattan_wire("supply_audio", "gnd", "gndrail", "tap2", WIRE["gnd"], "5V_AUDIO_SERVO return to COMMON_GND rail", 11, "hvh", 700)
    manhattan_wire("esp", "connector1", "gndrail", "tap1", WIRE["gnd"], "ESP32 GND reference to COMMON_GND rail", 10, "hvh", 250)
    manhattan_wire("esp", "connector0", "v3rail", "tap0", WIRE["hall_vcc"], "ESP32 3V3 to Hall 3.3V rail", 9, "hvh", 278)

    # Hall sensor power and local decoupling.
    manhattan_wire("v3rail", "tap10", "hall1", "vcc", WIRE["hall_vcc"], "3.3V rail to HALL 1 VCC", 9, "hvh", 1290)
    manhattan_wire("gndrail", "tap10", "hall1", "gnd", WIRE["gnd"], "HALL 1 GND to common rail", 9, "hvh", 1308)
    manhattan_wire("v3rail", "tap14", "hall2", "vcc", WIRE["hall_vcc"], "3.3V rail to HALL 2 VCC", 9, "hvh", 1590)
    manhattan_wire("gndrail", "tap14", "hall2", "gnd", WIRE["gnd"], "HALL 2 GND to common rail", 9, "hvh", 1610)
    manhattan_wire("cap_h1", "pos", "hall1", "vcc", WIRE["hall_vcc"], "C1 0.1uF positive to HALL 1 VCC", 7, "vh", None)
    manhattan_wire("cap_h1", "neg", "hall1", "gnd", WIRE["gnd"], "C1 0.1uF negative to HALL 1 GND", 7, "vh", None)
    manhattan_wire("cap_h2", "pos", "hall2", "vcc", WIRE["hall_vcc"], "C2 0.1uF positive to HALL 2 VCC", 7, "vh", None)
    manhattan_wire("cap_h2", "neg", "hall2", "gnd", WIRE["gnd"], "C2 0.1uF negative to HALL 2 GND", 7, "vh", None)

    # Hall analog signal paths.
    manhattan_wire("hall1", "out", "r_h1", "connector1", WIRE["hall1"], "HALL 1 AO to 1k series resistor", 9, "vhv", 637)
    manhattan_wire("r_h1", "connector0", "esp", "connector16", WIRE["hall1"], "R1 to GPIO20 / ADC1_CH4", 9, "vhv", 410)
    manhattan_wire("hall2", "out", "r_h2", "connector1", WIRE["hall2"], "HALL 2 AO to 1k series resistor", 9, "vhv", 657)
    manhattan_wire("r_h2", "connector0", "esp", "connector17", WIRE["hall2"], "R2 to GPIO21 / ADC1_CH5", 9, "vhv", 500)

    # RGB cooktop coil.
    manhattan_wire("vrail", "tap17", "coil", "vcc", WIRE["vplus"], "RGB strip +5V to 5V_LED rail", 10, "hvh", 1392)
    manhattan_wire("gndrail", "tap17", "coil", "gnd", WIRE["gnd"], "RGB strip GND to COMMON_GND rail", 10, "hvh", 1410)
    manhattan_wire("esp", "connector14", "r_led", "connector0", WIRE["led_data"], "GPIO23 to LED data resistor", 9, "vhv", 320)
    manhattan_wire("r_led", "connector1", "coil", "din", WIRE["led_data"], "LED data resistor to strip DIN", 9, "vhv", 350)
    manhattan_wire("c_led", "connector1", "coil", "vcc", WIRE["vplus"], "C3 positive across RGB strip +5V", 8, "hvh", 1465)
    manhattan_wire("c_led", "connector0", "coil", "gnd", WIRE["gnd"], "C3 negative across RGB strip GND", 8, "hvh", 1450)

    # DFPlayer power, serial, and speaker.
    manhattan_wire("audiorail", "tap15", "dfplayer", "connector0", WIRE["vplus"], "DFPlayer VCC to 5V_AUDIO_SERVO rail", 10, "hvh", 1258)
    manhattan_wire("gndrail", "tap15", "dfplayer", "connector6", WIRE["gnd"], "DFPlayer GND to COMMON_GND rail", 10, "hvh", 1276)
    manhattan_wire("c_df", "connector1", "dfplayer", "connector0", WIRE["vplus"], "C4 positive across DFPlayer +5V", 8, "hvh", 1380)
    manhattan_wire("c_df", "connector0", "dfplayer", "connector6", WIRE["gnd"], "C4 negative across DFPlayer GND", 8, "hvh", 1366)
    manhattan_wire("esp", "connector6", "r_df", "connector0", WIRE["serial"], "GPIO26 / UART2 TX to 1k DFPlayer RX resistor", 9, "hvh", 740)
    manhattan_wire("r_df", "connector1", "dfplayer", "connector1", WIRE["serial"], "1k resistor to DFPlayer RX", 9, "vhv", 852)
    manhattan_wire("esp", "connector5", "dfplayer", "connector2", WIRE["serial"], "GPIO27 / UART2 RX from DFPlayer TX", 9, "hvh", 705)
    manhattan_wire("dfplayer", "connector5", "speaker", "connector1", WIRE["speaker_a"], "DFPlayer SPK1 to speaker +", 9, "vhv", 920)
    manhattan_wire("dfplayer", "connector7", "speaker", "connector0", WIRE["speaker_b"], "DFPlayer SPK2 to speaker -", 9, "vhv", 950)

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
        zf.writestr("chef_station_pan_motion_cooktop_editable.fz", fz)
        for part in all_parts.values():
            zf.writestr(part.fzp_name, part.fzp)
            for name, text_value in part.svg_entries.items():
                zf.writestr(name, text_value)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Pan Motion / Cooktop Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO20 / ADC1_CH4 | HALL 1 analog output through optional 1k series resistor |
| GPIO21 / ADC1_CH5 | HALL 2 analog output through optional 1k series resistor |
| GPIO23 | Cooktop RGB LED strip data through 330-470 ohm resistor |
| GPIO26 / UART2 TX | ESP32 TX to DFPlayer RX through 1k resistor |
| GPIO27 / UART2 RX | ESP32 RX from DFPlayer TX |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power LED strips, DFPlayer/audio, or speakers from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the cooktop RGB strip only.
- `5V_AUDIO_SERVO` positive from the master power distribution goes to the local audio rail for DFPlayer/audio only.
- Both 5V rail returns connect to `COMMON_GND`; do not tie the two 5V positives together.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data, serial, or Hall signals cross power domains.
- Hall sensor VCC pins connect to ESP32 3.3V only, not external +5V.
- Do not feed external +5V into the ESP32 `3V3` pin.
- HALL 1 `AO` connects through an optional 1k series resistor to GPIO20 / ADC1_CH4.
- HALL 2 `AO` connects through an optional 1k series resistor to GPIO21 / ADC1_CH5.
- Use analog Hall sensors such as SS49E, OH49E, or 49E. KY-024 modules are acceptable only when using `AO`.
- Do not use digital-only A3144 / KY-003 sensors for motion scoring.
- Add a 0.1uF capacitor between VCC and GND near each Hall sensor.
- RGB strip `+5V` connects to the `5V_LED` rail.
- RGB strip `GND` connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to RGB strip `DIN`.
- Place a 1000uF electrolytic capacitor across RGB strip +5V and GND near the strip.
- DFPlayer `VCC` connects to the `5V_AUDIO_SERVO` rail.
- DFPlayer `GND` connects to `COMMON_GND`.
- ESP32 GPIO26 / UART2 TX connects through a 1k resistor to DFPlayer `RX`.
- ESP32 GPIO27 / UART2 RX connects directly to DFPlayer `TX`.
- Optional 470uF-1000uF capacitor goes across DFPlayer +5V and GND near the module.
- Speaker connects only to DFPlayer `SPK1` and `SPK2`.
- Do not connect either speaker terminal to GND.
- All grounds must be common where signals cross rails: ESP32, 5V_LED return, 5V_AUDIO_SERVO return, RGB strip, DFPlayer, and Hall sensors.

## Physical Cooktop Checklist

- Mount HALL 1 slightly left of burner center.
- Mount HALL 2 slightly right of burner center.
- Space HALL 1 and HALL 2 about 2.5-3.5 inches apart.
- Keep both Hall sensors under the fake cooktop within the 8-inch pan/burner area.
- Magnet should be hidden in the underside of the pan and offset about 1.5-2.5 inches from pan center.
- Target normal magnet-to-sensor gap is 1/4-1/2 inch.
- Use a thin non-metallic cooktop surface.
- Do not place Hall sensors under a stainless table or thick metal sheet.
- Optional expansion: add HALL 3-5 only if testing shows unreliable motion or dead zones; V1 uses two sensors.

## Firmware Behavior Notes

- At boot or round start, sample a no-pan baseline for both Hall sensors.
- Determine pan present by comparing current readings to the no-pan baseline.
- Sample Hall sensors repeatedly around 30-100 Hz.
- Calculate `motionScore = abs(H1_now - H1_last) + abs(H2_now - H2_last)`.
- Repeated changes above threshold count as pan moving.
- Pan present with motionScore below threshold counts as stationary.
- Accumulate pan active motion time for recipe scoring.
- RGB coil should react immediately to pan presence and movement.
- If pan is present and moving, play sizzle at low/medium volume.
- If pan is present but not moving, gradually increase volume and/or switch to burning track.
- If pan is absent, stop or reduce audio.
- Use forgiving thresholds; this is not precision gesture tracking.

## Assumptions And Part Notes

- Controller assumption: Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH module powered from the LS108GP over Ethernet.
- ESP32 part: custom editable ESP32-P4 PoE helper part with the module's functional GPIO labels. The Hall pins match the firmware's ESP32-P4 ADC1 map.
- Accessory rail assumption: cooktop LEDs use `5V_LED`; DFPlayer/audio uses `5V_AUDIO_SERVO`; these positives are not tied together.
- DFPlayer Mini, speaker, and electrolytic capacitors use stock Fritzing parts.
- Hall sensors, RGB cooktop coil, rails, supply, 0.1uF capacitors, resistors, physical cooktop layout, and callouts are custom editable Fritzing helper parts for readability.
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
            "--window-size=2600,1550",
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
