import os
import sys
import time
import threading
import subprocess
import webbrowser
from src.web.app import app

def run_flask():
    """在背景執行 Flask API 服務"""
    app.run(host='127.0.0.1', port=5000, debug=False)

def main():
    logger_msg = "正啟動 PCRD Battle Hub 獨立桌面應用程式..."
    print(logger_msg)

    # 1. 在背景背景執行緒啟動 Web 服務
    server_thread = threading.Thread(target=run_flask, daemon=True)
    server_thread.start()
    
    time.sleep(1.2)  # 等待伺服器啟動

    target_url = "http://127.0.0.1:5000"

    # 2. 嘗試使用 Edge / Chrome 的 App 模式開啟 (獨立獨立視窗，無選單與網址列)
    app_launched = False
    browsers = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]

    for browser_path in browsers:
        if os.path.exists(browser_path):
            try:
                subprocess.Popen([
                    browser_path,
                    f"--app={target_url}",
                    "--window-size=1380,880",
                    "--window-position=100,50"
                ])
                app_launched = True
                print(f"已使用原生 App 模式開啟獨立視窗: {browser_path}")
                break
            except Exception as e:
                print(f"啟動 App 視窗失敗: {e}")

    # 若無 App 模式，則使用預設瀏覽器開啟
    if not app_launched:
        webbrowser.open(target_url)

    print("桌面 App 執行中，若要結束請關閉此視窗。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程式已停止。")

if __name__ == '__main__':
    main()
