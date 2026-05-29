from __future__ import annotations

import html


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_text(
    x: float,
    y: float,
    value: str,
    size: int = 12,
    fill: str = "#1f2933",
    weight: int = 700,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{esc(value)}</text>'
    )


def make_protocol_esp32_poe_part(
    *,
    custom_part,
    connector_cls,
    key: str,
    title: str,
    pins: dict[str, tuple[float, float]],
    labels: dict[str, str],
    wire: dict[str, str],
    family: str,
    extra_note: str = "Local GPIO/data only; accessory loads use external rails.",
):
    """Build a compact editable ESP32 PoE helper part with caller-native Part type."""

    width = 340
    height = 210
    board_x = 36
    board_y = 12
    board_w = 112
    board_h = 176
    gnd_color = wire.get("gnd", "#111111")
    poe_color = wire.get("ethernet", "#1e88e5")
    logic_color = wire.get("control", wire.get("led_data", wire.get("start", "#178f46")))
    v3_color = wire.get("v3", "#7c3aed")

    def pin_color(label: str) -> str:
        upper = label.upper()
        if "GND" in upper:
            return gnd_color
        if "3V3" in upper or "3.3" in upper:
            return v3_color
        if "ETH" in upper or "POE" in upper:
            return poe_color
        return logic_color

    label_svg: list[str] = []
    connectors = []
    for cid, (x, y) in pins.items():
        label = labels.get(cid, cid)
        color = pin_color(label)
        if x < 40:
            label_svg.append(svg_text(x + 10, y + 4, label, 10, color, 800, "start"))
        else:
            label_svg.append(svg_text(x - 9, y + 4, label, 10, color, 800, "end"))
        connectors.append(connector_cls(cid, label, x, y, "#ffffff"))

    body = (
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="10" fill="#f8fafc" stroke="#334155" stroke-width="2"/>'
        f'<rect x="{board_x}" y="{board_y}" width="{board_w}" height="{board_h}" rx="14" fill="#111827" stroke="#475569" stroke-width="2.4"/>'
        f'<rect x="{board_x + 18}" y="{board_y + 18}" width="{board_w - 36}" height="42" rx="7" fill="#0f766e" stroke="#14b8a6" stroke-width="1.5"/>'
        + svg_text(board_x + board_w / 2, board_y + 35, "Waveshare", 12, "#ffffff", 850, "middle")
        + svg_text(board_x + board_w / 2, board_y + 52, "ESP32-P4-POE-ETH", 8, "#ccfbf1", 800, "middle")
        + f'<rect x="{board_x + 23}" y="{board_y + 75}" width="{board_w - 46}" height="46" rx="6" fill="#1f2937" stroke="#4b5563"/>'
        + svg_text(board_x + board_w / 2, board_y + 100, "ESP32", 13, "#e5e7eb", 850, "middle")
        + f'<rect x="{board_x + 18}" y="{board_y + 132}" width="{board_w - 36}" height="28" rx="5" fill="#e2e8f0" stroke="#94a3b8"/>'
        + svg_text(board_x + board_w / 2, board_y + 151, "RJ45 + PoE", 9, "#334155", 850, "middle")
        + svg_text(240, 28, "PoE from LS108GP", 11, poe_color, 850)
        + svg_text(240, 48, "powers ESP32 only", 10, "#7c2d12", 850)
        + svg_text(240, 70, "No LED/servo/audio", 10, "#7c2d12", 850)
        + svg_text(240, 88, "load power here", 10, "#7c2d12", 850)
        + svg_text(240, 118, extra_note, 9, "#334155", 700)
        + "".join(label_svg)
    )

    return custom_part(
        key,
        title,
        "PoE",
        width,
        height,
        body,
        connectors,
        properties={
            "family": family,
            "controller": "Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH helper",
            "power": "PoE powers ESP32 controller only",
            "accessory rails": "12V_SHOW, 5V_LED, 5V_AUDIO_SERVO, 5V_AUX, COMMON_GND",
        },
    )
