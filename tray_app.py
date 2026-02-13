"""
OpenSmoothScroll - 系統匣應用模組
管理系統匣圖示、右鍵選單，以及程式的整體生命週期。

架構說明：
  - 主線程：tkinter 事件迴圈（隱藏根視窗）
  - 背景線程：pystray 系統匣圖示
  - 背景線程：全域快捷鍵監聽（RegisterHotKey）
  - 設定視窗以 Toplevel 方式在主線程開啟
"""

import tkinter as tk
import threading
import ctypes
import ctypes.wintypes as wintypes
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
    """
    建立系統匣圖示。
    優先嘗試載入 'icon.ico'，若不存在則動態繪製。
    """
    try:
        from utils import get_resource_path
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            # 載入 ICO 並轉換為 RGBA 圖像
            return Image.open(icon_path).convert("RGBA")
    except Exception as e:
        print(f"[警告] 載入 icon.ico 失敗，使用預設圖示: {e}")

    # Fallback: 動態繪製 (解析度提高到 128)
    size = 128
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 背景圓角矩形
    padding = 8
    radius = 24
    bg_color = (124, 92, 252)  # #7c5cfc 主題紫色
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=bg_color
    )

    # 白色圖示（箭頭 + 波浪）
    arrow_color = (255, 255, 255)
    center_x = size // 2
    center_y = size // 2

    # 線條粗細
    stroke = 6

    # 上箭頭
    arrow_w = 24
    arrow_h = 12
    draw.polygon([
        (center_x, center_y - arrow_h * 2 - 10),
        (center_x - arrow_w, center_y - arrow_h - 10),
        (center_x + arrow_w, center_y - arrow_h - 10)
    ], fill=arrow_color)

    # 下箭頭
    draw.polygon([
        (center_x, center_y + arrow_h * 2 + 10),
        (center_x - arrow_w, center_y + arrow_h + 10),
        (center_x + arrow_w, center_y + arrow_h + 10)
    ], fill=arrow_color)

    # 中間波浪線 (簡化為直線以確保清晰，或使用更平滑的波浪)
    wave_len = 48
    draw.line(
        [(center_x - wave_len, center_y), (center_x + wave_len, center_y)],
        fill=arrow_color,
        width=stroke
    )

    return img


# ── Win32 常數 ──
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID_TOGGLE = 1

# 特殊鍵名稱對應 Virtual Key Code
SPECIAL_VK_MAP = {
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B,
    'home': 0x24, 'end': 0x23, 'insert': 0x2D, 'delete': 0x2E,
    'pageup': 0x21, 'pagedown': 0x22,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'pause': 0x13, 'capslock': 0x14, 'numlock': 0x90,
}


def parse_hotkey(hotkey_str: str) -> tuple:
    """
    解析快捷鍵字串為 (modifiers, virtual_key_code)
    例如： 'ctrl+alt+shift+s' → (MOD_CONTROL | MOD_ALT | MOD_SHIFT, 0x53)
    """
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    modifiers = MOD_NOREPEAT  # 防止按住不放時重複觸發
    vk = 0

    for part in parts:
        if part in ('ctrl', 'control'):
            modifiers |= MOD_CONTROL
        elif part in ('alt', 'menu'):
            modifiers |= MOD_ALT
        elif part == 'shift':
            modifiers |= MOD_SHIFT
        elif part in ('win', 'windows', 'super'):
            modifiers |= MOD_WIN
        elif part in SPECIAL_VK_MAP:
            vk = SPECIAL_VK_MAP[part]
        elif len(part) == 1 and part.isalnum():
            # 單一字母或數字
            vk = ord(part.upper())
        else:
            print(f"[警告] 無法辨識的快捷鍵組件: '{part}'")

    return modifiers, vk


class TrayApp:
    """系統匣應用程式主類別"""

    def __init__(self):
        self.settings = load_settings()
        self.engine = SmoothScrollEngine(self.settings)
        self.engine.set_status_callback(self._on_engine_status_change)

        self._tray_icon: Optional[pystray.Icon] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._tk_root: Optional[tk.Tk] = None
        self._hotkey_thread_id: Optional[int] = None  # 快捷鍵線程 ID（用於退出時傳送 WM_QUIT）

    def run(self) -> None:
        """啟動系統匣應用"""
        # ── 主線程：建立隱藏的 tkinter 根視窗 ──
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()  # 隱藏根視窗

        # ── 背景線程：啟動系統匣圖示 ──
        tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        tray_thread.start()

        # ── 背景線程：啟動全域快捷鍵監聽 ──
        hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)
        hotkey_thread.start()

        # 自動啟動引擎
        if self.settings.enabled:
            self.engine.start()

        print("[資訊] OpenSmoothScroll 已啟動，常駐於系統匣")
        print(f"[資訊] 快捷鍵: {self.settings.hotkey.upper()} （切換啟用/停用）")

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

    def _hotkey_listener(self) -> None:
        """在背景線程中監聽全域快捷鍵（使用 Win32 RegisterHotKey）"""
        # 記錄線程 ID，退出時需要向這個線程傳送 WM_QUIT
        self._hotkey_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        modifiers, vk = parse_hotkey(self.settings.hotkey)

        if vk == 0:
            print("[警告] 快捷鍵設定無效，快捷鍵功能未啟用")
            return

        # 註冊全域快捷鍵
        success = ctypes.windll.user32.RegisterHotKey(
            None, HOTKEY_ID_TOGGLE, modifiers, vk
        )
        if not success:
            print(f"[警告] 快捷鍵 {self.settings.hotkey.upper()} 註冊失敗（可能已被其他程式佔用）")
            return

        print(f"[資訊] 快捷鍵 {self.settings.hotkey.upper()} 已註冊")

        # 訊息迴圈：等待 WM_HOTKEY
        msg = wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID_TOGGLE:
                # 快捷鍵觸發 → 排程到主線程切換引擎
                if self._tk_root:
                    self._tk_root.after(0, self._toggle_engine)

        # 迴圈結束（收到 WM_QUIT），取消註冊
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)

    def _quit(self, icon=None, item=None) -> None:
        """結束程式"""
        print("[資訊] 正在關閉 OpenSmoothScroll...")

        # 停止引擎
        self.engine.stop()

        # 停止快捷鍵監聽線程
        if self._hotkey_thread_id:
            ctypes.windll.user32.PostThreadMessageW(
                self._hotkey_thread_id, WM_QUIT, 0, 0
            )

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
