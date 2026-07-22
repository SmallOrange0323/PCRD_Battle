import time
import logging
import threading
import cv2
import numpy as np
from typing import Optional

from src.controller.adb_controller import ADBController
from src.vision.timer_ocr import TimerOCR
from src.vision.set_detector import SETDetector
from src.vision.ub_detector import UBDetector
from src.engine.state_machine import BattleStateMachine

logger = logging.getLogger("BattleWorker")

class BattleWorker(threading.Thread):
    """
    戰鬥背景驅動 Worker Thread
    負責持續從 ADB 擷取畫面 -> 時間/SET 狀態/UB 閃光辨識 -> 推進 BattleStateMachine
    """
    def __init__(
        self,
        adb_controller: ADBController,
        timer_ocr: TimerOCR,
        set_detector: SETDetector,
        state_machine: BattleStateMachine,
        interval_seconds: float = 0.03
    ):
        super().__init__(daemon=True)
        self.adb = adb_controller
        self.timer_ocr = timer_ocr
        self.set_detector = set_detector
        self.ub_detector = UBDetector()
        self.state_machine = state_machine
        self.interval = interval_seconds
        
        self._stop_event = threading.Event()
        self._is_running = False

    def stop(self):
        """通知工作線程停止循環"""
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def run(self):
        logger.info("🚀 BattleWorker 背景戰鬥監控線程已啟動！")
        self._is_running = True

        while not self._stop_event.is_set() and not self.state_machine.is_finished:
            start_time = time.time()

            try:
                # 1. 從 ADB 取得當前畫面圖元
                frame_bytes = self.adb.capture_frame_bytes()
                if frame_bytes is None:
                    time.sleep(self.interval)
                    continue

                # 2. 解碼影格圖像
                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    time.sleep(self.interval)
                    continue

                # 3. 時間 OCR 辨識
                h, w, _ = frame.shape
                timer_roi = frame[int(h * 0.025):int(h * 0.075), int(w * 0.82):int(w * 0.92)]
                time_str, current_seconds = self.timer_ocr.parse_time_from_roi(timer_roi)

                # 4. SET 狀態與 UB 閃光辨識
                detected_set = self.set_detector.detect_p1_to_p5_set(frame, self.state_machine.set_coords)
                ub_flashes = self.ub_detector.detect_ub_flash(frame)

                # 實時 Debug 印出
                step = self.state_machine.get_current_step()
                if step:
                    logger.info(f"🔍 [Worker 監控] 辨識時間: '{time_str}' ({current_seconds}s) | 目標 Step {step.step_id}: {step.time_str} ({step.time_seconds}s) '{step.trigger_character}'")

                # 5. 推進戰鬥狀態機 (雙重條件: 時間點 + UB 閃光)
                self.state_machine.process_frame(time_str, current_seconds, detected_set, ub_flashes)

            except Exception as e:
                logger.error(f"BattleWorker 迴圈執行異常: {e}")

            # 控制 FPS 週期
            elapsed = time.time() - start_time
            sleep_time = max(0.001, self.interval - elapsed)
            time.sleep(sleep_time)

        self._is_running = False
        logger.info("🛑 BattleWorker 背景線程已結束！")
