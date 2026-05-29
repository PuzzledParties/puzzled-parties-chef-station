from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any

from .constants import ALL_MODULES, MODULE_LABELS, RESULT_LINES


class GameState(str, Enum):
    IDLE = "IDLE"
    COUNTDOWN = "COUNTDOWN"
    ACTIVE_MAIN = "ACTIVE_MAIN"
    GARNISH = "GARNISH"
    SCORING = "SCORING"
    PRINTING = "PRINTING"
    RESET = "RESET"


@dataclass(frozen=True)
class ModuleEvent:
    module: str
    event: str
    score: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    received_at: float = field(default_factory=time)


@dataclass
class ModuleScore:
    module: str
    label: str
    score: int | None = None
    event: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    received_at: float | None = None

    @property
    def reported(self) -> bool:
        return self.score is not None


@dataclass
class ScoreBoard:
    modules: tuple[str, ...] = ALL_MODULES
    assign_zero_for_missing: bool = False
    scores: dict[str, ModuleScore] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for module in self.modules:
            self.scores.setdefault(module, ModuleScore(module=module, label=MODULE_LABELS.get(module, module)))

    def clear(self) -> None:
        self.scores.clear()
        for module in self.modules:
            self.scores[module] = ModuleScore(module=module, label=MODULE_LABELS.get(module, module))

    def record(self, event: ModuleEvent) -> bool:
        if event.module not in self.scores:
            self.scores[event.module] = ModuleScore(
                module=event.module,
                label=MODULE_LABELS.get(event.module, event.module.replace("_", " ").title()),
            )

        score = self._clamp_score(event.score) if event.score is not None else None
        existing = self.scores[event.module]
        existing.event = event.event
        existing.payload = event.payload
        existing.received_at = event.received_at
        if score is not None:
            existing.score = score
            return True
        return False

    def missing_modules(self) -> list[str]:
        return [module for module in self.modules if not self.scores[module].reported]

    def total_score(self) -> int:
        values = [
            item.score
            for item in (self.scores[module] for module in self.modules)
            if item.score is not None
        ]

        if self.assign_zero_for_missing:
            values = [self.scores[module].score or 0 for module in self.modules]

        if not values:
            return 0

        return int(round(sum(values) / len(values)))

    def result_line(self) -> str:
        total = self.total_score()
        for threshold, line in RESULT_LINES:
            if total >= threshold:
                return line
        return RESULT_LINES[-1][1]

    def rows(self) -> list[ModuleScore]:
        return [self.scores[module] for module in self.modules]

    @staticmethod
    def _clamp_score(score: int | float | None) -> int | None:
        if score is None:
            return None
        return max(0, min(100, int(round(score))))
