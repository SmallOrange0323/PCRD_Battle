import subprocess
import time
import logging
import sys
from typing import List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ADBController")

# Windows 無視窗標籤
NO_WINDOW_FLAG = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

try:
    from ppadb.client import Client as AdbClient
    HAS_PPADB = True
except ImportError:
    HAS_PPADB = False
    logger.warning("未偵測到 pure-python-adb (ppadb)，ADB 控制器將使用傳統 subprocess 模式 (延遲較高)。建議執行 `pip install pure-python-adb` 以取得最佳效能。")

class ADBController:
    """
    ADB 多實例控制器
    優先使用 pure-python-adb (ppadb)Socket 長連線降低延遲，否則降級使用 subprocess
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5555, adb_path: str = "adb"):
        self.host = host
        self.port = port
        self.device_address = f"{host}:{port}"
        self.adb_path = adb_path
        self.is_connected = False
        
        self._ppadb_device = None

    @classmethod
    def discover_bluestacks_ports(cls) -> List[int]:
        """
        全自動探測 Windows 系統中目前由 HD-Player / BlueStacks 核心開啟 Listening 的 TCP Ports
        """
        discovered_ports = set()
        cmd = ["powershell", "-Command", "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess"]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, creationflags=NO_WINDOW_FLAG)
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                for line in lines[2:]:
                    parts = line.strip().split()
                    if len(parts) >= 1 and parts[0].isdigit():
                        port = int(parts[0])
                        if 5555 <= port <= 5999 or 5000 <= port <= 9000:
                            discovered_ports.add(port)
        except Exception as e:
            logger.warning(f"自動探測廣域 Ports 異常: {e}")

        for p in [5555, 5557, 5559, 5561, 5563, 5695]:
            discovered_ports.add(p)

        return sorted(list(discovered_ports))

    @classmethod
    def ensure_server_running(cls, adb_path: str = "adb"):
        """確保 ADB Server 正處於啟動狀態"""
        try:
            subprocess.run([adb_path, "start-server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, creationflags=NO_WINDOW_FLAG)
        except Exception as e:
            logger.error(f"啟動 ADB Server 失敗: {e}")

    @classmethod
    def get_online_devices(cls, adb_path: str = "adb") -> List[str]:
        """
        自動嘗試探測並連接所有廣域探測到的 ADB Ports，並回傳真實已連線的設備位址
        """
        cls.ensure_server_running(adb_path)
        
        candidate_ports = cls.discover_bluestacks_ports()
        for p in candidate_ports:
            try:
                subprocess.run([adb_path, "connect", f"127.0.0.1:{p}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, creationflags=NO_WINDOW_FLAG)
            except Exception:
                pass

        try:
            res = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, creationflags=NO_WINDOW_FLAG)
            lines = res.stdout.strip().splitlines()
            online_devices = []
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    online_devices.append(parts[0])
            return online_devices
        except Exception as e:
            logger.error(f"取得 ADB 設備列表失敗: {e}")
            return []

    def connect(self) -> bool:
        """嘗試連接模擬器 ADB 埠並精確驗證連線狀態"""
        self.ensure_server_running(self.adb_path)

        online = self.get_online_devices(self.adb_path)
        if self.device_address in online or f"emulator-{self.port}" in online:
            self.is_connected = True
            logger.info(f"✅ ADB 已處於連線狀態 [{self.device_address}]")
            self._init_ppadb()
            return True

        cmd = [self.adb_path, "connect", self.device_address]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, creationflags=NO_WINDOW_FLAG)
            output = res.stdout.strip()
            logger.info(f"ADB connect 回應 [{self.device_address}]: {output}")
        except Exception as e:
            logger.error(f"連線至 ADB [{self.device_address}] 異常: {e}")

        online_after = self.get_online_devices(self.adb_path)
        if self.device_address in online_after or f"emulator-{self.port}" in online_after:
            self.is_connected = True
            logger.info(f"⚡ ADB 連線成功 [{self.device_address}]")
            self._init_ppadb()
            return True
        else:
            self.is_connected = False
            logger.warning(f"❌ ADB 連線失敗 [{self.device_address}]")
            return False

    def _init_ppadb(self):
        """若環境支援 ppadb，嘗試初始化長連線物件"""
        if HAS_PPADB and self._ppadb_device is None:
            try:
                client = AdbClient(host="127.0.0.1", port=5037)
                device = client.device(self.device_address)
                if device is not None:
                    self._ppadb_device = device
                    logger.info(f"⚡ ppadb Socket 長連線初始化完成 [{self.device_address}]")
            except Exception as e:
                logger.warning(f"ppadb 初始化失敗，降級使用 subprocess: {e}")

    def run_adb_cmd(self, args: List[str], timeout: int = 5) -> str:
        """執行 adb 視窗指令並回傳字串輸出"""
        full_cmd = [self.adb_path, "-s", self.device_address] + args
        try:
            result = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
                creationflags=NO_WINDOW_FLAG
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"ADB 命令逾時: {' '.join(full_cmd)}")
            return ""
        except Exception as e:
            logger.error(f"ADB 執行異常: {e}")
            return ""

    def tap(self, x: int, y: int):
        """在指定點發送 ADB 點擊事件 (Background Tap)"""
        if self._ppadb_device:
            try:
                self._ppadb_device.shell(f"input tap {x} {y}")
                return
            except Exception as e:
                logger.error(f"ppadb tap 失敗: {e}")

        # Fallback
        self.run_adb_cmd(["shell", "input", "tap", str(x), str(y)])

    def tap_set_button(self, position_index: int, set_coords: List[Tuple[int, int]]):
        """
        點擊 P1~P5 指定角色的 SET 按鈕 (position_index 0 ~ 4)
        """
        if 0 <= position_index < len(set_coords):
            x, y = set_coords[position_index]
            self.tap(x, y)
            logger.info(f"[{self.device_address}] 點擊 SET P{position_index + 1} 座標 ({x}, {y})")

    def toggle_set_diff(self, current_set: List[bool], target_set: List[bool], set_coords: List[Tuple[int, int]]):
        """
        比對當前 SET 狀態與目標 SET 狀態，僅點擊差異按鈕 (增量切換)
        """
        for i in range(5):
            if current_set[i] != target_set[i]:
                self.tap_set_button(i, set_coords)

    def set_auto(self, target_auto: bool, current_auto: Optional[bool], auto_coord: Tuple[int, int]):
        """
        若標的 AUTO 與當前不符，點擊切換 AUTO 開關
        """
        if current_auto is None or current_auto != target_auto:
            x, y = auto_coord
            self.tap(x, y)
            logger.info(f"[{self.device_address}] 切換 AUTO -> {'ON' if target_auto else 'OFF'}")

    def capture_frame_bytes(self) -> Optional[bytes]:
        """
        經由 ADB screencap 抓取當前畫面 (PNG 格式 bytes)
        """
        if self._ppadb_device:
            try:
                return self._ppadb_device.screencap()
            except Exception as e:
                logger.error(f"ppadb screencap 失敗: {e}")

        full_cmd = [self.adb_path, "-s", self.device_address, "exec-out", "screencap", "-p"]
        try:
            res = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, creationflags=NO_WINDOW_FLAG)
            if res.returncode == 0 and res.stdout:
                return res.stdout
            return None
        except Exception as e:
            logger.error(f"[{self.device_address}] 畫面截取失敗: {e}")
            return None

    def resume_game(self, resume_coord: Tuple[int, int] = (350, 840)):
        """
        取消戰鬥暫停 (繼續戰鬥)：點擊選單左下角藍色【返回】按鈕 (350, 840)
        """
        x, y = resume_coord
        self.tap(x, y)
        logger.info(f"[{self.device_address}] 點擊選單藍色【返回】解暫停座標 ({x}, {y})")
