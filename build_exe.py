import subprocess
import sys
import os

def build():
    print("正開始打包 PCRD Battle Hub 5-Step SOP 版 v4 (.exe)...")
    
    try:
        import PyInstaller
    except ImportError:
        print("未安裝 PyInstaller，正自動安裝中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=PCRD_Battle_Hub_v4",
        "--add-data=src/web/templates;src/web/templates",
        "--add-data=src/web/static;src/web/static",
        "--add-data=config;config",
        "gui_app.py"
    ]

    print(f"執行指令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("\n[OK] 打包完成！獨立 App 可執行檔位於 dist/PCRD_Battle_Hub_v4/PCRD_Battle_Hub_v4.exe")

if __name__ == '__main__':
    build()
