import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.controller.adb_controller import ADBController

class TestADBController(unittest.TestCase):

    def test_adb_instance_init(self):
        controller1 = ADBController(host="127.0.0.1", port=5555)
        controller2 = ADBController(host="127.0.0.1", port=5557)

        self.assertEqual(controller1.device_address, "127.0.0.1:5555")
        self.assertEqual(controller2.device_address, "127.0.0.1:5557")

    def test_toggle_set_diff_calculation(self):
        controller = ADBController()
        coords = [(100, 100), (200, 200), (300, 300), (400, 400), (500, 500)]
        
        current_set = [True, True, True, True, True]    # OOOOO
        target_set  = [False, False, True, False, True]  # XXOXO
        
        # 應點擊 P1 (idx 0), P2 (idx 1), P4 (idx 3)
        diff_indices = [i for i in range(5) if current_set[i] != target_set[i]]
        self.assertEqual(diff_indices, [0, 1, 3])

if __name__ == '__main__':
    unittest.main()
