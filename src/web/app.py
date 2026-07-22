import os
import sys
import json
import logging
import subprocess
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.parser.timeline_parser import TimelineParser
from src.controller.adb_controller import ADBController
from src.engine.state_machine import BattleStateMachine

app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebHub")

active_tasks = {}
PRESETS_DIR = "config/presets"

def detect_bs4_ports() -> list:
    discovered_ports = set()
    try:
        cmd = ["netstat", "-ano", "-p", "tcp"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=0x08000000)
        lines = res.stdout.splitlines()
        for line in lines:
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 2 and ":" in parts[1]:
                    try:
                        port = int(parts[1].split(":")[-1])
                        if (5555 <= port <= 5750) or (5000 <= port <= 5050):
                            discovered_ports.add(port)
                    except ValueError:
                        pass
    except Exception as e:
        logger.error(f"Netstat Error: {e}")

    if not discovered_ports:
        fallback_ports = [5555, 5565, 5575, 5585, 5595, 5605, 5615, 5625, 5635, 5645, 5655, 5665, 5695]
        for p in fallback_ports:
            discovered_ports.add(p)

    return sorted(list(discovered_ports))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan_devices', methods=['GET'])
def scan_devices():
    ports = detect_bs4_ports()
    devices = []
    for idx, port in enumerate(ports):
        controller = ADBController(port=port)
        connected = controller.connect()
        devices.append({
            "id": f"bs4_instance_{idx+1}",
            "name": f"BlueStacks 模擬器 #{idx+1}",
            "address": f"127.0.0.1:{port}",
            "port": port,
            "connected": connected,
            "status": "已連線" if connected else "未連線"
        })
    return jsonify({"success": True, "devices": devices})

@app.route('/api/parse_timeline', methods=['POST'])
def parse_timeline():
    data = request.json or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"success": False, "error": "文字軸內容不能為空"})
    
    try:
        parsed = TimelineParser.parse_timeline_text(text)
        steps_dict = [step.to_dict() for step in parsed["steps"]]
        
        # 自動提取提煉到的角色暱稱
        chars = list(set([s.trigger_character for s in parsed["steps"] if s.trigger_character]))
        
        return jsonify({
            "success": True,
            "initial_auto": parsed["initial_auto"],
            "initial_set": parsed["initial_set"],
            "total_steps": len(steps_dict),
            "steps": steps_dict,
            "detected_characters": chars
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# 儲存軸檔與 P1~P5 對照關係
@app.route('/api/save_preset', methods=['POST'])
def save_preset():
    data = request.json or {}
    name = data.get("name", "").strip()
    text = data.get("text", "")
    party_mapping = data.get("party_mapping", []) # [P1, P2, P3, P4, P5]

    if not name:
        return jsonify({"success": False, "error": "請輸入軸檔儲存名稱"})

    os.makedirs(PRESETS_DIR, exist_ok=True)
    filename = f"{name}.json"
    filepath = os.path.join(PRESETS_DIR, filename)

    preset_data = {
        "name": name,
        "raw_text": text,
        "party_mapping": party_mapping
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(preset_data, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True, "message": f"成功儲存軸檔 [{name}]"})

# 取得所有已儲存的預設軸檔
@app.route('/api/get_presets', methods=['GET'])
def get_presets():
    os.makedirs(PRESETS_DIR, exist_ok=True)
    presets = []
    for filename in os.listdir(PRESETS_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(PRESETS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    presets.append(json.load(f))
            except Exception:
                pass
    return jsonify({"success": True, "presets": presets})

@app.route('/api/start_task', methods=['POST'])
def start_task():
    data = request.json or {}
    port = data.get("port", 5555)
    timeline_text = data.get("timeline_text", "")
    
    parsed = TimelineParser.parse_timeline_text(timeline_text)
    controller = ADBController(port=port)
    connected = controller.connect()
    
    set_coords = [(540, 840), (765, 840), (990, 840), (1215, 840), (1440, 840)]
    auto_coord = (1837, 892)

    sm = BattleStateMachine(
        timeline_steps=parsed["steps"],
        adb_controller=controller,
        set_button_coords=set_coords,
        auto_button_coord=auto_coord,
        initial_set=parsed["initial_set"],
        initial_auto=parsed["initial_auto"]
    )
    
    active_tasks[port] = {
        "port": port,
        "status": "RUNNING",
        "state_machine": sm,
        "connected": connected
    }

    return jsonify({"success": True, "message": f"成功於 127.0.0.1:{port} 啟動出刀作業", "connected": connected})

def run_server(port=5000):
    app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == '__main__':
    run_server()
