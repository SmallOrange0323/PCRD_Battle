# PCRD Battle Automation & Diagnostics System - 專案協作指南 (AGENTS.md)

本文件定義本專案《超異域公主連結 Re:Dive》(PCRD) 自動測刀與軸異常診斷系統的開發規範、架構共識與維護準則。

---

## 1. 專案概述 (Project Overview)

本專案旨在透過 Python 結合圖像辨識 (OpenCV / Template Matching) 與 **ADB 視窗/多實例控制 (pure-python-adb / ADB Shell)**，達成 BlueStacks 4 (BS4) 模擬器上的《公主連結》單帳號/多帳號並行自動測刀、半自動出刀與事故診斷功能。

### 核心功能
- **SET 軸文本解析器 (Timeline Parser)**：將文字格式的 SET 軸（如 `112 埃拉 → XXOXO`）轉換為自動化結構指令。
- **ADB 多實例控制與背景點擊 (ADB Multi-Instance Controller)**：透過 ADB 獨立連接埠 (如 `127.0.0.1:5555`, `127.0.0.1:5557`)，支援多帳號並行出刀與完全背景點擊。
- **戰鬥狀態即時辨識 (Real-time Battle OCR/CV)**：高頻率讀取戰鬥倒數時間、SET 開關狀態與角色 UB 釋放狀態。
- **軸異常診斷與報告生成 (Diagnostics & Reporter)**：檢測「未按時 UB」、「亂軸」、「角色倒刀」等異常，產出測刀事故報告。

---

## 2. 架構與模組約定 (Architecture & Module Contracts)

專案目錄結構設計如下：

```
PCRD battle/
├── AGENTS.md                 # 專案規範與動態憲法
├── config/
│   └── settings.json         # 座標、解析度與 ADB 設定檔
├── src/
│   ├── parser/               # 軸文字解析模組
│   │   └── timeline_parser.py
│   ├── vision/               # 戰鬥畫面辨識模組 (OpenCV / OCR)
│   │   ├── screen_capture.py
│   │   └── timer_ocr.py
│   ├── controller/           # BS4 ADB 多實例控制
│   │   └── adb_controller.py
│   ├── engine/               # 戰鬥狀態機與診斷核心
│   │   ├── state_machine.py
│   │   └── diagnostics.py
│   └── reporter/             # 報告與日誌產出
│       └── report_generator.py
├── tests/                    # 模組測試腳本
└── main.py                   # 主程式入口
```

---

## 3. 命名與資料傳遞規範 (Naming & Data Contracts)

### 3.1 軸指令資料結構 (Timeline Action Structure)

```python
{
    "step_id": "1",
    "time_str": "1:12",       # 顯示用時間字串
    "time_seconds": 72,       # 換算後剩餘總秒數
    "trigger_character": "埃拉", # 觸發 UB 的角色名稱
    "target_set": [False, False, True, False, True], # P1~P5 標的 SET 狀態 (True=ON, False=OFF)
    "raw_set_str": "XXOXO",   # 原始 SET 字串
    "auto_state": None,       # True: 開auto, False: 關auto, None: 不變
    "depends_on": None        # 連鎖相依 Step ID
}
```

### 3.2 ADB 多實例設定 (ADB Multi-Instance Config)
- **Default Port**: `127.0.0.1:5555` (BS4 第一開)
- **Secondary Ports**: `127.0.0.1:5557`, `127.0.0.1:5559` ...

---

## 4. 自主驗收與綠燈標準 (Self-Verification Criteria)

代碼變更在交付人類實機 GUI 驗收前，必須符合以下品質指標：

1. **靜態檢查**：無 Python 語法錯誤或匯入缺失。
2. **Parser 單元測試**：確保各種 SET 軸文本格式皆能精確解析出正確的毫秒/秒數與 `OOOOO` 陣列狀態。
3. **ADB 通訊測試**：確保 ADB 通訊與 tap 命令發送穩定無阻害。
4. **辨識速度標準**：單影格時間 OCR 與 SET 色彩比對延遲低於 15 ms。
