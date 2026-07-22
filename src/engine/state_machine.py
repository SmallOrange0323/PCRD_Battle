import time
import logging
from typing import List, Dict, Any, Optional
from src.parser.timeline_parser import TimelineStep
from src.controller.adb_controller import ADBController
from src.engine.diagnostics import DiagnosticsEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BattleStateMachine")

class BattleStateMachine:
    """
    戰鬥狀態機核心
    控制戰鬥軸步驟進行、透過 ADB 發送 SET 切換、並監測異常
    """

    def __init__(
        self,
        timeline_steps: List[TimelineStep],
        adb_controller: ADBController,
        set_button_coords: List[tuple],
        auto_button_coord: tuple,
        initial_set: Optional[List[bool]] = None,
        initial_auto: Optional[bool] = None
    ):
        self.steps = timeline_steps
        self.adb = adb_controller
        self.set_coords = set_button_coords
        self.auto_coord = auto_button_coord
        
        self.current_step_idx = 0
        self.current_set = initial_set if initial_set else [True, True, True, True, True]
        self.current_auto = initial_auto
        
        self.diagnostics = DiagnosticsEngine()
        self.is_finished = False

    def get_current_step(self) -> Optional[TimelineStep]:
        if self.current_step_idx < len(self.steps):
            return self.steps[self.current_step_idx]
        return None

    def process_frame(
        self,
        current_time_str: str,
        current_seconds: int,
        detected_set: List[bool],
        ub_flashes: Optional[List[bool]] = None
    ) -> bool:
        """
        處理單一影格資訊，判定時間點與 UB 閃光觸發
        """
        if self.is_finished:
            return False

        step = self.get_current_step()
        if not step:
            self.is_finished = True
            logger.info("所有軸步驟已全數執行完畢！")
            return False

        # 1. 如果當前時間還沒倒數到目標時間 (例如開場 1:25 > 目標 1:12)，繼續靜候倒數
        if current_seconds > step.time_seconds:
            return False

        # 2. 若時間已嚴重落後目標時間 3 秒以上，記錄事故並跳過此步驟
        if current_seconds < (step.time_seconds - 3):
            logger.warning(f"🚨 Step {step.step_id} 時間已過 ({step.time_str})，自動記錄並跳過此步驟")
            self.diagnostics.record_timeout_no_ub(
                step_id=step.step_id,
                time_str=step.time_str,
                seconds=current_seconds,
                char_name=step.trigger_character
            )
            self.current_step_idx += 1
            return False

        # 2. 只要戰鬥時間到達或剛好跨過目標秒數 (current_seconds <= step.time_seconds)
        # 即刻精確發送 SET 與 AUTO 點擊切換！
        pos_info = f"P{step.trigger_position + 1}" if step.trigger_position is not None else "全隊"
        logger.info(f"⚡ 戰鬥時間到達 [{current_time_str}] Step {step.step_id} ({step.time_str}) - 角色 '{step.trigger_character}' ({pos_info}) 絕對發送點擊！")
        
        # 根據 target_set 與指定 trigger_position 絕對發送點擊
        if step.trigger_position is not None and 0 <= step.trigger_position < 5:
            # 點擊指定觸發角色的 SET 按鈕
            self.adb.tap_set_button(step.trigger_position, self.set_coords)
        else:
            # 增量比對全隊切換
            self.adb.toggle_set_diff(detected_set, step.target_set, self.set_coords)

        self.current_set = list(step.target_set)

        # 執行 AUTO 變更 (若有指定)
        if step.auto_state is not None:
            self.adb.set_auto(step.auto_state, self.current_auto, self.auto_coord)
            self.current_auto = step.auto_state

        # 推進至下一個 Step
        self.current_step_idx += 1
        return True
