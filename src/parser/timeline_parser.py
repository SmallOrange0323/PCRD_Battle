import re
from typing import List, Dict, Any, Optional

class TimelineStep:
    """
    代表軸中的單一步驟指令
    """
    def __init__(
        self,
        step_id: str,
        time_str: str,
        time_seconds: int,
        trigger_character: str,
        target_set: List[bool],
        raw_set_str: str,
        auto_state: Optional[bool] = None,
        depends_on: Optional[str] = None,
        trigger_position: Optional[int] = None
    ):
        self.step_id = step_id
        self.time_str = time_str
        self.time_seconds = time_seconds
        self.trigger_character = trigger_character
        self.target_set = target_set  # 長度為 5 的 bool 陣列 [P1, P2, P3, P4, P5]
        self.raw_set_str = raw_set_str
        self.auto_state = auto_state  # True: 開, False: 關, None: 不變
        self.depends_on = depends_on  # 相依的上一個 step_id (用於連鎖切換)
        self.trigger_position = trigger_position  # 0~4 代表 P1~P5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "time_str": self.time_str,
            "time_seconds": self.time_seconds,
            "trigger_character": self.trigger_character,
            "trigger_position": self.trigger_position,
            "target_set": self.target_set,
            "raw_set_str": self.raw_set_str,
            "auto_state": self.auto_state,
            "depends_on": self.depends_on
        }

    def __repr__(self):
        auto_info = f", auto={self.auto_state}" if self.auto_state is not None else ""
        dep_info = f", dep={self.depends_on}" if self.depends_on else ""
        return f"<Step {self.step_id} | {self.time_str} '{self.trigger_character}' -> {self.raw_set_str}{auto_info}{dep_info}>"


class TimelineParser:
    """
    SET 軸文字解析器
    將文字格式的 SET 軸轉譯為結構化 TimelineStep 物件清單
    """

    @staticmethod
    def parse_set_str(set_str: str) -> List[bool]:
        set_str = set_str.strip().upper()
        if len(set_str) != 5:
            raise ValueError(f"SET 字串長度必須為 5，收到: {set_str}")
        return [char == 'O' for char in set_str]

    @staticmethod
    def parse_time_to_seconds(time_raw: str) -> int:
        time_raw = time_raw.strip()
        if ':' in time_raw:
            parts = time_raw.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        else:
            if len(time_raw) == 3:
                minutes = int(time_raw[0])
                seconds = int(time_raw[1:])
                return minutes * 60 + seconds
            elif len(time_raw) <= 2:
                return int(time_raw)
            else:
                raise ValueError(f"無法識別的時間格式: {time_raw}")

    @classmethod
    def parse_timeline_text(cls, text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
        
        initial_auto = None
        initial_set = None
        steps: List[TimelineStep] = []
        step_counter = 1

        for line in lines:
            if line.startswith('---'):
                continue

            # 開場解析
            if '開場' in line or ('set' in line.lower() and ('auto' in line.lower() or 'o' in line.lower() or 'x' in line.lower())):
                if '開場' in line:
                    if '開auto' in line.lower():
                        initial_auto = True
                    elif '關auto' in line.lower():
                        initial_auto = False
                    
                    set_match = re.search(r'set\s+([OXox]{5})', line, re.IGNORECASE)
                    if set_match:
                        initial_set = cls.parse_set_str(set_match.group(1))
                    continue

            # 時間與內容切分
            match = re.match(r'^(\d{1,3}|\d:\d{2})\s*(.*)$', line)
            if not match:
                continue

            time_raw, rest_content = match.groups()
            time_seconds = cls.parse_time_to_seconds(time_raw)
            time_str = f"{time_seconds // 60}:{time_seconds % 60:02d}"

            # 尋找所有 5 字元 SET 狀態區塊 ([OXox]{5})
            # 正則: 抓取 SET 狀態與之前的角色描述
            matches = list(re.finditer(r'([OXox]{5})(\s*\+\s*[開關]auto)?', rest_content))
            if not matches:
                continue

            prev_step_id = None
            last_end = 0
            for idx, m in enumerate(matches):
                set_start, set_end = m.span()
                prefix = rest_content[last_end:set_start]
                last_end = set_end

                # 清理 prefix 以提煉角色名稱
                # 移除箭頭, 'ub', 'UB'
                trigger_char = prefix.replace('->', '').replace('→', '').replace('ub', '').replace('UB', '').strip()

                raw_set_str = m.group(1).upper()
                target_set = cls.parse_set_str(raw_set_str)
                
                auto_str = m.group(2)
                auto_state = None
                if auto_str:
                    if '開auto' in auto_str:
                        auto_state = True
                    elif '關auto' in auto_str:
                        auto_state = False

                current_step_id = f"{step_counter}" if len(matches) == 1 else f"{step_counter}-{chr(65+idx)}"

                step = TimelineStep(
                    step_id=current_step_id,
                    time_str=time_str,
                    time_seconds=time_seconds,
                    trigger_character=trigger_char,
                    target_set=target_set,
                    raw_set_str=raw_set_str,
                    auto_state=auto_state,
                    depends_on=prev_step_id
                )
                steps.append(step)
                prev_step_id = current_step_id

            step_counter += 1

        detected_chars = []
        for s in steps:
            if s.trigger_character and s.trigger_character not in detected_chars:
                detected_chars.append(s.trigger_character)

        return {
            "initial_auto": initial_auto,
            "initial_set": initial_set,
            "detected_characters": detected_chars,
            "steps": steps
        }
