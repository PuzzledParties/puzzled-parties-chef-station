from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chef_station_master.config import MasterConfig
from chef_station_master.constants import GARNISH_PHASE_SECONDS, MAIN_PHASE_SECONDS, TOTAL_GAME_SECONDS
from chef_station_master.models import ModuleEvent, ScoreBoard
from chef_station_master.module_bus import DryRunTransport, ModuleBus, parse_module_event
from chef_station_master.receipt import format_receipt


class TimingTests(unittest.TestCase):
    def test_requested_game_timing(self) -> None:
        self.assertEqual(MAIN_PHASE_SECONDS, 150)
        self.assertEqual(GARNISH_PHASE_SECONDS, 30)
        self.assertEqual(TOTAL_GAME_SECONDS, 180)
        self.assertEqual(MasterConfig().total_game_seconds, 180)


class ProtocolTests(unittest.TestCase):
    def test_parse_json_score_event(self) -> None:
        event = parse_module_event('{"module":"pan","event":"complete","motion_ms":4200,"score":78}')
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.module, "pan")
        self.assertEqual(event.event, "complete")
        self.assertEqual(event.score, 78)

    def test_parse_simon_score_payload(self) -> None:
        event = parse_module_event(
            '{"module":"simon","event":"score","score":94,'
            '"successful_orders":13,"longest_streak":13,"failed_orders":0}'
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.module, "simon")
        self.assertEqual(event.score, 94)
        self.assertEqual(event.payload["successful_orders"], 13)
        self.assertEqual(event.payload["longest_streak"], 13)

    def test_parse_key_value_score_event(self) -> None:
        event = parse_module_event("module=pot_temp event=score percent=73 score=73")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.module, "pot_temp")
        self.assertEqual(event.score, 73)

    def test_command_format(self) -> None:
        transport = DryRunTransport()
        bus = ModuleBus(transport)
        bus.send_command("START_GAME", phase="main", modules=("simon", "chop"), duration_s=150)
        self.assertEqual(transport.written[0], "START_GAME phase=main modules=simon,chop duration_s=150")


class ScoreTests(unittest.TestCase):
    def test_total_averages_valid_reports(self) -> None:
        board = ScoreBoard()
        board.record(ModuleEvent(module="simon", event="complete", score=92))
        board.record(ModuleEvent(module="chop", event="complete", score=85))
        self.assertEqual(board.total_score(), 88)
        self.assertIn("pan", board.missing_modules())

    def test_receipt_marks_missing_modules(self) -> None:
        board = ScoreBoard()
        board.record(ModuleEvent(module="simon", event="complete", score=92))
        receipt = format_receipt(board, session_id="TEST")
        self.assertIn("R + B RESTAURANT", receipt)
        self.assertIn("May 29, 2026", receipt)
        self.assertIn("TOTAL SCORE              092/100", receipt)
        self.assertIn("Chop Speed             NO REPORT", receipt)
        self.assertIn("NO REPORT", receipt)


if __name__ == "__main__":
    unittest.main()
