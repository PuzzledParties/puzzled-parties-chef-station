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
FZZ_PATH = OUT_DIR / "chef_station_simon_library_art_resistor_values_editable.fzz"
EXPORT_DIR = OUT_DIR / "fritzing_svg_export"
FRITZING = Path(r"C:\Program Files\Fritzing\Fritzing.exe")
PARTS = Path(r"C:\Program Files\Fritzing\fritzing-parts")
ESP32_FZPZ = ROOT / "downloaded_parts" / "DOIT_Esp32_DevKit_v1_improved.fzpz"


BUTTONS = [
    {"n": 1, "name": "Ingredient 1", "sw": "GPIO 16", "lamp": "GPIO 21", "color": "red"},
    {"n": 2, "name": "Ingredient 2", "sw": "GPIO 17", "lamp": "GPIO 22", "color": "green"},
    {"n": 3, "name": "Ingredient 3", "sw": "GPIO 18", "lamp": "GPIO 23", "color": "white"},
    {"n": 4, "name": "Ingredient 4", "sw": "GPIO 19", "lamp": "GPIO 25", "color": "yellow"},
    {"n": 5, "name": "Ingredient 5", "sw": "GPIO 26", "lamp": "GPIO 27", "color": "blue"},
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
    "gnd": "#111111",
    "switch_a": "#f4b400",
    "switch_b": "#1e88e5",
    "gate": "#178f46",
    "lamp_minus": "#f57c00",
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


def make_rail_part(key: str, title: str, color: str, labels: list[str]) -> Part:
    connectors = []
    pins = {}
    for i in range(12):
        x = 35 + i * 55
        connectors.append(f'<connector id="tap{i}" type="male" name="tap {i}"><views><breadboardView><p layer="breadboard" svgId="tap{i}pin"/></breadboardView><schematicView><p layer="schematic" svgId="tap{i}pin"/></schematicView><pcbView><p layer="silkscreen" svgId="tap{i}pin"/></pcbView></views></connector>')
        pins[f"tap{i}"] = (x, 24)
    circles = "".join(f'<circle id="tap{i}pin" cx="{35+i*55}" cy="24" r="5" fill="#ffffff" stroke="{color}" stroke-width="2"/>' for i in range(12))
    label_svg = "".join(f'<text x="16" y="{52+i*20}" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="600" fill="#1f2933">{esc(line)}</text>' for i, line in enumerate(labels))
    height = 70 + len(labels) * 20
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="670" height="{height}" viewBox="0 0 670 {height}">
  <g id="breadboard"><rect x="0" y="0" width="670" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="652" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="schematic"><rect x="0" y="0" width="670" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="652" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="silkscreen"><rect x="0" y="0" width="670" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="652" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
  <g id="icon"><rect x="0" y="0" width="670" height="{height}" rx="8" fill="#ffffff" stroke="#9aa5b1"/><line x1="18" y1="24" x2="652" y2="24" stroke="{color}" stroke-width="7"/>{circles}{label_svg}</g>
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
  <buses><bus id="{key}">{''.join(f'<nodeMember connectorId="tap{i}"/>' for i in range(12))}</bus></buses>
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
        "arcade_red": read_stock_part("arcade_red", STOCK["arcade_red"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_yellow": read_stock_part("arcade_yellow", STOCK["arcade_yellow"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_white": read_stock_part("arcade_white", STOCK["arcade_white"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "arcade_blue": read_stock_part("arcade_blue", STOCK["arcade_blue"], {"connector1": (55, 135), "connector2": (76, 135)}),
        "vrail": make_rail_part("vplus_12v_rail", "+12V lamp rail", WIRE["vplus"], ["Shared +12V to every LED + terminal"]),
        "gndrail": make_rail_part("common_ground_rail", "Common ground rail", WIRE["gnd"], ["All grounds must be common"]),
        "notes": make_label_part("notes", ["Notes", "Use INPUT_PULLUP: unpressed HIGH, pressed LOW.", "Do not tie LED/lamp negatives together.", "Gate resistors: 1k. Pulldowns: 10k.", "IRFB11N50APBF is not logic-level; replace if LEDs are dim."], 760, 16),
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


def build_instances() -> tuple[list[Instance], list[Wire]]:
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
        widx += 1
        wires.append(Wire(widx, title, a, ac, b, bc, color, width))

    global parts_dynamic
    parts_dynamic = {}

    add("esp", "esp32", "DOIT ESP32 DevKit V1", 85, 275)
    add("vrail", "vrail", "+12V LED rail", 420, 100)
    add("gndrail", "gndrail", "Common GND rail", 420, 1510)
    add("notes", "notes", "Notes", 85, 1460)
    add_label("esp_pin_labels", ["ESP32 GPIOs", "BTN inputs: 16,17,18,19,26", "Lamp gates: 21,22,23,25,27"], 32, 210, 260)

    rows = [250, 490, 730, 970, 1210]
    esp_sw = {1: "connector5", 2: "connector6", 3: "connector8", 4: "connector9", 5: "connector23"}
    esp_lamp = {1: "connector10", 2: "connector13", 3: "connector14", 4: "connector22", 5: "connector24"}
    colors = {"red": "arcade_red", "green": "arcade_green", "white": "arcade_white", "yellow": "arcade_yellow", "blue": "arcade_blue"}
    for item, row in zip(BUTTONS, rows):
        n = item["n"]
        add(f"rg{n}", "resistor_1k", f"R{n} 1k gate", 370, row + 80, {"Resistance": "1k"})
        add(f"rp{n}", "resistor_10k", f"R{n} 10k gate pulldown", 520, row + 132, {"Resistance": "10k"})
        add(f"q{n}", "mosfet", f"Q{n} IRFB11N50APBF", 660, row + 48)
        add(f"term{n}", "terminal4", f"BTN{n} 4-terminal plug", 910, row + 86)
        add(f"button{n}", colors[item["color"]], f'{item["name"]} arcade button visual', 1085, row + 28)
        add_label(f"plug_labels_{n}", [f"BTN{n} plug order", "1 LED +   2 LED -", "3 SW SIG  4 SW GND"], 895, row + 15, 250)
        add_label(f"resistor_labels_{n}", [f"BTN{n} resistors", "Gate: 1k", "Pulldown: 10k"], 365, row + 10, 170)
        add_label(f"mosfet_labels_{n}", [f"Q{n} G / D / S", "Gate via 1k", "Drain to LED -", "Source to GND"], 610, row - 28, 210)

        wire("vrail", f"tap{n}", f"term{n}", "connector0", WIRE["vplus"], f"BTN{n} LED+ to shared +12V", 12)
        wire(f"term{n}", "connector1", f"q{n}", "connector1", WIRE["lamp_minus"], f"BTN{n} LED- to MOSFET drain", 10)
        wire(f"q{n}", "connector2", "gndrail", f"tap{n+1}", WIRE["gnd"], f"Q{n} source to common GND", 12)
        wire(f"term{n}", "connector3", "gndrail", f"tap{n+6}", WIRE["gnd"], f"BTN{n} switch GND", 10)
        wire("esp", esp_sw[n], f"term{n}", "connector2", WIRE["switch_a"] if n % 2 else WIRE["switch_b"], f"BTN{n} switch signal to {item['sw']}", 10)
        wire("esp", esp_lamp[n], f"rg{n}", "connector0", WIRE["gate"], f"{item['lamp']} to 1k gate resistor", 10)
        wire(f"rg{n}", "connector1", f"q{n}", "connector0", WIRE["gate"], f"1k resistor to Q{n} gate", 10)
        wire(f"q{n}", "connector0", f"rp{n}", "connector0", WIRE["gate"], f"Q{n} gate to 10k pulldown", 8)
        wire(f"rp{n}", "connector1", "gndrail", f"tap{min(n+2,11)}", WIRE["gnd"], f"10k pulldown to GND", 8)
        wire(f"term{n}", "connector2", f"button{n}", "connector1", WIRE["switch_a"], f"BTN{n} plug SW SIG to arcade switch lug", 7)
        wire(f"term{n}", "connector3", f"button{n}", "connector2", WIRE["gnd"], f"BTN{n} plug SW GND to arcade switch lug", 7)

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
        z.writestr("chef_station_simon_library_art_resistor_values_editable.fz", fz)
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
    inst, wires = build_instances()
    write_fzz(parts, inst, wires)
    export()
    print(f"Wrote {FZZ_PATH}")
    print(f"Editable part instances: {len(inst)}")
    print(f"Editable wires: {len(wires)}")
    print(f"Fritzing SVG export: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
