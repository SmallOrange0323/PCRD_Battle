import unittest
import numpy as np
from src.vision.ub_detector import UBDetector

class TestUBDetector(unittest.TestCase):
    def setUp(self):
        self.detector = UBDetector()

    def test_empty_frame(self):
        ub_flashes = self.detector.detect_ub_flash(None)
        self.assertEqual(ub_flashes, [False]*5)

    def test_dark_frame_no_ub(self):
        # 建立全黑畫面 (1920x1080)
        dark_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        ub_flashes = self.detector.detect_ub_flash(dark_frame)
        self.assertEqual(ub_flashes, [False]*5)

    def test_p1_flash_ub(self):
        # 建立畫面並將 P1 ROI (500~580, 780~860) 填滿高亮白色 (255)
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[780:860, 500:580] = 255
        
        ub_flashes = self.detector.detect_ub_flash(frame)
        self.assertTrue(ub_flashes[0])  # P1 應被判定發動 UB
        self.assertFalse(ub_flashes[1]) # P2 應為 False

if __name__ == '__main__':
    unittest.main()
