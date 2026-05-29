from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from .config import MasterConfig
from .hardware import AudioController, LedController, StartInput, VolumeReader
from .models import GameState, ScoreBoard
from .module_bus import ModuleBus
from .receipt import ReceiptPrinter, format_receipt


@dataclass
class ControllerHardware:
    start_input: StartInput
    volume: VolumeReader
    leds: LedController
    audio: AudioController
    printer: ReceiptPrinter


class MasterController:
    def __init__(self, config: MasterConfig, bus: ModuleBus, hardware: ControllerHardware) -> None:
        self.config = config
        self.bus = bus
        self.hw = hardware
        self.state = GameState.IDLE
        self.scoreboard = ScoreBoard(
            modules=config.all_modules,
            assign_zero_for_missing=config.assign_zero_for_missing,
        )
        self._last_volume: int | None = None
        self._last_volume_sent_at = 0.0

    def run_forever(self) -> None:
        try:
            while True:
                self.run_one_session()
        finally:
            self.close()

    def run_one_session(self) -> ScoreBoard:
        session_id = uuid.uuid4().hex[:8].upper()
        self.scoreboard.clear()
        self._last_volume = None

        self._set_state(GameState.IDLE)
        self.hw.leds.idle()
        self.hw.start_input.wait_for_start()

        self._countdown(session_id)
        self._run_main_phase(session_id)
        self._run_garnish_phase(session_id)
        self._score_and_print(session_id)
        self._reset(session_id)
        return self.scoreboard

    def close(self) -> None:
        self.hw.leds.off()
        self.bus.close()

    def _countdown(self, session_id: str) -> None:
        self._set_state(GameState.COUNTDOWN)
        self.bus.send_command("PREPARE_GAME", session_id=session_id, total_duration_s=self.config.total_game_seconds)
        for step in ("3", "2", "1", "GO"):
            self.hw.audio.countdown(step)
            self.hw.leds.countdown(step)
            self._sleep(1.0)

    def _run_main_phase(self, session_id: str) -> None:
        self._set_state(GameState.ACTIVE_MAIN)
        self.bus.send_command(
            "START_GAME",
            session_id=session_id,
            phase="main",
            target="main",
            modules=self.config.main_modules,
            duration_s=self.config.main_phase_seconds,
        )
        self._run_phase(
            phase_name="main",
            duration_s=self.config.main_phase_seconds,
            led_update=self.hw.leds.main_active,
        )
        self.bus.send_command("FORCE_END", session_id=session_id, phase="main", target="main")
        self.bus.send_command("REQUEST_SCORE", session_id=session_id, phase="main", target="main")
        self._collect_scores(self.config.score_timeout_s)

    def _run_garnish_phase(self, session_id: str) -> None:
        self._set_state(GameState.GARNISH)
        self.bus.send_command(
            "START_GAME",
            session_id=session_id,
            phase="garnish",
            target="garnish",
            modules=self.config.garnish_modules,
            duration_s=self.config.garnish_phase_seconds,
        )
        self._run_phase(
            phase_name="garnish",
            duration_s=self.config.garnish_phase_seconds,
            led_update=self.hw.leds.garnish_active,
        )
        self.bus.send_command("FORCE_END", session_id=session_id, phase="garnish", target="garnish")
        self.bus.send_command("REQUEST_SCORE", session_id=session_id, phase="garnish", target="garnish")
        self._collect_scores(self.config.score_timeout_s)

    def _run_phase(self, phase_name: str, duration_s: int | float, led_update) -> None:
        started = time.monotonic()
        real_duration = duration_s * self.config.time_scale
        next_log = started

        while True:
            now = time.monotonic()
            elapsed = now - started
            progress = 1.0 if real_duration <= 0 else min(1.0, elapsed / real_duration)
            if elapsed >= real_duration:
                break

            led_update(progress)
            self._poll_bus()
            self._broadcast_volume_if_needed()

            if now >= next_log:
                remaining_actual = max(0, int(round(duration_s * (1.0 - progress))))
                print(f"[{phase_name}] {remaining_actual}s remaining")
                next_log = now + max(1.0, 10.0 * self.config.time_scale)

            self._sleep(self.config.poll_interval_s)

        led_update(1.0)
        self._poll_bus()

    def _collect_scores(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s * self.config.time_scale
        while time.monotonic() < deadline:
            self._poll_bus()
            if not self.scoreboard.missing_modules():
                return
            self._sleep(self.config.poll_interval_s)

    def _score_and_print(self, session_id: str) -> None:
        self._set_state(GameState.SCORING)
        missing = self.scoreboard.missing_modules()
        if missing:
            print(f"[scoring] no report from: {', '.join(missing)}")
        print(f"[scoring] total score {self.scoreboard.total_score():03d}/100")
        self.hw.audio.victory()
        self.hw.leds.victory()

        self._set_state(GameState.PRINTING)
        receipt = format_receipt(self.scoreboard, session_id=session_id)
        self.hw.printer.print_receipt(receipt, logo_path=self.config.logo_path)

    def _reset(self, session_id: str) -> None:
        self._set_state(GameState.RESET)
        self.bus.send_command("RESET_GAME", session_id=session_id, target="all")
        self.hw.leds.idle()

    def _poll_bus(self) -> None:
        for event in self.bus.poll_events():
            recorded = self.scoreboard.record(event)
            if recorded:
                print(f"[score] {event.module} = {event.score:03d}")
            else:
                print(f"[event] {event.module}: {event.event}")

    def _broadcast_volume_if_needed(self) -> None:
        now = time.monotonic()
        if now - self._last_volume_sent_at < self.config.volume_poll_s * self.config.time_scale:
            return

        volume = self.hw.volume.read_volume()
        self.hw.audio.set_volume(volume)
        self._last_volume_sent_at = now
        if self._last_volume is None or abs(volume - self._last_volume) >= self.config.volume_broadcast_delta:
            self.bus.send_command("VOLUME_SET", value=volume, min=self.config.volume_min, max=self.config.volume_max)
            self._last_volume = volume

    def _set_state(self, state: GameState) -> None:
        self.state = state
        print(f"[state] {state.value}")

    def _sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds * self.config.time_scale))
