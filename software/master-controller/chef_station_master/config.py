from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import ALL_MODULES, GARNISH_PHASE_MODULES, GARNISH_PHASE_SECONDS, MAIN_PHASE_MODULES, MAIN_PHASE_SECONDS


@dataclass
class MasterConfig:
    main_phase_seconds: int = MAIN_PHASE_SECONDS
    garnish_phase_seconds: int = GARNISH_PHASE_SECONDS
    main_modules: tuple[str, ...] = MAIN_PHASE_MODULES
    garnish_modules: tuple[str, ...] = GARNISH_PHASE_MODULES
    all_modules: tuple[str, ...] = ALL_MODULES
    assign_zero_for_missing: bool = False

    module_udp_host: str = "255.255.255.255"
    module_udp_bind_host: str = "0.0.0.0"
    module_udp_port: int = 42100
    score_timeout_s: float = 8.0
    poll_interval_s: float = 0.05

    start_button_gpio: int = 5

    led_gpio: int = 18
    led_count: int = 60
    led_brightness: float = 0.45

    volume_min: int = 0
    volume_max: int = 30
    volume_broadcast_delta: int = 1
    volume_poll_s: float = 0.35
    fixed_volume: int = 18

    printer_mode: str = "file"
    printer_usb_vendor_id: int | None = None
    printer_usb_product_id: int | None = None
    printer_network_host: str | None = None
    printer_network_port: int = 9100
    logo_path: str | None = None
    receipt_output_dir: str = "receipts"

    dry_run: bool = False
    auto_start: bool = False
    time_scale: float = 1.0

    @classmethod
    def from_json(cls, path: str | Path) -> "MasterConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "MasterConfig":
        fields = cls.__dataclass_fields__
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key in fields:
                clean[key] = tuple(value) if key.endswith("_modules") or key == "all_modules" else value
        cfg = cls(**clean)
        if not data.get("all_modules"):
            cfg.all_modules = tuple(dict.fromkeys(cfg.main_modules + cfg.garnish_modules))
        return cfg

    def with_overrides(self, **overrides: Any) -> "MasterConfig":
        data = self.__dict__.copy()
        for key, value in overrides.items():
            if value is not None and key in data:
                data[key] = value
        return MasterConfig.from_mapping(data)

    @property
    def total_game_seconds(self) -> int:
        return self.main_phase_seconds + self.garnish_phase_seconds
