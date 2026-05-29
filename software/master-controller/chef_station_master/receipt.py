from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from .models import ScoreBoard

RECEIPT_DATE = date(2026, 5, 29)


class ReceiptPrinter(Protocol):
    def print_receipt(self, receipt_text: str, logo_path: str | None = None) -> None:
        ...


def format_receipt(scoreboard: ScoreBoard, session_id: str | None = None) -> str:
    total = scoreboard.total_score()
    rows = ["STATION SCORE ITEMS", "-" * 32]
    for row in scoreboard.rows():
        value = f"{row.score:03d}/100" if row.score is not None else "NO REPORT"
        rows.append(f"{row.label[:21]:<21}{value:>11}")

    session_line = f"SESSION: {session_id}" if session_id else datetime.now().strftime("%Y-%m-%d %H:%M")
    receipt_date = RECEIPT_DATE.strftime("%B %d, %Y")
    return "\n".join(
        [
            "        R + B",
            "     RESTAURANT",
            "   == CHEF STATION ==",
            "  --------------------",
            "      R + B RESTAURANT",
            "     29 MAY 2026 SERVICE",
            "",
            receipt_date,
            "",
            "TABLE: CHEF STATION",
            "SERVER: PUZZLED PARTIES",
            "",
            *rows,
            "",
            "-" * 32,
            f"{'TOTAL SCORE':<21}{f'{total:03d}/100':>11}",
            "",
            "RESULT",
            scoreboard.result_line(),
            "",
            session_line,
            "",
            "THANK YOU FOR DINING",
            "AT R + B RESTAURANT",
            "",
        ]
    )


@dataclass
class FileReceiptPrinter:
    output_dir: Path

    def print_receipt(self, receipt_text: str, logo_path: str | None = None) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"chef_station_receipt_{timestamp}.txt"
        latest = self.output_dir / "last_receipt.txt"
        path.write_text(receipt_text, encoding="utf-8")
        latest.write_text(receipt_text, encoding="utf-8")
        print(f"[printer file] wrote {path}")


class NullReceiptPrinter:
    def print_receipt(self, receipt_text: str, logo_path: str | None = None) -> None:
        print("[printer dry-run]\n" + receipt_text)


class EscposReceiptPrinter:
    def __init__(
        self,
        mode: str,
        usb_vendor_id: int | None = None,
        usb_product_id: int | None = None,
        host: str | None = None,
        port: int = 9100,
    ) -> None:
        try:
            from escpos.printer import Network, Usb  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install python-escpos to print to Epson hardware: pip install python-escpos") from exc

        if mode == "usb":
            if usb_vendor_id is None or usb_product_id is None:
                raise ValueError("USB printer mode requires vendor and product IDs")
            self._printer = Usb(usb_vendor_id, usb_product_id)
        elif mode == "network":
            if not host:
                raise ValueError("Network printer mode requires a host")
            self._printer = Network(host, port=port)
        else:
            raise ValueError(f"Unsupported ESC/POS printer mode: {mode}")

    def print_receipt(self, receipt_text: str, logo_path: str | None = None) -> None:
        if logo_path:
            logo = Path(logo_path)
            if logo.exists():
                self._printer.image(str(logo))
        self._printer.text(receipt_text)
        self._printer.cut()


def make_receipt_printer(
    mode: str,
    output_dir: str | Path,
    usb_vendor_id: int | None = None,
    usb_product_id: int | None = None,
    network_host: str | None = None,
    network_port: int = 9100,
    dry_run: bool = False,
) -> ReceiptPrinter:
    if dry_run or mode == "none":
        return NullReceiptPrinter()
    if mode == "file":
        return FileReceiptPrinter(Path(output_dir))
    if mode in {"usb", "network"}:
        return EscposReceiptPrinter(
            mode,
            usb_vendor_id=usb_vendor_id,
            usb_product_id=usb_product_id,
            host=network_host,
            port=network_port,
        )
    raise ValueError(f"Unknown printer mode: {mode}")
