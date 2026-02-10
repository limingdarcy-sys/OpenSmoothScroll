"""
OpenSmoothScroll - 主程式入口
一套取代 SmoothScroll 的 Windows 系統級平滑捲動工具。

使用方式：
    python main.py          # 啟動系統匣常駐程式
    python main.py --ui     # 直接開啟設定視窗（調試用）

功能：
    - 全域攔截滑鼠滾輪事件，實現平滑捲動
    - 可調整步幅、動畫時間、加速度等參數
    - 支援 Shift+滾輪水平捲動
    - 支援反向滾輪
    - 自訂緩動曲線（考慮 tail/head 比例）
    - 系統匣常駐，右鍵選單快速操作

作者：OpenSmoothScroll
授權：MIT
"""

import sys
import os
import ctypes

# 確保程式在 Windows 上執行
if sys.platform != "win32":
    print("[錯誤] OpenSmoothScroll 僅支援 Windows 作業系統。")
    sys.exit(1)


def is_admin() -> bool:
    """檢查是否以管理員身份執行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main():
    """主程式入口"""
    # 命令列參數處理
    if "--ui" in sys.argv:
        # 直接開啟設定視窗（調試模式）
        from config import load_settings
        from settings_ui import SettingsWindow
        settings = load_settings()
        window = SettingsWindow(settings=settings)
        window.show()
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("命令列選項：")
        print("  --ui      直接開啟設定視窗")
        print("  --help    顯示此說明")
        return

    # 單實例鎖定
    from utils import acquire_single_instance_lock, release_single_instance_lock

    if not acquire_single_instance_lock():
        print("[警告] OpenSmoothScroll 已在執行中，請勿重複啟動。")
        # 嘗試用訊息框通知使用者
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "OpenSmoothScroll 已在執行中！\n請檢查系統匣圖示。",
                "OpenSmoothScroll",
                0x40  # MB_ICONINFORMATION
            )
        except Exception:
            pass
        sys.exit(0)

    # 啟動系統匣應用
    from tray_app import TrayApp

    print("=" * 50)
    print("  OpenSmoothScroll v1.0")
    print("  Windows 系統級平滑捲動工具")
    print("=" * 50)

    if not is_admin():
        print("[警告] 建議以管理員身份執行以獲得最佳相容性。")
        print("       某些應用程式可能需要管理員權限才能攔截捲動事件。")
        print()

    app = TrayApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[資訊] 收到中斷信號，正在關閉...")
        app._quit()
    finally:
        release_single_instance_lock()


if __name__ == "__main__":
    main()
