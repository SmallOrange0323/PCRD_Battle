# PCRD Battle Hub — 技術問題與修復建議參考手冊

本文件由獨立技術評估報告彙整而成，記錄現階段所有已知問題、根本原因與建議修法。
**整體可用度評估：約 15~20%（架構展示階段，尚不具備實戰能力）**

---

## 一、 問題總覽速查表

| 優先度 | 模組 | 問題摘要 | 類型 |
|:---:|:---|:---|:---:|
| 🔴 P0 | 全系統 | 沒有背景驅動主迴圈，「啟動」後什麼都不會發生 | Blocker |
| 🔴 P0 | `adb_controller.py` | 每次 tap 都 spawn 新行程，延遲 100~300ms/次，多 SET 切換累積 0.5 秒 | Blocker |
| 🔴 P0 | `timer_ocr.py` | OCR 完全是 Fake，永遠回傳固定值 `("1:12", 72)` | Blocker |
| 🟠 P1 | `state_machine.py` | Line 57 的邏輯吃掉超時判定，Line 74 超時診斷是 Dead Code | Logic Bug |
| 🟠 P1 | `set_detector.py` | 僅用平均亮度判定 ON/OFF，UB 閃光效果會大量誤判 | 誤判風險 |
| 🟡 P2 | `diagnostics.py` | `record_order_mismatch` / `record_character_rip` 完全沒有呼叫來源 | 孤兒程式碼 |
| 🟡 P2 | `app.py` | `/api/start_task` 僅建立物件就回傳，沒有啟動背景 Thread | 功能失效 |
| 🟡 P2 | `tests/` | 測試全部通過，但測試內容幾乎都是假的（傳 Mock 資料） | 虛假綠燈 |

---

## 二、 各問題詳細說明與修法

---

### 🔴 [P0] 問題 1：缺少背景驅動主迴圈（最大 Blocker）

**影響檔案**：`main.py`、`src/web/app.py`、`src/engine/state_machine.py`

**問題說明**：
系統目前就像一台發動不了的車。`main.py` 只是建立物件後直接 Exit，`/api/start_task` 建立 `BattleStateMachine` 後就回傳 JSON 結果，背景完全靜止。沒有任何 Thread 在持續執行：截圖 → 辨識 → 狀態機推進 → ADB 點擊的驅動循環。

**建議修法**：
新增 `src/engine/battle_worker.py`，實作 `BattleWorker(threading.Thread)`：

```python
class BattleWorker(threading.Thread):
    def __init__(self, adb, timer_ocr, set_detector, state_machine):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set() and not self.state_machine.is_finished:
            frame_bytes = self.adb.capture_frame_bytes()
            if frame_bytes is None:
                time.sleep(0.05)
                continue

            frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
            _, current_seconds = self.timer_ocr.parse_time_from_roi(frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2])
            current_set = self.set_detector.detect_p1_to_p5_set(frame, SET_COORDS)
            self.state_machine.process_frame(current_seconds, current_set)
```

> [!IMPORTANT]
> `/api/start_task` 需改為啟動此 Thread 並保存其參照，另外新增 `/api/stop_task` 對應停止。

---

### 🔴 [P0] 問題 2：ADB 通訊延遲過高

**影響檔案**：`src/controller/adb_controller.py` — Line 26, 62, 79, 90~102

**問題說明**：
每次 `tap()` 都呼叫 `subprocess.run(["adb", "-s", ...])` 啟動一個全新系統行程，Windows 環境下延遲約 **100~300ms 每次**。一次需要點擊 3 個 SET 按鈕就累積 **0.3~0.9 秒延遲**。截圖部分（`exec-out screencap -p`）更糟，單次耗時 **300ms~1000ms**，實際只有 **1~3 FPS**。

**建議修法**：
改用 `ppadb`（pure-python-adb）維持 Socket 長連線：

```bash
pip install pure-python-adb
```

```python
from ppadb.client import Client as AdbClient

class ADBController:
    def connect(self):
        client = AdbClient(host="127.0.0.1", port=5037)
        self.device = client.device(f"{self.host}:{self.port}")

    def tap(self, x, y):
        self.device.shell(f"input tap {x} {y}")  # 延遲 < 10ms

    def capture_frame_bytes(self) -> bytes:
        return self.device.screencap()  # 比 subprocess 快且穩定
```

> [!NOTE]
> 截圖仍約 150~300ms，是 ADB 架構的硬上限。若未來需要更快速的截圖（< 50ms），需考慮引入 `scrcpy` 影像串流，但維護複雜度較高，建議先以 `ppadb.screencap()` 為基礎跑通後再評估。

---

### 🔴 [P0] 問題 3：TimerOCR 是假的 (Hardcoded Mock)

**影響檔案**：`src/vision/timer_ocr.py` — Line 44~46, Line 94~96

**問題說明**：
全專案從未載入任何真實數字圖片樣板，`parse_time_from_roi` 永遠走進 `_fallback_parse`，永遠回傳固定的 `("1:12", 72)`，數字辨識從未實際運作過。

另外 Line 62 的雜訊過濾 `if w < 3 or h < 8:` 會把冒號 `:` 的兩個小圓點也過濾掉，即使有樣板也無法辨識出分隔符。

**建議修法（二選一）**：

**選項 A：EasyOCR（不需準備樣板，立即可用）**
```bash
pip install easyocr
```
```python
import easyocr
reader = easyocr.Reader(['en'], gpu=False)

def parse_time(roi_img):
    results = reader.readtext(roi_img, allowlist='0123456789:')
    for _, text, conf in results:
        if ':' in text and conf > 0.7:
            m, s = map(int, text.split(':'))
            return text, m * 60 + s
    return None, -1
```
- 優點：零樣板準備，立即可用
- 缺點：首次初始化約 3~5 秒，每次辨識約 50~150ms

**選項 B：OpenCV 數字樣板比對（最快，約 1~3ms，但需準備樣板圖）**
- 從 BS4 真實戰鬥截圖中手動裁出 0~9 數字各一張，存到 `assets/digits/`
- `TimerOCR` 啟動時載入並快取這些樣板

> [!IMPORTANT]
> 選項 B 需要您提供真實的 BS4 遊戲截圖，用來裁出數字樣板。建議先用選項 A 跑通後，再換成 B 提升速度。

---

### 🟠 [P1] 問題 4：state_machine.py 超時保護是 Dead Code

**影響檔案**：`src/engine/state_machine.py` — Line 57, Line 74

**問題說明**：
```python
# Line 57 — 此條件把「已超時」的情況也吃掉了
if current_seconds <= step.time_seconds:
    # 68 <= 72 為 True，即使已超時也觸發 SET 切換 ← 錯誤

# Line 74 — 永遠執行不到（Dead Code）
if current_seconds < (step.time_seconds - 2):
    # 超時診斷與自動暫停保護 ← 完全失靈
```

**建議修法**：
```python
def process_frame(self, current_seconds: int, current_set: List[bool]) -> bool:
    step = self.get_current_step()
    if not step or self.is_finished:
        return False

    # 先判斷超時（必須放在正常觸發之前）
    if current_seconds < (step.time_seconds - 2):
        self.diagnostics.record_timeout_no_ub(...)
        self.adb.tap(*self.pause_coord)  # 自動暫停保護
        self.current_step_idx += 1
        return False

    # 時間進入觸發窗口
    if current_seconds <= step.time_seconds:
        self.adb.toggle_set_diff(current_set, step.target_set, self.set_coords)
        self.current_step_idx += 1
        return True

    return False  # 還沒到時間，等待
```

---

### 🟠 [P1] 問題 5：SET 燈號辨識受特效干擾

**影響檔案**：`src/vision/set_detector.py` — Line 26~31

**問題說明**：
`is_on = (mean_v > 140) or (mean_s > 80)` 僅用平均 HSV 亮度/彩度判斷。角色釋放 UB 的全螢幕白色閃光或 Boss 技能特效會讓畫面瞬間提亮，把 OFF 的按鈕誤判為 ON。

**建議修法**：
- 加入**時序穩定機制**：只有連續 3 幀以上都判斷為同一狀態，才正式認定為切換，過濾單幀閃光誤判。
- 或改用 **圖片樣板比對 (`cv2.matchTemplate`)**：準備 SET ON 與 OFF 的按鈕圖片，以相似度分數而非平均亮度作為判斷依據。

---

### 🟡 [P2] 問題 6：測試都是虛假綠燈

**影響檔案**：`tests/` 全部

**問題說明**：
- `test_vision.py`：驗證 `TimerOCR` fallback 回傳 `"1:12"` 通過，但這只是驗證假 Mock，毫無實戰意義。
- `test_adb.py`：只測試 Python List 差集邏輯，沒有測試 ADB 指令發送或 Timeout 處理。
- `test_engine.py`：完全沒有測試超時情境，因此沒有抓到 Dead Code Bug。

**修復後需補充的測試情境**：
```python
def test_timeout_triggers_pause_not_trigger(self):
    """超時時應記錄事故並暫停，不應執行正常 SET 切換"""
    sm = BattleStateMachine(steps=[step_at_72s], ...)
    sm.process_frame(current_seconds=65, current_set=[True]*5)
    self.assertEqual(sm.diagnostics.anomalies[0].anomaly_type, "TIMEOUT_NO_UB")
    self.assertEqual(sm.current_step_idx, 1)  # 步驟應被跳過
    self.assertNotEqual(sm.current_set, step_at_72s.target_set)  # SET 不應被切換
```

---

## 三、 修復優先順序

```
Phase 1（讓系統真正能跑）：
  ├── 安裝 ppadb，重寫 ADBController 連線機制
  ├── 修復 state_machine.py 的超時判斷 Dead Code Bug
  └── 實作 BattleWorker 背景驅動主迴圈

Phase 2（讓系統能真正辨識）：
  ├── 選擇 OCR 策略（EasyOCR 或樣板比對）並實作
  └── 改善 SETDetector 加入時序穩定機制或樣板比對

Phase 3（讓系統可靠穩定）：
  ├── 補全真實情境的單元測試（含超時、誤觸等邊界條件）
  └── 整合 BattleWorker 與 /api/start_task, /api/stop_task
```

---

## 四、 需要使用者配合的事項

| 項目 | 說明 | 需要您做什麼 |
|:---|:---|:---|
| OCR 策略決定 | 選項 A (EasyOCR) 或 選項 B (樣板比對) | 告知選哪個 |
| 數字樣板圖片 | 若選擇 B，需要真實截圖 | 提供 BS4 戰鬥畫面截圖 |
| ppadb 安裝 | 取代 subprocess ADB 呼叫 | 執行 `pip install pure-python-adb` |
| 暫停按鈕座標 | 確認 1280x720 畫面中暫停按鈕的實際位置 | 在 `config/settings.json` 中校正 |

---

*本文件由 PCRD Battle Hub 技術評估報告彙整 — 2026-07-21*
