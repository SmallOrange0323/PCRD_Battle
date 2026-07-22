import time
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Diagnostics")

class BattleAnomaly:
    """
    紀錄單一戰鬥異常/事故
    """
    def __init__(
        self,
        timestamp_str: str,
        seconds: int,
        anomaly_type: str,  # "TIMEOUT_NO_UB", "ORDER_MISMATCH", "RIP_DEATH", "STATE_ERROR"
        expected: str,
        actual: str,
        severity: str = "WARNING",  # "WARNING", "CRITICAL"
        details: Optional[str] = None
    ):
        self.timestamp_str = timestamp_str
        self.seconds = seconds
        self.anomaly_type = anomaly_type
        self.expected = expected
        self.actual = actual
        self.severity = severity
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp_str,
            "seconds": self.seconds,
            "type": self.anomaly_type,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "details": self.details
        }

    def __repr__(self):
        return f"[{self.severity}] {self.timestamp_str} ({self.anomaly_type}) | 預期: {self.expected} | 實際: {self.actual}"


class DiagnosticsEngine:
    """
    事故診斷引擎
    收集並分析戰鬥過程中的偏差與異常
    """

    def __init__(self):
        self.anomalies: List[BattleAnomaly] = []

    def record_timeout_no_ub(self, step_id: str, time_str: str, seconds: int, char_name: str):
        """記錄時間到了但角色未能發動 UB (如 1:12 埃拉未 UB)"""
        anomaly = BattleAnomaly(
            timestamp_str=time_str,
            seconds=seconds,
            anomaly_type="TIMEOUT_NO_UB",
            expected=f"Step {step_id}: {time_str} {char_name} 發動 UB 並切換 SET",
            actual=f"到達時間 {time_str} 後超時未檢測到 {char_name} UB (可能因 TP 未滿或遭控制)",
            severity="CRITICAL"
        )
        self.anomalies.append(anomaly)
        logger.warning(str(anomaly))

    def record_order_mismatch(self, time_str: str, seconds: int, expected_char: str, actual_char: str):
        """記錄亂軸 (發動 UB 的順序不符)"""
        anomaly = BattleAnomaly(
            timestamp_str=time_str,
            seconds=seconds,
            anomaly_type="ORDER_MISMATCH",
            expected=f"預期 {expected_char} 發動 UB",
            actual=f"實際檢測到 {actual_char} 搶先發動 UB (亂軸)",
            severity="CRITICAL"
        )
        self.anomalies.append(anomaly)
        logger.warning(str(anomaly))

    def record_character_rip(self, time_str: str, seconds: int, char_name: str, position_idx: int):
        """記錄角色暴斃/倒刀事故"""
        anomaly = BattleAnomaly(
            timestamp_str=time_str,
            seconds=seconds,
            anomaly_type="RIP_DEATH",
            expected=f"P{position_idx+1} {char_name} 存活",
            actual=f"P{position_idx+1} {char_name} 於 {time_str} HP歸零倒刀死亡",
            severity="CRITICAL"
        )
        self.anomalies.append(anomaly)
        logger.warning(str(anomaly))

    def has_critical_anomalies(self) -> bool:
        return any(a.severity == "CRITICAL" for a in self.anomalies)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_anomalies": len(self.anomalies),
            "critical_count": sum(1 for a in self.anomalies if a.severity == "CRITICAL"),
            "anomalies": [a.to_dict() for a in self.anomalies]
        }
