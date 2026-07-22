import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UBDetector")

class UBDetector:
    """
    方案 A：角色 UB 閃光與 TP 高亮發動檢測器 (1920x1080 基準)
    """

    def __init__(self, threshold_brightness: int = 220):
        self.threshold_brightness = threshold_brightness
        
        # P1 ~ P5 角色頭像右上角及閃光 ROI 區域 (1920x1080 基準)
        # 格式: (x1, y1, x2, y2)
        self.p1_to_p5_rois = [
            (500, 780, 580, 860),   # P1
            (725, 780, 805, 860),   # P2
            (950, 780, 1030, 860),  # P3
            (1175, 780, 1255, 860), # P4
            (1400, 780, 1480, 860)  # P5
        ]

    def detect_ub_flash(self, frame: np.ndarray) -> List[bool]:
        """
        傳入 1920x1080 戰鬥影格，回傳長度為 5 的 bool 陣列 [P1_UB, P2_UB, P3_UB, P4_UB, P5_UB]
        代表當前幀是否有檢測到該位置發動 UB 閃光特寫
        """
        ub_states = [False] * 5
        if frame is None or frame.size == 0:
            return ub_states

        h, w, _ = frame.shape
        # 若傳入非 1920x1080，進行動態比例縮放對齊
        scale_x = w / 1920.0
        scale_y = h / 1080.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for idx, (x1, y1, x2, y2) in enumerate(self.p1_to_p5_rois):
            rx1, ry1 = int(x1 * scale_x), int(y1 * scale_y)
            rx2, ry2 = int(x2 * scale_x), int(y2 * scale_y)

            roi = gray[ry1:ry2, rx1:rx2]
            if roi.size == 0:
                continue

            # 計算高亮像素 (> 220 亮度) 的佔比
            _, bright_mask = cv2.threshold(roi, self.threshold_brightness, 255, cv2.THRESH_BINARY)
            bright_ratio = np.count_nonzero(bright_mask) / float(roi.size)

            # 當高亮比例超過 25%，判定該位置正在釋放 UB 閃光
            if bright_ratio > 0.25:
                ub_states[idx] = True

        return ub_states
