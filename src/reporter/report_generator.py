import time
import os
from typing import Dict, Any, Optional
from src.engine.diagnostics import DiagnosticsEngine

class ReportGenerator:
    """
    測刀事故報告生成器
    產出結構化的 Markdown / HTML 事故診斷報告
    """

    @staticmethod
    def generate_markdown_report(
        timeline_name: str,
        diagnostics: DiagnosticsEngine,
        total_damage: Optional[int] = None
    ) -> str:
        report_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        summary = diagnostics.get_summary()
        has_issues = summary["critical_count"] > 0

        status_badge = "❌ **發現戰鬥異常/事故**" if has_issues else "✅ **測刀順利通關 (未發現事故)**"

        md = []
        md.append(f"# PCRD 自動測刀事故診斷報告")
        md.append(f"- **測刀時間**：{report_time}")
        md.append(f"- **測試軸檔**：{timeline_name}")
        if total_damage:
            md.append(f"- **實測總傷害**：{total_damage:,} 萬")
        md.append(f"- **總體狀態**：{status_badge}")
        md.append("")
        md.append("---")
        md.append("")

        md.append("## 異常統計與診斷明細")
        md.append(f"- 檢測到事故總數：**{summary['total_anomalies']}** 筆 (關鍵事故：{summary['critical_count']} 筆)")
        md.append("")

        if not summary["anomalies"]:
            md.append("> 🎉 所有 SET 切換與 UB 釋放皆符合預期時序！")
        else:
            md.append("| 時間點 | 異常類型 | 嚴重性 | 預期狀況 | 實際發生狀況 |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for item in summary["anomalies"]:
                severity_icon = "🔴 嚴重" if item["severity"] == "CRITICAL" else "🟡 警告"
                md.append(f"| `{item['timestamp']}` | `{item['type']}` | {severity_icon} | {item['expected']} | {item['actual']} |")

        md.append("")
        md.append("---")
        md.append("*報告由 PCRD Battle Automation & Diagnostics Engine 自動生成*")
        
        return "\n".join(md)

    @classmethod
    def save_report_file(
        cls,
        output_filepath: str,
        timeline_name: str,
        diagnostics: DiagnosticsEngine,
        total_damage: Optional[int] = None
    ) -> str:
        content = cls.generate_markdown_report(timeline_name, diagnostics, total_damage)
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_filepath
