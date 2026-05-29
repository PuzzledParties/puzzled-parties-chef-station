from __future__ import annotations

import json
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import ModuleEvent


KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\"[^\"]*\"|'[^']*'|[^,\s]+)")
SCORE_RE = re.compile(r"\bscore\s*[:=]\s*(?P<score>-?\d+(?:\.\d+)?)\b", re.IGNORECASE)
MODULE_RE = re.compile(r"\bmodule\s*[:=]\s*(?P<module>[A-Za-z0-9_ -]+)\b", re.IGNORECASE)


class LineTransport(Protocol):
    def write_line(self, line: str) -> None:
        ...

    def read_available(self) -> list[str]:
        ...

    def close(self) -> None:
        ...


@dataclass
class DryRunTransport:
    written: list[str] = field(default_factory=list)
    incoming: list[str] = field(default_factory=list)

    def write_line(self, line: str) -> None:
        self.written.append(line)
        print(f"[module-bus dry-run] -> {line}")

    def read_available(self) -> list[str]:
        lines = list(self.incoming)
        self.incoming.clear()
        return lines

    def close(self) -> None:
        return


class UdpLineTransport:
    def __init__(self, host: str, port: int, bind_host: str = "0.0.0.0") -> None:
        self.host = host
        self.port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.bind((bind_host, port))
        self._socket.setblocking(False)

    def write_line(self, line: str) -> None:
        payload = (line.rstrip() + "\n").encode("utf-8")
        self._socket.sendto(payload, (self.host, self.port))

    def read_available(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                payload, _addr = self._socket.recvfrom(2048)
            except BlockingIOError:
                break
            lines.extend(
                line.strip()
                for line in payload.decode("utf-8", errors="replace").splitlines()
                if line.strip()
            )
        return lines

    def close(self) -> None:
        self._socket.close()


class ModuleBus:
    def __init__(self, transport: LineTransport) -> None:
        self.transport = transport

    def send_command(self, command: str, **fields: Any) -> None:
        parts = [command]
        for key, value in fields.items():
            if value is None:
                continue
            if isinstance(value, (tuple, list)):
                value = ",".join(str(item) for item in value)
            parts.append(f"{key}={value}")
        self.transport.write_line(" ".join(parts))

    def poll_events(self) -> list[ModuleEvent]:
        events: list[ModuleEvent] = []
        for line in self.transport.read_available():
            if not line:
                continue
            event = parse_module_event(line)
            if event is not None:
                events.append(event)
            else:
                print(f"[module-bus] ignored line: {line}")
        return events

    def close(self) -> None:
        self.transport.close()


def parse_module_event(line: str) -> ModuleEvent | None:
    stripped = line.strip()
    if not stripped:
        return None

    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return _event_from_mapping(data)

    key_values = _parse_key_values(stripped)
    if key_values:
        return _event_from_mapping(key_values)

    return _parse_loose_score_line(stripped)


def _event_from_mapping(data: dict[str, Any]) -> ModuleEvent | None:
    module = _clean_module_name(data.get("module") or data.get("station") or data.get("name"))
    if not module:
        return None

    event = str(data.get("event") or data.get("status") or "score").strip().lower()
    score = _coerce_score(data.get("score"))
    return ModuleEvent(module=module, event=event, score=score, payload=data, received_at=time.time())


def _parse_key_values(line: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for match in KEY_VALUE_RE.finditer(line):
        value = match.group("value").strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        parsed[match.group("key").lower()] = value
    return parsed


def _parse_loose_score_line(line: str) -> ModuleEvent | None:
    score_match = SCORE_RE.search(line)
    if not score_match:
        return None

    module_match = MODULE_RE.search(line)
    module = _clean_module_name(module_match.group("module")) if module_match else None
    if not module:
        prefix = line.split(":", 1)[0].strip().lower()
        module = _clean_module_name(prefix) if prefix and " " not in prefix else None
    if not module:
        return None

    return ModuleEvent(
        module=module,
        event="score",
        score=_coerce_score(score_match.group("score")),
        payload={"raw": line},
        received_at=time.time(),
    )


def _coerce_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _clean_module_name(value: Any) -> str | None:
    if value is None:
        return None
    module = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "chopping": "chop",
        "chop_speed": "chop",
        "pan_motion": "pan",
        "pot": "pot_temp",
        "pot_balance": "pot_temp",
        "temperature": "pot_temp",
        "garnish_placement": "garnish",
    }
    return aliases.get(module, module)
