import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SETDetector")

class SETDetector:
    """
    SET 開關與 AUTO 狀態辨識器
    具備時序平滑濾波 (Temporal Buffer)，防範 UB 特效或全螢幕白光產生的單幀誤判
    """

    def __init__(self, history_size: int = 3):
        self.history_size = history_size
        self._history_buffer: deque = deque(maxlen=history_size)

    @staticmethod
    def is_button_on(crop_bgr: np.ndarray, brightness_threshold: float = 140.0, saturation_threshold: float = 80.0) -> bool:
        """
        傳入單一 SET 按鈕 ROI 圖塊，判定是否為 SET ON (發光/亮燈)
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return False

        hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        
        # S: 彩度 (Saturation), V: 明度 (Value/Brightness)
        mean_s = np.mean(hsv[:, :, 1])
        mean_v = np.mean(hsv[:, :, 2])

        # 明度與彩度較高即代表 SET 亮燈狀態 (ON)
        is_on = (mean_v > brightness_threshold) or (mean_s > saturation_threshold)
        return bool(is_on)

    def detect_p1_to_p5_set(
        self,
        full_frame: np.ndarray,
        set_button_coords: List[Tuple[int, int]],
        roi_size: Tuple[int, int] = (40, 20)
    ) -> List[bool]:
        """
        傳入完整戰鬥影格與 P1~P5 座標，回傳時序平滑後的 bool 陣列 (True=ON, False=OFF)
        """
        raw_results = []
        rw, rh = roi_size
        h, w = full_frame.shape[:2]

        for idx, (cx, cy) in enumerate(set_button_coords):
            x1 = max(0, cx - rw // 2)
            y1 = max(0, cy - rh // 2)
            x2 = min(w, cx + rw // 2)
            y2 = min(h, cy + rh // 2)

            crop = full_frame[y1:y2, x1:x2]
            status = self.is_button_on(crop)
            raw_results.append(status)

        self._history_buffer.append(raw_results)

        # 多幀投票取眾數，減少閃光誤判
        if len(self._history_buffer) < self.history_size:
            return raw_results

        smoothed_results = []
        for col in range(5):
            votes = [frame_res[col] for frame_res in self._history_buffer]
            # 超過半數判定為 True 即為 True
            smoothed_results.append(votes.count(True) > (self.history_size // 2))

        return smoothed_results

    @classmethod
    def detect_auto_state(
        cls,
        full_frame: np.ndarray,
        auto_coord: Tuple[int, int],
        roi_size: Tuple[int, int] = (40, 20)
    ) -> bool:
        """
        判定 AUTO 按鈕是否為 ON
        """
        cx, cy = auto_coord
        rw, rh = roi_size
        h, w = full_frame.shape[:2]

        x1 = max(0, cx - rw // 2)
        y1 = max(0, cy - rh // 2)
        x2 = min(w, cx + rh // 2)
        y2 = min(h, cy + rh // 2)

        crop = full_frame[y1:y2, x1:x2]
        return cls.is_button_on(crop, brightness_threshold=160.0)
