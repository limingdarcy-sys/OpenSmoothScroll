"""
OpenSmoothScroll - 系統匣應用模組
管理系統匣圖示、右鍵選單，以及程式的整體生命週期。

架構說明：
  - 主線程：tkinter 事件迴圈（隱藏根視窗）
  - 背景線程：pystray 系統匣圖示
  - 設定視窗以 Toplevel 方式在主線程開啟
"""

import tkinter as tk
import threading
import os
import sys
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from config import ScrollSettings, load_settings, save_settings
from settings_ui import SettingsWindow
from smooth_scroll_engine import SmoothScrollEngine
from utils import is_startup_enabled, toggle_startup


def create_tray_icon_image() -> Image.Image:
    """建立系統匣圖示（程式碼繪製，無需外部檔案）"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 背景圓角矩形
    bg_color = (124, 92, 252)  # 主題紫色
    draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill=bg_color)

    # 白色滾輪圖示
    arrow_color = (255, 255, 255)
    center_x = size // 2

    # 上箭頭
    for i in range(5):
        draw.rectangle([center_x - i - 1, 16 + i, center_x + i + 1, 17 + i],
                       fill=arrow_color)

    # 下箭頭
    for i in range(5):
        draw.rectangle([center_x - i - 1, 47 - i, center_x + i + 1, 48 - i],
                       fill=arrow_color)

    # 波浪線（代表平滑）
    for i in range(center_x - 12, center_x + 12, 2):
        y_offset = 2 if (i // 4) % 2 == 0 else -2
        draw.rectangle([i, center_x + y_offset - 1, i + 1, center_x + y_offset + 1],
                       fill=arrow_color)

    return img


class TrayApp:
    """系統匣應用程式主類別"""

    def __init__(self):
        self.settings = load_settings()
        self.engine = SmoothScrollEngine(self.settings)
        self.engine.set_status_callback(self._on_engine_status_change)

        self._tray_icon: Optional[pystray.Icon] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._tk_root: Optional[tk.Tk] = None

    def run(self) -> None:
        """啟動系統匣應用"""
        # ── 主線程：建立隱藏的 tkinter 根視窗 ──
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()  # 隱藏根視窗

        # ── 背景線程：啟動系統匣圖示 ──
        tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        tray_thread.start()

        # 自動啟動引擎
        if self.settings.enabled:
            self.engine.start()

        print("[資訊] OpenSmoothScroll 已啟動，常駐於系統匣")

        # ── 主線程：tkinter 事件迴圈 ──
        self._tk_root.mainloop()

    def _run_tray(self) -> None:
        """在背景線程中執行系統匣圖示"""
        icon_image = create_tray_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem(
                "OpenSmoothScroll",
                None,
                enabled=False,
                default=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: "✅ 已啟用" if self.engine.is_running else "❌ 已停用",
                self._toggle_engine,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙ 設定...", self._open_settings, default=True),
            pystray.MenuItem(
                lambda item: "✅ 開機啟動" if is_startup_enabled() else "⬜ 開機啟動",
                self._toggle_startup,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🚪 結束", self._quit),
        )

        self._tray_icon = pystray.Icon(
            "OpenSmoothScroll",
            icon_image,
            "OpenSmoothScroll - 平滑捲動",
            menu
        )

        self._tray_icon.run()

    def _toggle_engine(self, icon=None, item=None) -> None:
        """切換引擎開關"""
        new_state = self.engine.toggle()
        self.settings.enabled = new_state
        save_settings(self.settings)

        # 更新匣圖示提示文字
        if self._tray_icon:
            state_text = "已啟用" if new_state else "已停用"
            self._tray_icon.title = f"OpenSmoothScroll - {state_text}"
            self._tray_icon.update_menu()

    def _toggle_startup(self, icon=None, item=None) -> None:
        """切換開機啟動"""
        new_state = toggle_startup()
        state_text = "已啟用" if new_state else "已停用"
        print(f"[資訊] 開機啟動{state_text}")
        if self._tray_icon:
            self._tray_icon.update_menu()

    def _open_settings(self, icon=None, item=None) -> None:
        """開啟設定視窗（排程到主線程執行）"""
        if self._tk_root:
            self._tk_root.after(0, self._show_settings_on_main_thread)

    def _show_settings_on_main_thread(self) -> None:
        """在主線程中建立並顯示設定視窗"""
        if not self._settings_window:
            self._settings_window = SettingsWindow(
                settings=self.settings,
                on_save=self._on_settings_save,
                on_toggle_engine=self._toggle_engine_from_ui,
                engine_running=self.engine.is_running
            )
        self._settings_window.show(parent=self._tk_root)

    def _toggle_engine_from_ui(self) -> bool:
        """從 UI 切換引擎（回傳新狀態）"""
        new_state = self.engine.toggle()
        self.settings.enabled = new_state
        save_settings(self.settings)

        if self._tray_icon:
            state_text = "已啟用" if new_state else "已停用"
            self._tray_icon.title = f"OpenSmoothScroll - {state_text}"
            self._tray_icon.update_menu()

        return new_state

    def _on_settings_save(self, new_settings: ScrollSettings) -> None:
        """設定儲存回呼"""
        self.settings = new_settings
        self.engine.update_settings(new_settings)
        print("[資訊] 設定已更新")

    def _on_engine_status_change(self, running: bool) -> None:
        """引擎狀態變更回呼"""
        if self._settings_window:
            self._settings_window.update_engine_status(running)

    def _quit(self, icon=None, item=None) -> None:
        """結束程式"""
        print("[資訊] 正在關閉 OpenSmoothScroll...")

        # 停止引擎
        self.engine.stop()

        # 停止系統匣
        if self._tray_icon:
            self._tray_icon.stop()

        # 在主線程中安全關閉 tkinter
        if self._tk_root:
            self._tk_root.after(0, self._shutdown_tk)

    def _shutdown_tk(self) -> None:
        """在主線程中安全關閉 tkinter 並結束程式"""
        try:
            # 關閉設定視窗
            if self._settings_window and self._settings_window.root:
                self._settings_window._on_close()

            # 銷毀隱藏的根視窗（結束 mainloop）
            if self._tk_root:
                self._tk_root.destroy()
        except Exception:
            pass
        finally:
            os._exit(0)
