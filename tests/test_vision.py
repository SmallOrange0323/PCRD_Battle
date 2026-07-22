import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.vision.timer_ocr import TimerOCR
from src.vision.set_detector import SETDetector

class TestVisionModules(unittest.TestCase):

    def test_timer_ocr_fallback(self):
        ocr = TimerOCR()
        dummy_img = np.zeros((40, 100, 3), dtype=np.uint8)
        time_str, seconds = ocr.parse_time_from_roi(dummy_img)
        
        self.assertEqual(time_str, "1:12")
        self.assertEqual(seconds, 72)

    def test_set_detector_button_on_off(self):
        # 測試暗色圖片 (OFF)
        dark_crop = np.zeros((20, 40, 3), dtype=np.uint8)
        is_dark_on = SETDetector.is_button_on(dark_crop)
        self.assertFalse(is_dark_on)

        # 測試高亮度亮圖 (ON)
        bright_crop = np.full((20, 40, 3), 255, dtype=np.uint8)
        is_bright_on = SETDetector.is_button_on(bright_crop)
        self.assertTrue(is_bright_on)

    def test_p1_to_p5_detection(self):
        detector = SETDetector(history_size=3)
        full_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # 設定 P3 為高亮 (ON)
        full_frame[640:660, 640:680] = 255

        coords = [
            (360, 650),
            (510, 650),
            (660, 650),  # P3
            (810, 650),
            (960, 650)
        ]
        results = detector.detect_p1_to_p5_set(full_frame, coords)
        
        self.assertEqual(results, [False, False, True, False, False])

if __name__ == '__main__':
    unittest.main()
