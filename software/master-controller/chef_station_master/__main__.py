from __future__ import annotations

import argparse
from pathlib import Path

from .config import MasterConfig
from .runtime import build_controller


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Chef Station Raspberry Pi master controller.")
    parser.add_argument("--config", type=Path, help="Path to a JSON config file.")
    parser.add_argument("--dry-run", action="store_true", help="Run without Pi GPIO, ADS1115, NeoPixels, printer, or network hardware.")
    parser.add_argument("--auto-start", action="store_true", help="Start immediately instead of waiting for the GPIO/console start button.")
    parser.add_argument("--once", action="store_true", help="Run one game session and exit.")
    parser.add_argument("--time-scale", type=float, help="Scale real wait time for testing; commands still use real game seconds.")
    parser.add_argument("--module-host", help="Module command host or broadcast address.")
    parser.add_argument("--module-port", type=int, help="UDP port for module line commands.")
    parser.add_argument("--printer-mode", choices=["file", "none", "usb", "network"], help="Receipt printer output mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = MasterConfig.from_json(args.config) if args.config else MasterConfig()
    config = config.with_overrides(
        dry_run=args.dry_run or None,
        auto_start=args.auto_start or None,
        time_scale=args.time_scale,
        module_udp_host=args.module_host,
        module_udp_port=args.module_port,
        printer_mode=args.printer_mode,
    )

    if config.main_phase_seconds != 150 or config.garnish_phase_seconds != 30:
        raise SystemExit("Chef Station timing must be 150s main phase + 30s garnish phase for a 180s game.")

    controller = build_controller(config)
    if args.once:
        try:
            controller.run_one_session()
        finally:
            controller.close()
    else:
        controller.run_forever()


if __name__ == "__main__":
    main()
