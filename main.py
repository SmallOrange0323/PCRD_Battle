import os
import sys
import json
import argparse
import logging

from src.parser.timeline_parser import TimelineParser
from src.controller.adb_controller import ADBController
from src.engine.state_machine import BattleStateMachine
from src.reporter.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("PCRDBattleMain")

def load_settings(config_path: str = "config/settings.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "adb": {"default_host": "127.0.0.1", "default_port": 5555},
        "ui_coordinates": {
            "auto_button": [1180, 660],
            "set_buttons": [[360, 650], [510, 650], [660, 650], [810, 650], [960, 650]]
        }
    }

def main():
    parser = argparse.ArgumentParser(description="PCRD BS4 自動測刀與軸異常診斷系統")
    parser.add_argument("--port", type=int, default=5555, help="BS4 ADB 連接埠 (預設 5555)")
    parser.add_argument("--file", type=str, help="軸文字檔路徑 (若無則使用內建範例測試)")
    args = parser.parse_args()

    settings = load_settings()
    host = settings["adb"]["default_host"]
    port = args.port

    logger.info(f"正連接至 BS4 模擬器 ADB [{host}:{port}]...")
    adb = ADBController(host=host, port=port)
    connected = adb.connect()

    if not connected:
        logger.warning(f"無法連線至 ADB [{host}:{port}]，系統將離線執行模擬測試模式。")

    # 軸文字範例
    sample_timeline = """
    開場：開auto + set OOOOO
    112 埃拉 → XXOXO
    103 真步 → OXOOO
    055 真步 → XOOOO
    048 水堇 → OOXOX
    027 埃拉 → XOXXO
    022 埃拉 → OOOOX
    014 真步 → XOOOX
    008 埃拉 → XOOXO
    """

    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            sample_timeline = f.read()

    # 1. 軸解析
    parsed = TimelineParser.parse_timeline_text(sample_timeline)
    logger.info(f"軸解析完成，共載入 {len(parsed['steps'])} 個操作步驟。")

    # 2. 初始化戰鬥狀態機
    set_coords = [tuple(c) for c in settings["ui_coordinates"]["set_buttons"]]
    auto_coord = tuple(settings["ui_coordinates"]["auto_button"])

    state_machine = BattleStateMachine(
        timeline_steps=parsed["steps"],
        adb_controller=adb,
        set_button_coords=set_coords,
        auto_button_coord=auto_coord,
        initial_set=parsed["initial_set"],
        initial_auto=parsed["initial_auto"]
    )

    logger.info("系統初始化完成，準備進入戰鬥監控！")

    # 3. 產出預覽報告測試
    report_file = ReportGenerator.save_report_file(
        output_filepath="reports/sample_report.md",
        timeline_name=args.file if args.file else "Sample_SET_Timeline",
        diagnostics=state_machine.diagnostics,
        total_damage=43300
    )
    logger.info(f"已產出預覽事故報告: {report_file}")

if __name__ == '__main__':
    main()
