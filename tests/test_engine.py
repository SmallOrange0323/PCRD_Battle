import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.timeline_parser import TimelineParser, TimelineStep
from src.controller.adb_controller import ADBController
from src.engine.state_machine import BattleStateMachine
from src.reporter.report_generator import ReportGenerator

class TestEngineAndReporter(unittest.TestCase):

    def test_state_machine_flow(self):
        steps = [
            TimelineStep("1", "1:12", 72, "埃拉", [False, False, True, False, True], "XXOXO"),
            TimelineStep("2", "1:03", 63, "真步", [True, False, True, True, True], "OXOOO")
        ]
        adb = ADBController(port=5555)
        coords = [(100, 100), (200, 200), (300, 300), (400, 400), (500, 500)]
        auto_coord = (1180, 660)

        sm = BattleStateMachine(steps, adb, coords, auto_coord)

        # 模擬戰鬥影格到達 1:12
        updated = sm.process_frame("1:12", 72, [True, True, True, True, True])
        self.assertTrue(updated)
        self.assertEqual(sm.current_step_idx, 1)
        self.assertEqual(sm.current_set, [False, False, True, False, True])

    def test_report_generation(self):
        steps = []
        adb = ADBController(port=5555)
        coords = [(100, 100), (200, 200), (300, 300), (400, 400), (500, 500)]
        auto_coord = (1180, 660)

        sm = BattleStateMachine(steps, adb, coords, auto_coord)
        sm.diagnostics.record_timeout_no_ub("1", "1:12", 72, "埃拉")

        md_content = ReportGenerator.generate_markdown_report("TestTimeline", sm.diagnostics, 43300)
        self.assertIn("1:12", md_content)
        self.assertIn("TIMEOUT_NO_UB", md_content)
        self.assertIn("43,300", md_content)

    def test_state_machine_timeout(self):
        steps = [
            TimelineStep("1", "1:12", 72, "埃拉", [False, False, True, False, True], "XXOXO")
        ]
        adb = ADBController(port=5555)
        coords = [(100, 100), (200, 200), (300, 300), (400, 400), (500, 500)]
        auto_coord = (1180, 660)

        sm = BattleStateMachine(steps, adb, coords, auto_coord)

        # 模擬時間落後超過 2 秒 (傳入 68 秒，目標 72 秒)
        updated = sm.process_frame("1:08", 68, [True, True, True, True, True])
        self.assertFalse(updated)
        self.assertEqual(sm.current_step_idx, 1)  # 已跳過此步驟
        self.assertEqual(len(sm.diagnostics.anomalies), 1)  # 記錄 1 個異常
        self.assertEqual(sm.diagnostics.anomalies[0].anomaly_type, "TIMEOUT_NO_UB")

if __name__ == '__main__':
    unittest.main()
