from __future__ import annotations

import html
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
NATIVE_DIR = OUT_DIR / "native_editable_fritzing"
FZZ_PATH = NATIVE_DIR / "chef_station_simon_native_editable.fzz"
EXPORT_DIR = NATIVE_DIR / "fritzing_svg_export"
FRITZING_EXE = Path(r"C:\Program Files\Fritzing\Fritzing.exe")


BUTTONS = [
    {"n": 1, "name": "Ingredient 1", "sw": "GPIO 16", "lamp": "GPIO 21", "color": "#e53935"},
    {"n": 2, "name": "Ingredient 2", "sw": "GPIO 17", "lamp": "GPIO 22", "color": "#43a047"},
    {"n": 3, "name": "Ingredient 3", "sw": "GPIO 18", "lamp": "GPIO 23", "color": "#ffffff"},
    {"n": 4, "name": "Ingredient 4", "sw": "GPIO 19", "lamp": "GPIO 25", "color": "#fbc02d"},
    {"n": 5, "name": "Ingredient 5", "sw": "GPIO 26", "lamp": "GPIO 27", "color": "#1e88e5"},
]

WIRE_COLORS = {
    "vplus": "#d71920",
    "gnd": "#111111",
    "switch1": "#f4b400",
    "switch2": "#1e88e5",
    "gate": "#178f46",
    "lampminus": "#f57c00",
}


@dataclass
class ConnectorDef:
    id: str
    name: str
    x: float
    y: float
    svg_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.svg_id = f"{self.id}pin"


@dataclass
class PartDef:
    module_id: str
    title: str
    label: str
    width: int
    height: int
    connectors: list[ConnectorDef]
    body_svg: str
    properties: dict[str, str] = field(default_factory=dict)
    buses: dict[str, list[str]] = field(default_factory=dict)

    def svg(self, layer: str) -> str:
        safe_title = html.escape(self.title)
        connector_svg = []
        for c in self.connectors:
            connector_svg.append(
                f'<circle id="{c.svg_id}" cx="{c.x}" cy="{c.y}" r="4.5" fill="#f7fafc" '
                f'stroke="#111111" stroke-width="1.5"><title>{html.escape(c.name)}</title></circle>'
            )
            connector_svg.append(
                f'<circle id="{c.id}terminal" cx="{c.x}" cy="{c.y}" r="1.5" fill="none" stroke="none"/>'
            )
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">
  <g id="{layer}">
    <title>{safe_title}</title>
    {self.body_svg}
    {''.join(connector_svg)}
  </g>
</svg>
'''

    def fzp(self, base_image_name: str) -> str:
        props = "\n".join(
            f'    <property name="{html.escape(k)}">{html.escape(v)}</property>' for k, v in self.properties.items()
        )
        connectors_xml = []
        for c in self.connectors:
            connectors_xml.append(
                f'''    <connector id="{c.id}" type="male" name="{html.escape(c.name)}">
      <description>{html.escape(c.name)}</description>
      <views>
        <breadboardView><p layer="breadboard" svgId="{c.svg_id}" terminalId="{c.id}terminal"/></breadboardView>
        <schematicView><p layer="schematic" svgId="{c.svg_id}" terminalId="{c.id}terminal"/></schematicView>
        <pcbView><p layer="silkscreen" svgId="{c.svg_id}" terminalId="{c.id}terminal"/></pcbView>
      </views>
    </connector>'''
            )
        if self.buses:
            bus_xml = ["  <buses>"]
            for bus_id, members in self.buses.items():
                bus_xml.append(f'    <bus id="{html.escape(bus_id)}">')
                for member in members:
                    bus_xml.append(f'      <nodeMember connectorId="{member}"/>')
                bus_xml.append("    </bus>")
            bus_xml.append("  </buses>")
            buses = "\n".join(bus_xml)
        else:
            buses = "  <buses/>"
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" moduleId="{self.module_id}">
  <version>1</version>
  <author>OpenAI Codex</author>
  <title>{html.escape(self.title)}</title>
  <label>{html.escape(self.label)}</label>
  <date>2026-05-23</date>
  <tags><tag>chef station</tag><tag>simon</tag><tag>esp32</tag></tags>
  <properties>
    <property name="family">Chef Station Simon</property>
{props}
  </properties>
  <description>{html.escape(self.title)}</description>
  <views>
    <iconView><layers image="icon/{base_image_name}"><layer layerId="icon"/></layers></iconView>
    <breadboardView><layers image="breadboard/{base_image_name}"><layer layerId="breadboard"/></layers></breadboardView>
    <schematicView><layers image="schematic/{base_image_name}"><layer layerId="schematic"/></layers></schematicView>
    <pcbView><layers image="pcb/{base_image_name}"><layer layerId="silkscreen"/></layers></pcbView>
  </views>
  <connectors>
{chr(10).join(connectors_xml)}
  </connectors>
{buses}
</module>
'''


@dataclass
class PartInstance:
    key: str
    part: PartDef
    title: str
    x: float
    y: float
    model_index: int
    connects: dict[str, list[tuple[int, str]]] = field(default_factory=dict)


@dataclass
class WireInstance:
    title: str
    model_index: int
    a_key: str
    a_conn: str
    b_key: str
    b_conn: str
    color: str
    width: float = 9.0


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def text(x, y, value, size=14, fill="#1f2933", weight="600", anchor="middle") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" dominant-baseline="middle">{esc(value)}</text>'
    )


def make_parts() -> dict[str, PartDef]:
    parts: dict[str, PartDef] = {}

    esp_connectors = [
        ConnectorDef("gnd", "GND", 260, 595),
        ConnectorDef("gpio16", "GPIO 16 BTN1 switch", 420, 62),
        ConnectorDef("gpio21", "GPIO 21 BTN1 lamp", 420, 110),
        ConnectorDef("gpio17", "GPIO 17 BTN2 switch", 420, 162),
        ConnectorDef("gpio22", "GPIO 22 BTN2 lamp", 420, 210),
        ConnectorDef("gpio18", "GPIO 18 BTN3 switch", 420, 262),
        ConnectorDef("gpio23", "GPIO 23 BTN3 lamp", 420, 310),
        ConnectorDef("gpio19", "GPIO 19 BTN4 switch", 420, 362),
        ConnectorDef("gpio25", "GPIO 25 BTN4 lamp", 420, 410),
        ConnectorDef("gpio26", "GPIO 26 BTN5 switch", 420, 462),
        ConnectorDef("gpio27", "GPIO 27 BTN5 lamp", 420, 510),
    ]
    esp_rows = [
        ("GPIO 16", 62),
        ("GPIO 21", 110),
        ("GPIO 17", 162),
        ("GPIO 22", 210),
        ("GPIO 18", 262),
        ("GPIO 23", 310),
        ("GPIO 19", 362),
        ("GPIO 25", 410),
        ("GPIO 26", 462),
        ("GPIO 27", 510),
    ]
    esp_body = [
        '<rect x="0" y="0" width="450" height="640" rx="18" fill="#2a9d8f" stroke="#1f756b" stroke-width="5"/>',
        '<rect x="135" y="18" width="180" height="54" rx="8" fill="#c7cdd4" stroke="#1f756b" stroke-width="2"/>',
        text(225, 120, "ESP32 DevKit", 32, "#ffffff", "700"),
        text(225, 158, "Inputs: INPUT_PULLUP", 18, "#ffffff", "700"),
        text(225, 184, "unpressed=HIGH  pressed=LOW", 16, "#ffffff", "400"),
        text(102, 596, "GND", 22, "#ffffff", "700", "start"),
    ]
    for label, y in esp_rows:
        esp_body.append(f'<rect x="286" y="{y - 16}" width="106" height="32" rx="5" fill="#e6edf3" stroke="#1f756b" stroke-width="1.5"/>')
        esp_body.append(text(280, y, label, 16, "#ffffff", "500", "end"))
    parts["esp32"] = PartDef(
        "chef_simon_esp32_devkit",
        "ESP32 DevKit",
        "ESP32",
        450,
        640,
        esp_connectors,
        "\n".join(esp_body),
        {"note": "Custom diagram part exposing only the GPIOs used here"},
    )

    for item in BUTTONS:
        color = item["color"]
        label_fill = "#1f2933" if color == "#ffffff" else "#ffffff"
        button_body = "\n".join(
            [
                '<rect x="0" y="0" width="280" height="220" rx="10" fill="#eef2f7" stroke="#9aa5b1" stroke-width="2"/>',
                text(140, 25, f'BTN{item["n"]} terminal block', 16, "#1f2933", "700"),
                text(62, 60, "LED +", 16, "#d71920", "700", "start"),
                text(62, 100, "LED -", 16, "#f57c00", "700", "start"),
                text(62, 140, "SW SIG", 16, "#f4b400", "700", "start"),
                text(62, 180, "SW GND", 16, "#111111", "700", "start"),
                f'<circle cx="215" cy="110" r="48" fill="{color}" stroke="#1f2933" stroke-width="4"/>',
                '<circle cx="215" cy="110" r="31" fill="#ffffff" stroke="#f7fafc" stroke-width="1.5"/>',
                text(215, 110, f'BTN{item["n"]}', 18, label_fill, "700"),
                text(140, 205, item["name"], 16, "#1f2933", "700"),
            ]
        )
        parts[f'button{item["n"]}'] = PartDef(
            f'chef_simon_illuminated_button_{item["n"]}',
            f'{item["name"]} illuminated arcade button',
            f'BTN{item["n"]}',
            280,
            220,
            [
                ConnectorDef("ledp", "LED +", 28, 60),
                ConnectorDef("ledm", "LED -", 28, 100),
                ConnectorDef("swsig", "Switch signal", 28, 140),
                ConnectorDef("swgnd", "Switch GND", 28, 180),
            ],
            button_body,
            {
                "button type": "uxcell 60mm 12V LED illuminated arcade pushbutton",
                "switch": "normally open",
            },
        )

    mos_body = "\n".join(
        [
            '<rect x="36" y="6" width="72" height="36" rx="5" fill="#c7cdd4" stroke="#111111" stroke-width="1.5"/>',
            '<rect x="8" y="34" width="128" height="96" rx="8" fill="#2f343b" stroke="#111111" stroke-width="3"/>',
            '<circle cx="72" cy="56" r="9" fill="#dfe5eb" stroke="#111111" stroke-width="1"/>',
            text(72, 84, "IRFB11N50APBF", 13, "#ffffff", "600"),
            text(30, 154, "G", 14, "#1f2933", "700"),
            text(72, 154, "D", 14, "#1f2933", "700"),
            text(114, 154, "S", 14, "#1f2933", "700"),
            '<line x1="30" y1="130" x2="30" y2="146" stroke="#111111" stroke-width="5"/>',
            '<line x1="72" y1="130" x2="72" y2="146" stroke="#111111" stroke-width="5"/>',
            '<line x1="114" y1="130" x2="114" y2="146" stroke="#111111" stroke-width="5"/>',
        ]
    )
    parts["mosfet"] = PartDef(
        "chef_simon_irfb11n50apbf_to220",
        "IRFB11N50APBF N-channel MOSFET TO-220",
        "Q",
        145,
        165,
        [
            ConnectorDef("gate", "Gate", 30, 146),
            ConnectorDef("drain", "Drain", 72, 146),
            ConnectorDef("source", "Source", 114, 146),
        ],
        mos_body,
        {"pinout": "front view Gate / Drain / Source; tab is Drain"},
    )

    def resistor_part(key: str, title: str, label: str) -> None:
        body = "\n".join(
            [
                '<line x1="0" y1="24" x2="36" y2="24" stroke="#8b5e20" stroke-width="4"/>',
                '<rect x="36" y="8" width="110" height="32" rx="8" fill="#e7c99a" stroke="#946b2d" stroke-width="2"/>',
                '<line x1="146" y1="24" x2="182" y2="24" stroke="#8b5e20" stroke-width="4"/>',
                text(91, 24, label, 18, "#1f2933", "700"),
            ]
        )
        parts[key] = PartDef(
            f"chef_simon_resistor_{key}",
            title,
            "R",
            182,
            48,
            [ConnectorDef("a", "Pin A", 0, 24), ConnectorDef("b", "Pin B", 182, 24)],
            body,
            {"resistance": label},
        )

    resistor_part("100r", "100 ohm gate resistor", "100 ohm")
    resistor_part("10k", "10k gate pulldown resistor", "10k")

    rail_connectors = [ConnectorDef(f"tap{i}", f"Tap {i}", 44 + i * 74, 24) for i in range(12)]
    rail_body = "\n".join(
        [
            '<rect x="0" y="0" width="900" height="48" rx="8" fill="#fff7f7" stroke="#d71920" stroke-width="2"/>',
            '<line x1="24" y1="24" x2="876" y2="24" stroke="#d71920" stroke-width="8"/>',
            text(450, 15, "+12V lamp rail (shared LED positives)", 18, "#d71920", "700"),
        ]
    )
    parts["vrail"] = PartDef(
        "chef_simon_12v_lamp_rail",
        "+12V lamp rail",
        "+12V",
        900,
        48,
        rail_connectors,
        rail_body,
        {"rail": "12V for linked uxcell LED buttons"},
        {"vplus": [c.id for c in rail_connectors]},
    )

    gnd_connectors = [ConnectorDef(f"tap{i}", f"Tap {i}", 44 + i * 74, 24) for i in range(12)]
    gnd_body = "\n".join(
        [
            '<rect x="0" y="0" width="900" height="48" rx="8" fill="#f4f4f5" stroke="#111111" stroke-width="2"/>',
            '<line x1="24" y1="24" x2="876" y2="24" stroke="#111111" stroke-width="8"/>',
            text(450, 15, "COMMON GROUND: ESP32 + 12V supply - + switches + MOSFET sources", 16, "#111111", "700"),
        ]
    )
    parts["gndrail"] = PartDef(
        "chef_simon_common_ground_rail",
        "Common ground rail",
        "GND",
        900,
        48,
        gnd_connectors,
        gnd_body,
        {"rail": "all grounds must be common"},
        {"gnd": [c.id for c in gnd_connectors]},
    )

    supply_body = "\n".join(
        [
            '<rect x="0" y="0" width="190" height="100" rx="10" fill="#ffffff" stroke="#9aa5b1" stroke-width="2"/>',
            text(95, 24, "External 12V", 20, "#1f2933", "700"),
            text(95, 49, "lamp supply", 17, "#1f2933", "700"),
            text(55, 78, "+", 20, "#d71920", "700"),
            text(135, 78, "-", 20, "#111111", "700"),
        ]
    )
    parts["supply"] = PartDef(
        "chef_simon_external_12v_supply",
        "External 12V lamp supply",
        "12V",
        190,
        100,
        [ConnectorDef("plus", "+12V", 55, 62), ConnectorDef("minus", "GND", 135, 62)],
        supply_body,
        {"voltage": "12V"},
    )

    note_body = "\n".join(
        [
            '<rect x="0" y="0" width="880" height="175" rx="10" fill="#ffffff" stroke="#9aa5b1" stroke-width="2"/>',
            text(20, 26, "Notes", 22, "#1f2933", "700", "start"),
            text(20, 64, "All grounds must be common.", 18, "#1f2933", "500", "start"),
            text(20, 92, "Do not connect lamp negatives together if individual flashing is required.", 18, "#1f2933", "500", "start"),
            text(20, 120, "Shared +V is OK; switched low side controls each lamp.", 18, "#1f2933", "500", "start"),
            text(20, 148, "Use INPUT_PULLUP. IRFB11N50APBF is not logic-level; replace if LEDs are dim.", 18, "#1f2933", "500", "start"),
        ]
    )
    parts["notes"] = PartDef("chef_simon_notes", "Visible wiring notes", "NOTE", 880, 175, [], note_body)

    return parts


def part_instance_xml(inst: PartInstance) -> str:
    connectors_xml = []
    for conn_id in inst.part.connectors:
        connects = inst.connects.get(conn_id.id, [])
        if connects:
            connect_xml = "\n".join(
                f'                <connect connectorId="{wire_conn}" modelIndex="{wire_idx}" layer="breadboardWire"/>'
                for wire_idx, wire_conn in connects
            )
            connectors_xml.append(
                f'''          <connector connectorId="{conn_id.id}" layer="breadboard">
            <geometry x="0" y="0"/>
            <connects>
{connect_xml}
            </connects>
          </connector>'''
            )
    connectors_block = f"\n        <connectors>\n{chr(10).join(connectors_xml)}\n        </connectors>" if connectors_xml else ""
    return f'''    <instance moduleIdRef="{inst.part.module_id}" modelIndex="{inst.model_index}" path="part.{inst.part.module_id}.fzp">
      <title>{esc(inst.title)}</title>
      <views>
        <breadboardView layer="breadboard">
          <geometry z="2" x="{inst.x:.3f}" y="{inst.y:.3f}"/>{connectors_block}
        </breadboardView>
      </views>
    </instance>'''


def wire_xml(wire: WireInstance, instances: dict[str, PartInstance]) -> str:
    a = instances[wire.a_key]
    b = instances[wire.b_key]
    ac = next(c for c in a.part.connectors if c.id == wire.a_conn)
    bc = next(c for c in b.part.connectors if c.id == wire.b_conn)
    ax, ay = a.x + ac.x, a.y + ac.y
    bx, by = b.x + bc.x, b.y + bc.y
    return f'''    <instance moduleIdRef="WireModuleID" modelIndex="{wire.model_index}" path=":/resources/parts/core/wire.fzp">
      <title>{esc(wire.title)}</title>
      <views>
        <breadboardView layer="breadboardWire">
          <geometry z="3" x="{ax:.3f}" y="{ay:.3f}" x1="0" y1="0" x2="{(bx - ax):.3f}" y2="{(by - ay):.3f}" wireFlags="64"/>
          <wireExtras mils="{wire.width:.3f}" color="{wire.color}" opacity="1" banded="0"/>
          <connectors>
            <connector connectorId="connector0" layer="breadboardWire">
              <geometry x="0" y="0"/>
              <connects>
                <connect connectorId="{wire.a_conn}" modelIndex="{a.model_index}" layer="breadboard"/>
              </connects>
            </connector>
            <connector connectorId="connector1" layer="breadboardWire">
              <geometry x="0" y="0"/>
              <connects>
                <connect connectorId="{wire.b_conn}" modelIndex="{b.model_index}" layer="breadboard"/>
              </connects>
            </connector>
          </connectors>
        </breadboardView>
      </views>
    </instance>'''


def build_sketch(parts: dict[str, PartDef]) -> tuple[list[PartInstance], list[WireInstance]]:
    instances: list[PartInstance] = []
    idx = 1000

    def add(key: str, part_key: str, title: str, x: float, y: float) -> PartInstance:
        nonlocal idx
        idx += 1
        inst = PartInstance(key, parts[part_key], title, x, y, idx)
        instances.append(inst)
        return inst

    add("esp", "esp32", "ESP32 DevKit", 80, 280)
    add("supply", "supply", "External 12V lamp supply", 80, 120)
    add("vrail", "vrail", "+12V lamp rail", 640, 130)
    add("gndrail", "gndrail", "Common ground rail", 640, 1700)
    add("notes", "notes", "Visible wiring notes", 80, 1510)

    rows = [285, 535, 785, 1035, 1285]
    for item, row in zip(BUTTONS, rows):
        add(f'btn{item["n"]}', f'button{item["n"]}', item["name"], 2220, row - 54)
        add(f'q{item["n"]}', "mosfet", f'Q{item["n"]} IRFB11N50APBF', 1320, row + 6)
        add(f'rg{item["n"]}', "100r", f'R{item["n"]} 100 ohm gate', 820, row + 111)
        add(f'rp{item["n"]}', "10k", f'R{item["n"]} 10k pulldown', 1150, row + 174)

    wires: list[WireInstance] = []
    widx = 5000

    def wire(a_key, a_conn, b_key, b_conn, color, title, width=12.0):
        nonlocal widx
        widx += 1
        wires.append(WireInstance(title, widx, a_key, a_conn, b_key, b_conn, color, width))

    wire("supply", "plus", "vrail", "tap0", WIRE_COLORS["vplus"], "12V supply + to +12V rail")
    wire("supply", "minus", "gndrail", "tap0", WIRE_COLORS["gnd"], "12V supply - to common ground")
    wire("esp", "gnd", "gndrail", "tap1", WIRE_COLORS["gnd"], "ESP32 GND to common ground")

    for item, row in zip(BUTTONS, rows):
        n = item["n"]
        sig_color = WIRE_COLORS["switch1"] if n % 2 else WIRE_COLORS["switch2"]
        gpio_sw = item["sw"].lower().replace(" ", "")
        gpio_lamp = item["lamp"].lower().replace(" ", "")
        wire("vrail", f"tap{n}", f"btn{n}", "ledp", WIRE_COLORS["vplus"], f"BTN{n} LED + to +12V")
        wire(f"btn{n}", "ledm", f"q{n}", "drain", WIRE_COLORS["lampminus"], f"BTN{n} LED - to Q{n} drain")
        wire(f"q{n}", "source", "gndrail", f"tap{n + 1}", WIRE_COLORS["gnd"], f"Q{n} source to GND")
        wire(f"btn{n}", "swgnd", "gndrail", f"tap{n + 6}", WIRE_COLORS["gnd"], f"BTN{n} switch common to GND")
        wire("esp", gpio_sw, f"btn{n}", "swsig", sig_color, f"BTN{n} switch signal to {item['sw']}", 10.0)
        wire("esp", gpio_lamp, f"rg{n}", "a", WIRE_COLORS["gate"], f"{item['lamp']} to R gate resistor", 10.0)
        wire(f"rg{n}", "b", f"q{n}", "gate", WIRE_COLORS["gate"], f"R gate resistor to Q{n} gate", 10.0)
        wire(f"q{n}", "gate", f"rp{n}", "a", WIRE_COLORS["gate"], f"Q{n} gate to pulldown", 8.0)
        wire(f"rp{n}", "b", "gndrail", f"tap{min(n + 2, 11)}", WIRE_COLORS["gnd"], f"Q{n} 10k pulldown to GND", 8.0)

    inst_by_key = {inst.key: inst for inst in instances}
    for w in wires:
        inst_by_key[w.a_key].connects.setdefault(w.a_conn, []).append((w.model_index, "connector0"))
        inst_by_key[w.b_key].connects.setdefault(w.b_conn, []).append((w.model_index, "connector1"))

    return instances, wires


def write_fzz(parts: dict[str, PartDef], instances: list[PartInstance], wires: list[WireInstance]) -> None:
    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    inst_by_key = {i.key: i for i in instances}
    instance_xml = "\n".join([wire_xml(w, inst_by_key) for w in wires] + [part_instance_xml(i) for i in instances])
    fz = f'''<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="1.0.3" icon=".png">
  <project_properties>
    <simulator_animation_time_s value="5s"/>
    <simulator_number_of_steps value="400"/>
    <simulator_time_step_mode value="false"/>
    <simulator_time_step_s value="1us"/>
  </project_properties>
  <views>
    <view name="breadboardView" backgroundColor="#fbfaf7" gridSize="0.1in" showGrid="0" alignToGrid="0" viewFromBelow="0" colorWiresByLength="0"/>
    <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="0" alignToGrid="1" viewFromBelow="0"/>
    <view name="pcbView" backgroundColor="#ffffff" gridSize="0.05in" showGrid="0" alignToGrid="1" viewFromBelow="0" autorouteViaHoleSize="" autorouteTraceWidth="24" GPG_Keepout="" autorouteViaRingThickness="" DRC_Keepout="0.01in"/>
  </views>
  <instances>
{instance_xml}
  </instances>
</module>
'''
    with zipfile.ZipFile(FZZ_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("chef_station_simon_native_editable.fz", fz)
        for key, part in parts.items():
            image_name = f"{part.module_id}.svg"
            zf.writestr(f"part.{part.module_id}.fzp", part.fzp(image_name))
            zf.writestr(f"svg.breadboard.{image_name}", part.svg("breadboard"))
            zf.writestr(f"svg.icon.{image_name}", part.svg("icon"))
            zf.writestr(f"svg.schematic.{image_name}", part.svg("schematic"))
            zf.writestr(f"svg.pcb.{image_name}", part.svg("silkscreen"))


def export_with_fritzing() -> bool:
    if not FRITZING_EXE.exists():
        return False
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True)
    shutil.copy2(FZZ_PATH, EXPORT_DIR / FZZ_PATH.name)
    subprocess.run([str(FRITZING_EXE), "-svg", str(EXPORT_DIR)], check=True)
    return True


def main() -> None:
    parts = make_parts()
    instances, wires = build_sketch(parts)
    write_fzz(parts, instances, wires)
    exported = export_with_fritzing()
    print(f"Wrote native editable Fritzing sketch: {FZZ_PATH}")
    print(f"Parts: {len(instances)} instances, Wires: {len(wires)} editable wire instances")
    if exported:
        print(f"Fritzing SVG validation export: {EXPORT_DIR}")
    else:
        print("Fritzing executable not found; skipped validation export")


if __name__ == "__main__":
    main()
