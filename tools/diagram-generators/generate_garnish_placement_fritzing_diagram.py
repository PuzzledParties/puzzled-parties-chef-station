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
OUT_DIR = PROJECT_ROOT / "hardware" / "fritzing" / "garnish-placement"
FZZ_PATH = OUT_DIR / "chef_station_garnish_placement_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
PNG_PATH = OUT_DIR / "chef_station_garnish_placement_wiring_diagram.png"
CHECKLIST_PATH = OUT_DIR / "wiring_checklist_garnish_placement.md"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")


WIRE = {
    "vplus": "#f59e0b",
    "gnd": "#111111",
    "control": "#178f46",
    "ethernet": "#1e88e5",
    "touch_center": "#f4b400",
    "touch_inner": "#f57c00",
    "touch_outer": "#c76b00",
    "button": "#1e88e5",
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
    z: float = 2


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
            PARTS / "svg" / "contrib" / view / filename,
        ]
        source = next((p for p in candidates if p.exists()), candidates[0])
        svg_entries[f"svg.{view}.{filename}"] = source.read_text(encoding="utf-8", errors="replace")
    return Part(key, module_id, f"part.{module_id}.fzp", fzp, svg_entries, pins)


def read_esp32_part() -> Part:
    s = 72 / 1000
    raw = {
        "connector1": (1054.7, 1537.4),  # GND
        "connector14": (1054.5, 237.2),  # GPIO23
        "connector20": (54.5, 737.4),    # GPIO2 / TOUCH CH1
        "connector21": (54.5, 837.4),    # GPIO3 / TOUCH CH2
        "connector22": (54.5, 937.4),    # GPIO32
        "connector23": (54.5, 1037.4),   # GPIO26
        "connector24": (54.5, 1137.4),   # GPIO6 / TOUCH CH5
    }
    pins = {k: (x * s, y * s) for k, (x, y) in raw.items()}
    labels = {
        "connector1": "GND",
        "connector14": "GPIO23 / LED DATA",
        "connector20": "GPIO2 / CENTER",
        "connector21": "GPIO3 / INNER",
        "connector22": "GPIO32 / SERVO SIG",
        "connector23": "GPIO26 / DONE",
        "connector24": "GPIO6 / OUTER",
    }
    return make_protocol_esp32_poe_part(
        custom_part=custom_part,
        connector_cls=Connector,
        key="waveshare_esp32_poe_eth",
        title="Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH",
        pins=pins,
        labels=labels,
        wire=WIRE,
        family="Chef Station Garnish Placement",
        extra_note="Touch/GPIO/data only; LED and servo use external 5V rails.",
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


def text(x: float, y: float, value: str, size: int = 14, fill: str = "#1f2933", weight: int = 600, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(value)}</text>'
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
    module_id = f"chef_garnish_{key}"

    def svg_for(layer: str) -> str:
        connector_svg = []
        for c in connectors:
            connector_svg.append(
                f'<circle id="{c.cid}pin" cx="{c.x}" cy="{c.y}" r="5.2" fill="{c.color}" '
                f'stroke="#111111" stroke-width="1.4"><title>{esc(c.name)}</title></circle>'
            )
            connector_svg.append(f'<circle id="{c.cid}terminal" cx="{c.x}" cy="{c.y}" r="1.5" fill="none" stroke="none"/>')
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g id="{layer}">
    {body}
    {''.join(connector_svg)}
  </g>
</svg>
'''

    prop_xml = "\n".join(f'    <property name="{esc(k)}">{esc(v)}</property>' for k, v in properties.items())
    connector_xml = []
    for c in connectors:
        connector_xml.append(
            f'''    <connector id="{c.cid}" type="male" name="{esc(c.name)}">
      <description>{esc(c.name)}</description>
      <views>
        <breadboardView><p layer="breadboard" svgId="{c.cid}pin" terminalId="{c.cid}terminal"/></breadboardView>
        <schematicView><p layer="schematic" svgId="{c.cid}pin" terminalId="{c.cid}terminal"/></schematicView>
        <pcbView><p layer="silkscreen" svgId="{c.cid}pin" terminalId="{c.cid}terminal"/></pcbView>
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
  <tags><tag>chef station</tag><tag>garnish placement</tag><tag>esp32</tag></tags>
  <properties>
    <property name="family">Chef Station Garnish Placement</property>
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
        {c.cid: (c.x, c.y) for c in connectors},
    )


def make_label_part(key: str, lines: list[str], width: int = 280, size: int = 14) -> Part:
    height = max(36, 18 + len(lines) * (size + 5))
    body = [f'<rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#fffefa" stroke="#d0d7de" stroke-width="1.2"/>']
    y = 19
    for i, line in enumerate(lines):
        body.append(text(9, y, line, size, "#1f2933", 700 if i == 0 else 500))
        y += size + 5
    return custom_part(key, lines[0], "TXT", width, height, "".join(body))


def make_waypoint_part() -> Part:
    body = '<circle id="pinmark" cx="3" cy="3" r="2" fill="#ffffff" stroke="#6b7280" stroke-width="1"/>'
    return custom_part("waypoint", "Wire waypoint", "WP", 6, 6, body, [Connector("pin", "waypoint", 3, 3)])


def make_resistor_part(key: str, title: str, value_label: str) -> Part:
    bands = ["#6b4f1d", "#111111", "#d71920", "#c49a23"]
    if value_label.startswith("330"):
        bands = ["#f57c00", "#f57c00", "#6b4f1d", "#c49a23"]
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
        [Connector("connector0", "lead A", 0, 17, "#ffffff"), Connector("connector1", "lead B", 120, 17, "#ffffff")],
        properties={"Resistance": value_label},
    )


def make_rail_part(key: str, title: str, color: str, note: str, tap_count: int = 18) -> Part:
    width = 1010
    connectors: list[Connector] = []
    for i in range(tap_count):
        connectors.append(Connector(f"tap{i}", f"{title} tap {i}", 35 + i * 55, 24, "#ffffff"))
    circles = "".join(f'<circle cx="{35+i*55}" cy="24" r="4.2" fill="#ffffff" stroke="{color}" stroke-width="1.7"/>' for i in range(tap_count))
    body = (
        f'<rect x="0" y="0" width="{width}" height="72" rx="8" fill="#ffffff" stroke="#9aa5b1" stroke-width="1.2"/>'
        f'<line x1="18" y1="24" x2="{width-18}" y2="24" stroke="{color}" stroke-width="8" stroke-linecap="round"/>'
        f'{circles}'
        f'{text(14, 58, note, 14, "#1f2933", 700)}'
    )
    return custom_part(key, title, "RAIL", width, 72, body, connectors, buses={key: [f"tap{i}" for i in range(tap_count)]})


def make_breadboard_part() -> Part:
    holes = []
    for x in range(34, 820, 24):
        for y in range(95, 520, 24):
            holes.append(f'<circle cx="{x}" cy="{y}" r="2.1" fill="#d9d2c3"/>')
    body = (
        '<rect x="0" y="0" width="870" height="610" rx="10" fill="#f1ead7" stroke="#d8ccb0" stroke-width="2"/>'
        + text(22, 33, "Manhattan breadboard / power distribution", 22, "#52606d", 700)
        + text(22, 62, "Straight bus lanes, short branch stubs, labeled rails", 15, "#52606d", 500)
        + "".join(holes)
    )
    return custom_part("breadboard_backplane", "Breadboard / power rails area", "BB", 870, 610, body)


def make_supply_part() -> Part:
    body = (
        '<rect x="0" y="0" width="260" height="135" rx="8" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>'
        + text(16, 25, "Named 5V rail input", 18, "#1f2933", 700)
        + text(16, 49, "from master rails", 20, WIRE["vplus"], 700)
        + text(16, 80, "+ to matching local rail", 14, "#1f2933", 600)
        + text(16, 102, "- to COMMON_GND", 14, "#1f2933", 600)
        + text(210, 52, "+5V", 13, WIRE["vplus"], 700, "end")
        + text(210, 97, "GND", 13, WIRE["gnd"], 700, "end")
    )
    return custom_part(
        "external_5v_supply",
        "Named 5V accessory rail input",
        "5V IN",
        260,
        135,
        body,
        [Connector("vcc", "+5V rail input", 236, 48, "#ffffff"), Connector("gnd", "COMMON_GND", 236, 94, "#ffffff")],
    )


def make_led_strip_part() -> Part:
    leds = []
    for i in range(8):
        x = 104 + i * 25
        leds.append(f'<rect x="{x}" y="26" width="17" height="17" rx="3" fill="#f8fafc" stroke="#aab3bd"/>')
        leds.append(f'<circle cx="{x+8.5}" cy="34.5" r="4" fill="#ffd166" opacity="0.55"/>')
    body = (
        '<rect x="0" y="0" width="335" height="122" rx="8" fill="#2f343b" stroke="#111111" stroke-width="2"/>'
        '<rect x="88" y="18" width="222" height="34" rx="4" fill="#111111" stroke="#8d99a6"/>'
        + "".join(leds)
        + text(18, 29, "+5V", 13, "#ffffff", 700)
        + text(18, 64, "DIN", 13, "#ffffff", 700)
        + text(18, 99, "GND", 13, "#ffffff", 700)
        + text(112, 82, "3-contact addressable RGB strip", 15, "#ffffff", 700)
        + text(112, 103, "WS2812B / NeoPixel style", 13, "#ffffff", 500)
    )
    return custom_part(
        "rgb_led_strip",
        "3-contact addressable RGB strip: +5V / DIN / GND",
        "LED",
        335,
        122,
        body,
        [
            Connector("vcc", "+5V", 18, 28, "#ffffff"),
            Connector("din", "DIN", 18, 63, "#ffffff"),
            Connector("gnd", "GND", 18, 98, "#ffffff"),
        ],
    )


def make_servo_part() -> Part:
    body = (
        '<rect x="70" y="20" width="188" height="126" rx="10" fill="#4b5563" stroke="#111827" stroke-width="2"/>'
        '<circle cx="164" cy="82" r="34" fill="#e5e7eb" stroke="#9ca3af" stroke-width="2"/>'
        '<path d="M164 82 L226 62 L235 78 L168 93 Z" fill="#f8fafc" stroke="#6b7280" stroke-width="2"/>'
        + text(92, 50, "Small hobby servo", 16, "#ffffff", 700)
        + text(92, 72, "30-second pointer", 14, "#ffffff", 500)
        + text(24, 47, "+5V", 13, WIRE["vplus"], 700)
        + text(24, 82, "GND", 13, WIRE["gnd"], 700)
        + text(24, 117, "SIG", 13, WIRE["control"], 700)
    )
    return custom_part(
        "servo_timer",
        "Small hobby servo timer pointer",
        "SERVO",
        280,
        166,
        body,
        [
            Connector("vcc", "+5V red wire", 18, 44, "#ffffff"),
            Connector("gnd", "GND brown/black wire", 18, 79, "#ffffff"),
            Connector("sig", "signal", 18, 114, "#ffffff"),
        ],
    )


def make_button_part() -> Part:
    body = (
        '<rect x="0" y="0" width="210" height="138" rx="8" fill="#eef2ff" stroke="#9aa5b1" stroke-width="2"/>'
        '<circle cx="140" cy="65" r="42" fill="#1e88e5" stroke="#0f5fa8" stroke-width="4"/>'
        '<circle cx="140" cy="65" r="27" fill="#73b7ff" stroke="#e0f2fe" stroke-width="2"/>'
        + text(104, 65, "DONE", 18, "#ffffff", 700, "middle")
        + text(18, 45, "SIG", 13, WIRE["button"], 700)
        + text(18, 89, "GND", 13, WIRE["gnd"], 700)
        + text(18, 119, "INPUT_PULLUP", 13, "#1f2933", 700)
    )
    return custom_part(
        "done_button",
        "DONE momentary pushbutton",
        "DONE",
        210,
        138,
        body,
        [Connector("sig", "DONE signal to GPIO26", 18, 42, "#ffffff"), Connector("gnd", "DONE GND", 18, 86, "#ffffff")],
    )


def make_target_part() -> Part:
    body = (
        '<rect x="0" y="0" width="500" height="500" rx="12" fill="#fff7ed" stroke="#c2410c" stroke-width="2"/>'
        + text(20, 28, "Fake steak capacitive target", 22, "#7c2d12", 700)
        + text(20, 55, "Conductive garnish sits on top", 15, "#7c2d12", 600)
        + '<path d="M196 112 C270 54 408 96 442 199 C477 306 404 418 284 423 C171 429 91 348 98 248 C103 179 139 139 196 112 Z" fill="#d96b4a" stroke="#9f2f18" stroke-width="4"/>'
        + '<path d="M218 153 C280 115 375 142 399 215 C425 294 369 367 286 371 C203 374 147 314 153 246 C158 205 181 176 218 153 Z" fill="#f09368" stroke="#bc4a2f" stroke-width="2" opacity="0.92"/>'
        + '<circle cx="285" cy="258" r="118" fill="none" stroke="#b87333" stroke-width="24"/>'
        + '<circle cx="285" cy="258" r="75" fill="none" stroke="#d28a35" stroke-width="24"/>'
        + '<circle cx="285" cy="258" r="30" fill="#edc46b" stroke="#9a6b22" stroke-width="4"/>'
        + '<circle cx="330" cy="183" r="19" fill="#c4a45a" stroke="#5f4514" stroke-width="3"/>'
        + '<rect x="314" y="174" width="33" height="18" rx="5" fill="#b18b48" opacity="0.7"/>'
        + text(285, 258, "CENTER", 11, "#3b2f12", 700, "middle")
        + text(285, 302, "PERFECT", 13, "#3b2f12", 700, "middle")
        + text(285, 170, "INNER / GOOD", 13, "#3b2f12", 700, "middle")
        + text(285, 120, "OUTER / OK", 13, "#3b2f12", 700, "middle")
        + text(24, 152, "CENTER", 13, WIRE["touch_center"], 700)
        + text(24, 232, "INNER", 13, WIRE["touch_inner"], 700)
        + text(24, 312, "OUTER", 13, WIRE["touch_outer"], 700)
        + text(20, 458, "Visible gaps keep copper / foil zones isolated", 14, "#7c2d12", 700)
    )
    return custom_part(
        "fake_steak_bullseye_target",
        "Fake steak bullseye capacitive electrodes",
        "TARGET",
        500,
        500,
        body,
        [
            Connector("center", "CENTER / PERFECT electrode", 18, 150, "#ffffff"),
            Connector("inner", "INNER / GOOD electrode", 18, 230, "#ffffff"),
            Connector("outer", "OUTER / OK electrode", 18, 310, "#ffffff"),
        ],
        properties={"note": "Electrodes are isolated and never connect to +5V or GND"},
    )


def build_parts() -> dict[str, Part]:
    return {
        "esp32": read_esp32_part(),
        "resistor_1k": make_resistor_part("resistor_1k_series", "1k series resistor", "1k"),
        "resistor_330": make_resistor_part("resistor_330_data", "330-470 ohm LED data resistor", "330 ohm"),
        "cap1000": uniquify_svg_entries(
            read_stock_part("cap1000", PARTS / "obsolete" / "electrolytic_capacitor_1000uF.fzp", {"connector0": (20.64, 97.26), "connector1": (30.64, 97.26)})
        ),
        "cap470": uniquify_svg_entries(
            read_stock_part("cap470", PARTS / "obsolete" / "electrolytic_capacitor_470uF.fzp", {"connector0": (14.73, 82.15), "connector1": (24.73, 82.15)})
        ),
        "breadboard": make_breadboard_part(),
        "vrail": make_rail_part("local_5v_led_rail", "5V_LED rail", WIRE["vplus"], "5V_LED from master power: RGB strip only"),
        "audiorail": make_rail_part("local_5v_audio_servo_rail", "5V_AUDIO_SERVO rail", WIRE["vplus"], "5V_AUDIO_SERVO from master power: servo only"),
        "gndrail": make_rail_part("common_ground_rail", "COMMON_GND rail", WIRE["gnd"], "COMMON_GND: ESP32 + 5V_LED + 5V_AUDIO_SERVO + strip + servo + DONE"),
        "supply": make_supply_part(),
        "ledstrip": make_led_strip_part(),
        "servo": make_servo_part(),
        "button": make_button_part(),
        "target": make_target_part(),
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
          <geometry z="4" x="{x1:.2f}" y="{y1:.2f}" x1="0" y1="0" x2="{x2-x1:.2f}" y2="{y2-y1:.2f}" wireFlags="64"/>
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

    def add(key: str, part: str, title: str, x: float, y: float, props: dict[str, str] | None = None, z: float = 5) -> Instance:
        nonlocal idx
        idx += 1
        item = Instance(key, part, title, x, y, idx, props or {}, z=z)
        inst.append(item)
        return item

    def add_label(key: str, lines: list[str], x: float, y: float, width: int = 280, size: int = 14) -> Instance:
        parts_dynamic[key] = make_label_part(key, lines, width, size)
        return add(key, key, lines[0], x, y, z=7)

    def add_waypoint(key: str, x: float, y: float) -> Instance:
        return add(key, "waypoint", key, x - 3, y - 3, z=4)

    def abs_pos(key: str, conn: str) -> tuple[float, float]:
        by_key = {i.key: i for i in inst}
        item = by_key[key]
        px, py = {**parts, **parts_dynamic}[item.part].pins[conn]
        return item.x + px, item.y + py

    def wire(a: str, ac: str, b: str, bc: str, color: str, title: str, width: float = 9) -> None:
        nonlocal widx
        ax, ay = abs_pos(a, ac)
        bx, by = abs_pos(b, bc)
        if abs(ax - bx) < 0.01 and abs(ay - by) < 0.01:
            return
        widx += 1
        wires.append(Wire(widx, title, a, ac, b, bc, color, width))

    def routed_wire(a: str, ac: str, b: str, bc: str, points: list[tuple[float, float]], color: str, title: str, width: float = 9) -> None:
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
            'Chef Station "Garnish Placement" ESP32 Wiring',
            "Waveshare ESP32-P4 PoE controller, capacitive target, RGB strip, separately powered servo, DONE input",
        ],
        30,
        20,
        760,
        18,
    )
    add_label(
        "pin_table",
        [
            "Pin assignment summary",
            "GPIO2 / TOUCH CH1: CENTER electrode",
            "GPIO3 / TOUCH CH2: INNER RING electrode",
            "GPIO6 / TOUCH CH5: OUTER RING electrode",
            "GPIO23: RGB LED strip data",
            "GPIO32: Servo signal",
            "GPIO26: DONE button input",
        ],
        28,
        425,
        310,
        13,
    )
    add_label(
        "electrode_notes",
        [
            "Capacitive electrode notes",
            "Electrodes never connect to +5V.",
            "Electrodes never connect to GND.",
            "Each zone uses one 1k series resistor.",
            "Keep electrode wires short.",
            "Score after hands/chopsticks are away.",
            "Calibrate baseline before each round.",
        ],
        1805,
        335,
        410,
        13,
    )
    add_label(
        "power_notes",
        [
            "Power and logic notes",
            "ESP32 is powered/networked by PoE from LS108GP.",
            "PoE powers the controller only.",
            "5V_LED powers the RGB strip.",
            "5V_AUDIO_SERVO powers the servo.",
            "COMMON_GND is required for shared signals.",
            "Do not feed +5V into ESP32 3V3.",
            "Do not tie 5V_LED and 5V_AUDIO_SERVO positives together.",
        ],
        28,
        590,
        420,
        13,
    )
    add_label(
        "firmware_notes",
        [
            "Firmware behavior",
            "At start: sample baseline with no garnish.",
            "30s round: strip white, yellow at 10s.",
            "Flash red at 5s; DONE ends early.",
            "Scoring: wait 300-800 ms, read deltas.",
            "Strongest zone: PERFECT / GOOD / OK.",
            "Weak or no signal: MISS / NO GARNISH.",
        ],
        1575,
        955,
        430,
        13,
    )
    add_label(
        "button_note",
        [
            "DONE logic",
            "Use INPUT_PULLUP.",
            "Unpressed = HIGH.",
            "Pressed = LOW.",
            "Software debounce.",
        ],
        905,
        795,
        220,
        13,
    )

    add("esp", "esp32", "Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH", 75, 235)
    add_label(
        "esp_pin_labels",
        [
            "Waveshare ESP32-P4 PoE module",
            "RJ45 carries Ethernet + PoE.",
            "PoE powers ESP32 only.",
            "ESP32-P4 touch pins are GPIO2-GPIO15.",
            "This layout avoids USB GPIO24/GPIO25.",
        ],
        25,
        145,
        290,
        13,
    )

    add("supply_led", "supply", "5V_LED input from master power rails", 360, 78)
    add("supply_servo", "supply", "5V_AUDIO_SERVO input from master power rails", 360, 255)
    add("vrail", "vrail", "5V_LED local rail", 360, 142)
    add("audiorail", "audiorail", "5V_AUDIO_SERVO local rail", 360, 318)
    add("gndrail", "gndrail", "COMMON_GND rail", 360, 650)

    add("r_led", "resistor_330", "R4 330 ohm LED data resistor (330-470 ohm OK)", 610, 213, {"Resistance": "330 ohm"})
    add("r_center", "resistor_1k", "R1 1k CENTER electrode series resistor", 680, 368, {"Resistance": "1k"})
    add("r_inner", "resistor_1k", "R2 1k INNER electrode series resistor", 680, 448, {"Resistance": "1k"})
    add("r_outer", "resistor_1k", "R3 1k OUTER electrode series resistor", 680, 528, {"Resistance": "1k"})
    add_label("resistor_labels", ["Series resistors", "R1/R2/R3: 1k touch safety/isolation", "R4: 330-470 ohm LED DIN"], 602, 292, 345, 13)

    add("ledstrip", "ledstrip", "3-contact addressable RGB strip: +5V / DIN / GND", 1340, 85)
    add("c_led", "cap1000", "C1 1000uF electrolytic near LED strip", 1225, 92, {"Capacitance": "1000uF"})
    add_label("led_note", ["RGB strip", "+5V from 5V_LED.", "DIN from GPIO23 via R4.", "1000uF cap near strip.", "Ground to COMMON_GND."], 1685, 105, 360, 13)

    add("target", "target", "Fake steak bullseye capacitive target", 1280, 300)

    add("servo", "servo", "Small hobby servo timer pointer", 1325, 785)
    add("c_servo", "cap470", "C2 470uF-1000uF electrolytic near servo", 1230, 800, {"Capacitance": "470uF-1000uF"})
    add_label("servo_note", ["Servo timer", "GPIO32 signal.", "Power from 5V_AUDIO_SERVO.", "Do not use ESP32 3.3V.", "Sweeps for 30 seconds."], 1585, 790, 300, 13)

    add("done", "button", "DONE momentary pushbutton", 690, 760)
    add("breadboard", "breadboard", "Breadboard and power rails area", 300, 120, z=0)

    # Power rails and common ground.
    routed_wire("supply_led", "vcc", "vrail", "tap0", [(596, 126), (596, 166)], WIRE["vplus"], "5V_LED input to local 5V_LED rail", 11)
    routed_wire("supply_led", "gnd", "gndrail", "tap0", [(628, 172), (628, 674)], WIRE["gnd"], "5V_LED return to COMMON_GND", 11)
    routed_wire("supply_servo", "vcc", "audiorail", "tap0", [(620, 303), (620, 342)], WIRE["vplus"], "5V_AUDIO_SERVO input to local servo rail", 11)
    routed_wire("supply_servo", "gnd", "gndrail", "tap2", [(650, 349), (650, 674)], WIRE["gnd"], "5V_AUDIO_SERVO return to COMMON_GND", 11)
    routed_wire("esp", "connector1", "gndrail", "tap1", [(225, 345.69), (225, 674)], WIRE["gnd"], "ESP32 GND reference to COMMON_GND rail", 10)

    routed_wire("vrail", "tap13", "ledstrip", "vcc", [(1270, 166), (1270, 113)], WIRE["vplus"], "LED strip +5V to 5V_LED rail", 10)
    routed_wire("gndrail", "tap13", "ledstrip", "gnd", [(1270, 674), (1270, 183)], WIRE["gnd"], "LED strip GND to COMMON_GND rail", 10)
    routed_wire("c_led", "connector1", "ledstrip", "vcc", [(1300, 189.26), (1300, 113)], WIRE["vplus"], "C1 positive across LED +5V", 8)
    routed_wire("c_led", "connector0", "ledstrip", "gnd", [(1260, 189.26), (1260, 183)], WIRE["gnd"], "C1 negative across LED GND", 8)

    routed_wire("audiorail", "tap15", "servo", "vcc", [(1220, 342), (1220, 829)], WIRE["vplus"], "Servo red wire to 5V_AUDIO_SERVO rail", 10)
    routed_wire("gndrail", "tap15", "servo", "gnd", [(1220, 674), (1220, 864)], WIRE["gnd"], "Servo brown/black wire to COMMON_GND", 10)
    routed_wire("c_servo", "connector1", "servo", "vcc", [(1275, 882.15), (1275, 829)], WIRE["vplus"], "C2 positive across servo +5V", 8)
    routed_wire("c_servo", "connector0", "servo", "gnd", [(1248, 882.15), (1248, 864)], WIRE["gnd"], "C2 negative across servo GND", 8)

    routed_wire("done", "gnd", "gndrail", "tap7", [(720, 846), (720, 674)], WIRE["gnd"], "DONE button other side to COMMON_GND", 9)

    # Control/data outputs and button input.
    routed_wire("esp", "connector14", "r_led", "connector0", [(255, 252.08), (255, 230)], WIRE["control"], "GPIO23 to LED data resistor", 9)
    routed_wire("r_led", "connector1", "ledstrip", "din", [(1045, 230), (1045, 148)], WIRE["control"], "LED data resistor to strip DIN", 9)
    routed_wire("esp", "connector22", "servo", "sig", [(245, 302.49), (245, 899), (1343, 899)], WIRE["control"], "GPIO32 servo signal", 9)
    routed_wire("esp", "connector23", "done", "sig", [(270, 309.69), (270, 802)], WIRE["button"], "GPIO26 DONE button input", 9)

    # Capacitive electrode touch lines. The electrodes are isolated from power and ground.
    routed_wire("esp", "connector20", "r_center", "connector0", [(225, 288.09), (225, 385)], WIRE["touch_center"], "GPIO2 / TOUCH CH1 to CENTER 1k resistor", 9)
    routed_wire("esp", "connector21", "r_inner", "connector0", [(240, 295.29), (240, 465)], WIRE["touch_inner"], "GPIO3 / TOUCH CH2 to INNER 1k resistor", 9)
    routed_wire("esp", "connector24", "r_outer", "connector0", [(255, 316.89), (255, 545)], WIRE["touch_outer"], "GPIO6 / TOUCH CH5 to OUTER 1k resistor", 9)
    routed_wire("r_center", "connector1", "target", "center", [(980, 385), (980, 450)], WIRE["touch_center"], "CENTER electrode through R1", 9)
    routed_wire("r_inner", "connector1", "target", "inner", [(1050, 465), (1050, 530)], WIRE["touch_inner"], "INNER electrode through R2", 9)
    routed_wire("r_outer", "connector1", "target", "outer", [(1120, 545), (1120, 610)], WIRE["touch_outer"], "OUTER electrode through R3", 9)

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
        z.writestr("chef_station_garnish_placement_editable.fz", fz)
        for part in all_parts.values():
            z.writestr(part.fzp_name, part.fzp)
            for name, text_value in part.svg_entries.items():
                z.writestr(name, text_value)


def write_checklist() -> None:
    CHECKLIST_PATH.write_text(
        """# Chef Station Garnish Placement Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO2 / Touch CH1 | CENTER capacitive electrode |
| GPIO3 / Touch CH2 | INNER RING capacitive electrode |
| GPIO6 / Touch CH5 | OUTER RING capacitive electrode |
| GPIO23 | RGB LED strip data through 330-470 ohm resistor |
| GPIO32 | Servo signal |
| GPIO26 | DONE button input using `INPUT_PULLUP` |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power RGB strips or servos from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the RGB strip only.
- `5V_AUDIO_SERVO` positive from the master power distribution goes to the local servo rail.
- Both 5V rail returns connect to `COMMON_GND`; do not tie the two 5V positives together.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data, servo signal, DONE input, or touch references cross power domains.
- Do not feed +5V into the ESP32 `3V3` pin.
- LED strip `+5V` connects to the `5V_LED` rail.
- LED strip `GND` connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to LED strip `DIN`.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip.
- Servo red wire connects to `5V_AUDIO_SERVO`, brown/black wire to `COMMON_GND`, and signal to GPIO32.
- Place a 470uF-1000uF electrolytic capacitor across servo +5V and GND near the servo.
- DONE button one side connects to GPIO26; the other side connects to `COMMON_GND`.
- Configure DONE as `INPUT_PULLUP`; logic is unpressed = HIGH, pressed = LOW, with software debounce.
- CENTER electrode connects only to GPIO2 / Touch CH1 through its own 1k series resistor.
- INNER RING electrode connects only to GPIO3 / Touch CH2 through its own 1k series resistor.
- OUTER RING electrode connects only to GPIO6 / Touch CH5 through its own 1k series resistor.
- Capacitive electrodes do not connect to +5V or GND.
- Keep electrode wires short and leave visible gaps between copper/foil zones.
- Score after hands and chopsticks are away; calibrate capacitive baselines before each round.

## Firmware Behavior Notes

- At round start, sample capacitive baselines with no garnish present.
- Player has 30 seconds to place the conductive garnish.
- Servo sweeps from start to end over the 30-second timer.
- RGB strip shows active/countdown state: white at start, yellow at 10 seconds, flashing red at 5 seconds.
- DONE button ends the garnish round early.
- At scoring time, wait 300-800 ms, sample all three touch electrodes, calculate deltas from baseline, and score by strongest zone.
- CENTER strongest = PERFECT; INNER strongest = GOOD; OUTER strongest = OK; weak/no signal = MISS / NO GARNISH.

## Assumptions And Substitutions

- Controller assumption: Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH module powered from the LS108GP over Ethernet.
- ESP32 part: custom editable ESP32-P4 PoE helper part. ESP32-P4 touch-capable GPIOs are GPIO2-GPIO15; this layout uses GPIO2, GPIO3, and GPIO6 while GPIO24/GPIO25 remain untouched.
- Accessory rail assumption: RGB strip uses `5V_LED`; servo uses `5V_AUDIO_SERVO`; these positives are not tied together.
- The LED strip is represented as a custom editable 3-contact WS2812B/NeoPixel-style strip connector.
- The fake steak target is represented as a custom editable bullseye electrode part because no stock Fritzing part matches that prop.
- The servo, target, rails, supply, DONE button, and callouts use custom diagram parts for readable labeled terminals.
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
            "--window-size=2300,1350",
            svg_path.as_uri(),
        ],
        check=True,
    )


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


if __name__ == "__main__":
    main()
