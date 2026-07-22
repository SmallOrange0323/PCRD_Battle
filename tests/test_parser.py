import unittest
import sys
import os

# 將 src 目錄加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser.timeline_parser import TimelineParser

class TestTimelineParser(unittest.TestCase):

    def test_parse_sample_1(self):
        text = """
        第2隊，傷害43300萬

        6★真步
        5★阿剌克涅
        5★涅妃＝涅羅
        5★埃拉
        5★薇歐莉特（黃泉鯨命）

        開場：開auto + set OOOOO
        112 埃拉 → XXOXO
        103 真步 → OXOOO
        055 真步 → XOOOO
        048 水堇 → OOXOX
        027 埃拉 → XOXXO
        022 埃拉 → OOOOX
        014 真步 → XOOOX
        008 埃拉 → XOOXO
        """
        result = TimelineParser.parse_timeline_text(text)
        
        self.assertTrue(result["initial_auto"])
        self.assertEqual(result["initial_set"], [True, True, True, True, True])
        
        steps = result["steps"]
        self.assertEqual(len(steps), 8)
        
        # 驗證 Step 1
        self.assertEqual(steps[0].time_str, "1:12")
        self.assertEqual(steps[0].time_seconds, 72)
        self.assertEqual(steps[0].trigger_character, "埃拉")
        self.assertEqual(steps[0].target_set, [False, False, True, False, True])
        self.assertEqual(steps[0].raw_set_str, "XXOXO")
        
        # 驗證 Step 4 (048 水堇)
        self.assertEqual(steps[3].time_str, "0:48")
        self.assertEqual(steps[3].trigger_character, "水堇")
        self.assertEqual(steps[3].target_set, [True, True, False, True, False])

    def test_parse_advanced_chain_sample(self):
        text = """
        開場：開auto + set OXXOO
        120 安古 → OXXXO
        110 烏爾 → OOOOO → 安古ub OOOXO
        107 安古 → OOOOO
        050 安古 → OXOXO
        048 安古 → OXOOO + 關auto
        044 烏爾 → OOOOO + 開auto → 風靈ub OXOOO
        033 安古 → XXOXO
        024 烏爾 → XOXOO
        008 烏爾 → XXOOO
        002 烏爾 → XOOOO
        """
        result = TimelineParser.parse_timeline_text(text)
        
        self.assertTrue(result["initial_auto"])
        self.assertEqual(result["initial_set"], [True, False, False, True, True])
        
        steps = result["steps"]
        
        # 驗證 110 連鎖 Step (包含 A 和 B 兩個子步驟)
        step_110_a = [s for s in steps if s.time_str == "1:10" and s.trigger_character == "烏爾"][0]
        step_110_b = [s for s in steps if s.time_str == "1:10" and s.trigger_character == "安古"][0]
        
        self.assertEqual(step_110_a.step_id, "2-A")
        self.assertEqual(step_110_a.raw_set_str, "OOOOO")
        
        self.assertEqual(step_110_b.step_id, "2-B")
        self.assertEqual(step_110_b.raw_set_str, "OOOXO")
        self.assertEqual(step_110_b.depends_on, "2-A")

        # 驗證 048 + 關auto
        step_048 = [s for s in steps if s.time_str == "0:48"][0]
        self.assertFalse(step_048.auto_state)
        self.assertEqual(step_048.raw_set_str, "OXOOO")

        # 驗證 044 + 開auto
        step_044_a = [s for s in steps if s.time_str == "0:44" and s.trigger_character == "烏爾"][0]
        self.assertTrue(step_044_a.auto_state)

if __name__ == '__main__':
    unittest.main()
