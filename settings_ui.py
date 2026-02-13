"""
OpenSmoothScroll - 設定介面
使用 tkinter 搭配自訂美化，打造現代化的設定面板。
"""

import tkinter as tk
from tkinter import ttk, font as tkfont, filedialog, messagebox
import sys
import os
import ctypes
import ctypes.wintypes
from typing import Callable, Optional, List

from config import ScrollSettings, save_settings, reset_settings


# ─── 色彩系統（深色主題）────────────────────────────────────────────
class Colors:
    """現代深色主題配色"""
    BG_DARK = "#0f0f14"            # 最深背景
    BG_MAIN = "#16161e"            # 主背景
    BG_CARD = "#1e1e2e"            # 卡片背景
    BG_CARD_HOVER = "#252540"      # 卡片懸停
    BG_INPUT = "#2a2a3e"           # 輸入框背景
    BG_SLIDER_TRACK = "#2a2a3e"    # 滑桿軌道

    TEXT_PRIMARY = "#e4e4ef"        # 主要文字
    TEXT_SECONDARY = "#8888a0"      # 次要文字
    TEXT_MUTED = "#5a5a72"          # 淡化文字

    ACCENT = "#7c5cfc"             # 主題色（紫色）
    ACCENT_HOVER = "#9578ff"       # 主題色懸停
    ACCENT_GLOW = "#7c5cfc40"      # 主題色光暈

    SUCCESS = "#4ade80"            # 成功/啟用
    WARNING = "#fb923c"            # 警告
    DANGER = "#f87171"             # 危險/停用

    BORDER = "#2a2a3e"             # 邊框
    BORDER_FOCUS = "#7c5cfc"       # 焦點邊框

    TOGGLE_ON = "#7c5cfc"          # 開關開啟
    TOGGLE_OFF = "#3a3a4e"         # 開關關閉
    TOGGLE_KNOB = "#ffffff"        # 開關旋鈕


class SettingsWindow:
    """設定視窗主類別"""

    def __init__(self, settings: ScrollSettings, on_save: Optional[Callable] = None,
                 on_toggle_engine: Optional[Callable] = None,
                 engine_running: bool = False):
        self.settings = settings
        self.on_save = on_save
        self.on_toggle_engine = on_toggle_engine
        self.engine_running = engine_running
        self.root: Optional[tk.Tk] = None
        self._standalone = False  # 是否為獨立模式（自己的 mainloop）
        self._sliders = {}
        self._toggles = {}

    def show(self, parent=None) -> None:
        """
        顯示設定視窗
        parent: 若傳入 tk.Tk 根視窗，則使用 Toplevel 並不呼叫 mainloop（附屬模式）
                若為 None，則建立獨立的 tk.Tk 視窗（獨立模式，用於 --ui 參數）
        """
        if self.root and self.root.winfo_exists():
            self.root.lift()
            self.root.focus_force()
            return

        # 決定模式
        if parent:
            self.root = tk.Toplevel(parent)
            self._standalone = False
        else:
            self.root = tk.Tk()
            self._standalone = True

        self.root.title("OpenSmoothScroll 設定")
        self.root.configure(bg=Colors.BG_DARK)
        self.root.resizable(False, True)  # 允許垂直拉伸

        # 視窗大小與位置（高度取螢幕 85% 與 960 的較小值）
        win_w = 520
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_h = min(960, int(screen_h * 0.85))
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.minsize(win_w, 400)

        # 設定視窗圖示（如果有）
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        from utils import get_resource_path
        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                 # 嘗試在上一層目錄找（開發環境 fallback）
                dev_path = os.path.join(os.path.dirname(__file__), "icon.ico")
                if os.path.exists(dev_path):
                     self.root.iconbitmap(dev_path)
        except Exception as e:
            print(f"[警告] 無法設定視窗圖示: {e}")

        # ── 設定 Windows 深色標題列 ──
        self._apply_dark_title_bar()

        # 配置 ttk 樣式
        self._setup_styles()

        # 建立 UI 元件
        self._build_ui()

        # 綁定關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 獨立模式才需要自己跑 mainloop
        if self._standalone:
            self.root.mainloop()

    def _apply_dark_title_bar(self) -> None:
        """使用 Windows DWM API 設定深色標題列並指定顏色"""
        try:
            # 需要先 update 才能取得正確的 HWND
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

            # 啟用深色模式（DWMWA_USE_IMMERSIVE_DARK_MODE = 20）
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark_mode = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode)
            )

            # 精確設定標題列顏色為 #0f0f14（DWMWA_CAPTION_COLOR = 35，Windows 11+）
            DWMWA_CAPTION_COLOR = 35
            # COLORREF 格式：0x00BBGGRR
            # #0f0f14 → R=0x0f, G=0x0f, B=0x14 → 0x00140f0f
            color = ctypes.c_int(0x00140f0f)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_CAPTION_COLOR,
                ctypes.byref(color),
                ctypes.sizeof(color)
            )

            # 強制重繪標題列
            self.root.withdraw()
            self.root.deiconify()
        except Exception:
            pass  # 較舊的 Windows 版本可能不支援

    def _setup_styles(self) -> None:
        """設定 ttk 樣式"""
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # 自訂 Scale (滑桿) 樣式
        style.configure("Custom.Horizontal.TScale",
                       background=Colors.BG_CARD,
                       troughcolor=Colors.BG_SLIDER_TRACK,
                       sliderthickness=18,
                       borderwidth=0)

    def _build_ui(self) -> None:
        """建構所有 UI 元件（使用可捲動容器）"""
        # 建立可捲動的外層容器
        outer_frame = tk.Frame(self.root, bg=Colors.BG_DARK)
        outer_frame.pack(fill="both", expand=True)

        # Canvas 用於實現捲動功能
        self._canvas = tk.Canvas(outer_frame, bg=Colors.BG_DARK,
                                  highlightthickness=0, borderwidth=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        # 自訂現代化捲軸
        self._scrollbar = ModernScrollbar(outer_frame, self._canvas)
        self._scrollbar.pack(side="right", fill="y")

        # 內容 Frame（放在 Canvas 內）
        main_frame = tk.Frame(self._canvas, bg=Colors.BG_DARK)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=main_frame, anchor="nw"
        )

        # 綁定內容尺寸變化事件
        main_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # 綁定滑鼠滾輪事件（在 Canvas 區域內可用滾輪捲動）
        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)

        # 內容區域加上邊距
        content_frame = tk.Frame(main_frame, bg=Colors.BG_DARK)
        content_frame.pack(fill="both", expand=True, padx=16, pady=12)

        # ── 標題區域 ──
        self._build_header(content_frame)

        # ── 狀態控制 ──
        self._build_status_control(content_frame)

        # ── 捲動參數區段 ──
        self._build_scroll_params(content_frame)

        # ── 功能開關區段 ──
        self._build_feature_toggles(content_frame)

        # ── 排除清單區段 ──
        self._build_blacklist_section(content_frame)

        # ── 底部按鈕列 ──
        self._build_footer(content_frame)

    def _build_header(self, parent: tk.Frame) -> None:
        """建構標題區域"""
        header = tk.Frame(parent, bg=Colors.BG_DARK)
        header.pack(fill="x", pady=(0, 12))

        title_label = tk.Label(
            header,
            text="⚙  OpenSmoothScroll",
            font=("Segoe UI", 18, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_DARK
        )
        title_label.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="讓你的滑鼠滾輪滑如絲綢 ✨",
            font=("Segoe UI", 10),
            fg=Colors.TEXT_SECONDARY,
            bg=Colors.BG_DARK
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_status_control(self, parent: tk.Frame) -> None:
        """建構狀態控制區"""
        card = self._create_card(parent)

        row = tk.Frame(card, bg=Colors.BG_CARD)
        row.pack(fill="x")

        # 狀態指示燈
        self._status_dot = tk.Canvas(row, width=12, height=12, bg=Colors.BG_CARD,
                                     highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 8))
        dot_color = Colors.SUCCESS if self.engine_running else Colors.DANGER
        self._status_dot.create_oval(1, 1, 11, 11, fill=dot_color, outline="")

        self._status_label = tk.Label(
            row,
            text="平滑捲動已啟用" if self.engine_running else "平滑捲動已停用",
            font=("Segoe UI", 11, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_CARD
        )
        self._status_label.pack(side="left")

        # 快捷鍵提示標籤
        hotkey_text = self.settings.hotkey.upper().replace("+", " + ")
        hotkey_badge = tk.Label(
            row,
            text=f"  {hotkey_text}  ",
            font=("Segoe UI", 8),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_INPUT,
            padx=6, pady=2
        )
        hotkey_badge.pack(side="left", padx=(10, 0))

        # 切換按鈕
        toggle_btn = tk.Label(
            row,
            text="  停用  " if self.engine_running else "  啟用  ",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg=Colors.ACCENT,
            cursor="hand2",
            padx=12, pady=4
        )
        toggle_btn.pack(side="right")
        toggle_btn.bind("<Button-1>", self._toggle_engine)
        toggle_btn.bind("<Enter>", lambda e: toggle_btn.configure(bg=Colors.ACCENT_HOVER))
        toggle_btn.bind("<Leave>", lambda e: toggle_btn.configure(bg=Colors.ACCENT))
        self._toggle_btn = toggle_btn

    def _build_scroll_params(self, parent: tk.Frame) -> None:
        """建構捲動參數設定區"""
        # 區段標題
        section_label = tk.Label(
            parent,
            text="捲動參數",
            font=("Segoe UI", 12, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_DARK
        )
        section_label.pack(anchor="w", pady=(12, 6))

        # 每個參數一張卡片
        params = [
            {
                "key": "step_size",
                "label": "步幅大小",
                "unit": "px",
                "desc": "每次滾輪滾動的像素數量",
                "min": 10, "max": 500, "default": 100,
                "resolution": 10,
                "type": int,
            },
            {
                "key": "animation_time",
                "label": "動畫時間",
                "unit": "ms",
                "desc": "捲動動畫的持續時間（越大越慢）",
                "min": 50, "max": 2000, "default": 400,
                "resolution": 50,
                "type": int,
            },
            {
                "key": "acceleration_delta",
                "label": "加速臨界值",
                "unit": "ms",
                "desc": "兩次捲動間隔小於此值時觸發加速",
                "min": 10, "max": 200, "default": 50,
                "resolution": 5,
                "type": int,
            },
            {
                "key": "acceleration_max",
                "label": "最大加速倍率",
                "unit": "x",
                "desc": "快速滾動時的最高速度倍率",
                "min": 1.0, "max": 10.0, "default": 3.0,
                "resolution": 0.5,
                "type": float,
            },
            {
                "key": "tail_head_ratio",
                "label": "減速/加速比",
                "unit": "x",
                "desc": "減速尾巴佔加速時間的倍數",
                "min": 1.0, "max": 10.0, "default": 4.0,
                "resolution": 0.5,
                "type": float,
            },
        ]

        for param in params:
            self._build_slider_param(parent, param)

    def _build_slider_param(self, parent: tk.Frame, param: dict) -> None:
        """建構帶滑桿的參數設定元件"""
        card = self._create_card(parent, pady=(0, 6))

        # 參數標題列
        title_row = tk.Frame(card, bg=Colors.BG_CARD)
        title_row.pack(fill="x", pady=(0, 4))

        tk.Label(
            title_row,
            text=param["label"],
            font=("Segoe UI", 10, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_CARD
        ).pack(side="left")

        # 數值顯示
        current_val = getattr(self.settings, param["key"])
        if param["type"] == int:
            val_text = f"{int(current_val)} {param['unit']}"
        else:
            val_text = f"{current_val:.1f} {param['unit']}"

        val_label = tk.Label(
            title_row,
            text=val_text,
            font=("Segoe UI Semibold", 10),
            fg=Colors.ACCENT,
            bg=Colors.BG_CARD
        )
        val_label.pack(side="right")

        # 描述
        tk.Label(
            card,
            text=param["desc"],
            font=("Segoe UI", 8),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD
        ).pack(anchor="w", pady=(0, 6))

        # 滑桿
        slider_frame = tk.Frame(card, bg=Colors.BG_CARD)
        slider_frame.pack(fill="x")

        slider_var = tk.DoubleVar(value=current_val)

        slider = ttk.Scale(
            slider_frame,
            from_=param["min"],
            to=param["max"],
            variable=slider_var,
            orient="horizontal",
            style="Custom.Horizontal.TScale",
        )
        slider.pack(fill="x", padx=4)

        # 最小/最大值標籤
        range_frame = tk.Frame(card, bg=Colors.BG_CARD)
        range_frame.pack(fill="x", padx=4)

        tk.Label(
            range_frame,
            text=str(param["min"]),
            font=("Segoe UI", 7),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD
        ).pack(side="left")

        tk.Label(
            range_frame,
            text=str(param["max"]),
            font=("Segoe UI", 7),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD
        ).pack(side="right")

        # 滑桿值變更事件
        def on_change(val, key=param["key"], resolution=param["resolution"],
                      vtype=param["type"], vlabel=val_label, unit=param["unit"]):
            raw = float(val)
            # 對齊到解析度
            snapped = round(raw / resolution) * resolution
            if vtype == int:
                snapped = int(snapped)
                vlabel.configure(text=f"{snapped} {unit}")
            else:
                vlabel.configure(text=f"{snapped:.1f} {unit}")
            setattr(self.settings, key, snapped)

        slider.configure(command=on_change)

        # 雙擊重設為預設值
        def on_double_click(event, key=param["key"], default=param["default"],
                          var=slider_var, resolution=param["resolution"],
                          vtype=param["type"], vlabel=val_label, unit=param["unit"]):
            var.set(default)
            setattr(self.settings, key, default)
            if vtype == int:
                vlabel.configure(text=f"{int(default)} {unit}")
            else:
                vlabel.configure(text=f"{default:.1f} {unit}")

        slider.bind("<Double-Button-1>", on_double_click)

        self._sliders[param["key"]] = slider_var

    def _build_feature_toggles(self, parent: tk.Frame) -> None:
        """建構功能開關區段"""
        section_label = tk.Label(
            parent,
            text="功能設定",
            font=("Segoe UI", 12, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_DARK
        )
        section_label.pack(anchor="w", pady=(12, 6))

        toggles = [
            ("enable_for_all_apps", "為所有應用程式啟用", "攔截所有應用程式的捲動事件"),
            ("animation_easing", "緩動動畫", "使用非線性緩動曲線讓動畫更自然"),
            ("shift_horizontal", "Shift + 滾輪水平捲動", "按住 Shift 鍵時將垂直捲動轉為水平"),
            ("horizontal_smoothness", "水平平滑捲動", "水平方向也套用平滑捲動效果"),
            ("reverse_direction", "反向滾輪方向", "反轉滑鼠滾輪的捲動方向"),
        ]

        for key, label, desc in toggles:
            self._build_toggle_row(parent, key, label, desc)

    def _build_toggle_row(self, parent: tk.Frame, key: str, label: str, desc: str) -> None:
        """建構單個開關列"""
        card = self._create_card(parent, pady=(0, 4))

        row = tk.Frame(card, bg=Colors.BG_CARD)
        row.pack(fill="x")

        # 文字區域
        text_frame = tk.Frame(row, bg=Colors.BG_CARD)
        text_frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_frame,
            text=label,
            font=("Segoe UI", 10),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_CARD
        ).pack(anchor="w")

        tk.Label(
            text_frame,
            text=desc,
            font=("Segoe UI", 8),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD
        ).pack(anchor="w")

        # 自訂切換開關
        toggle = ToggleSwitch(row, initial=getattr(self.settings, key))
        toggle.pack(side="right", padx=(8, 0))

        def on_toggle(new_val, k=key):
            setattr(self.settings, k, new_val)

        toggle.set_callback(on_toggle)
        self._toggles[key] = toggle

    def _build_blacklist_section(self, parent: tk.Frame) -> None:
        """建構排除清單（黑名單）區段"""
        section_label = tk.Label(
            parent,
            text="排除清單",
            font=("Segoe UI", 12, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_DARK
        )
        section_label.pack(anchor="w", pady=(12, 2))

        desc_label = tk.Label(
            parent,
            text="列表中的程式將不會套用平滑捲動，保留原始捲動行為",
            font=("Segoe UI", 8),
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_DARK
        )
        desc_label.pack(anchor="w", pady=(0, 6))

        card = self._create_card(parent, pady=(0, 8))

        # 清單顯示區
        list_frame = tk.Frame(card, bg=Colors.BG_INPUT, highlightbackground=Colors.BORDER,
                              highlightthickness=1)
        list_frame.pack(fill="x", pady=(0, 8))

        # 使用 Listbox 顯示已排除的程式
        self._blacklist_var = tk.StringVar(value=self.settings.blacklist)
        self._blacklist_box = tk.Listbox(
            list_frame,
            listvariable=self._blacklist_var,
            height=4,
            font=("Segoe UI", 9),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_INPUT,
            selectbackground=Colors.ACCENT,
            selectforeground="#ffffff",
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
        )
        self._blacklist_box.pack(fill="x", padx=2, pady=2)

        # 當清單為空時顯示提示訊息
        if not self.settings.blacklist:
            self._blacklist_box.insert(0, "（尚未排除任何程式）")
            self._blacklist_box.configure(fg=Colors.TEXT_MUTED)

        # 按鈕列
        btn_frame = tk.Frame(card, bg=Colors.BG_CARD)
        btn_frame.pack(fill="x")

        # 加入程式按鈕（瀏覽 .exe 檔）
        add_btn = tk.Label(
            btn_frame,
            text="➕ 瀏覽加入",
            font=("Segoe UI", 9),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_INPUT,
            cursor="hand2",
            padx=10, pady=4
        )
        add_btn.pack(side="left", padx=(0, 4))
        add_btn.bind("<Button-1>", self._blacklist_add_browse)
        add_btn.bind("<Enter>", lambda e: add_btn.configure(bg=Colors.BG_CARD_HOVER))
        add_btn.bind("<Leave>", lambda e: add_btn.configure(bg=Colors.BG_INPUT))

        # 偵測前景程式按鈕
        detect_btn = tk.Label(
            btn_frame,
            text="🔍 偵測程式",
            font=("Segoe UI", 9),
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_INPUT,
            cursor="hand2",
            padx=10, pady=4
        )
        detect_btn.pack(side="left", padx=(0, 4))
        detect_btn.bind("<Button-1>", self._blacklist_detect_foreground)
        detect_btn.bind("<Enter>", lambda e: detect_btn.configure(bg=Colors.BG_CARD_HOVER))
        detect_btn.bind("<Leave>", lambda e: detect_btn.configure(bg=Colors.BG_INPUT))

        # 移除選中程式按鈕
        remove_btn = tk.Label(
            btn_frame,
            text="❌ 移除選中",
            font=("Segoe UI", 9),
            fg=Colors.DANGER,
            bg=Colors.BG_INPUT,
            cursor="hand2",
            padx=10, pady=4
        )
        remove_btn.pack(side="right")
        remove_btn.bind("<Button-1>", self._blacklist_remove_selected)
        remove_btn.bind("<Enter>", lambda e: remove_btn.configure(bg=Colors.BG_CARD_HOVER))
        remove_btn.bind("<Leave>", lambda e: remove_btn.configure(bg=Colors.BG_INPUT))

    def _refresh_blacklist_display(self) -> None:
        """更新排除清單顯示"""
        self._blacklist_box.delete(0, tk.END)
        if self.settings.blacklist:
            self._blacklist_box.configure(fg=Colors.TEXT_PRIMARY)
            for name in self.settings.blacklist:
                self._blacklist_box.insert(tk.END, name)
        else:
            self._blacklist_box.configure(fg=Colors.TEXT_MUTED)
            self._blacklist_box.insert(0, "（尚未排除任何程式）")

    def _blacklist_add_browse(self, event=None) -> None:
        """透過檔案瀏覽器加入程式到排除清單"""
        filepath = filedialog.askopenfilename(
            title="選擇要排除的程式",
            filetypes=[("executable", "*.exe"), ("所有檔案", "*.*")],
            parent=self.root
        )
        if filepath:
            exe_name = os.path.basename(filepath).lower()
            if exe_name not in [n.lower() for n in self.settings.blacklist]:
                self.settings.blacklist.append(exe_name)
                self._refresh_blacklist_display()
                self._show_toast(f"✅ 已加入 {exe_name}")
            else:
                self._show_toast(f"⚠️ {exe_name} 已在清單中")

    def _blacklist_detect_foreground(self, event=None) -> None:
        """偵測下一個取得焦點的程式，3 秒後偵測"""
        self._show_toast("🔍 3 秒後偵測前景程式，請切換到目標程式...")
        self.root.after(3000, self._detect_foreground_exe)

    def _detect_foreground_exe(self) -> None:
        """偵測目前前景程式並加入排除清單"""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                self._show_toast("❌ 無法偵測前景程式")
                return

            pid = ctypes.wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == 0:
                self._show_toast("❌ 無法取得程序 PID")
                return

            # 取得執行檔名稱
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not handle:
                self._show_toast("❌ 無法開啟程序")
                return

            try:
                buf = ctypes.create_unicode_buffer(512)
                buf_size = ctypes.wintypes.DWORD(512)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_size)):
                    exe_name = buf.value.rsplit("\\", 1)[-1].lower()
                    if exe_name not in [n.lower() for n in self.settings.blacklist]:
                        self.settings.blacklist.append(exe_name)
                        self._refresh_blacklist_display()
                        self._show_toast(f"✅ 已偵測並加入 {exe_name}")
                    else:
                        self._show_toast(f"⚠️ {exe_name} 已在清單中")
                else:
                    self._show_toast("❌ 無法取得程式名稱")
            finally:
                kernel32.CloseHandle(handle)
        except Exception as e:
            self._show_toast(f"❌ 偵測失敗: {e}")

    def _blacklist_remove_selected(self, event=None) -> None:
        """從排除清單中移除選中的程式"""
        selection = self._blacklist_box.curselection()
        if not selection:
            self._show_toast("請先選取要移除的程式")
            return

        index = selection[0]
        if not self.settings.blacklist:
            return

        removed = self.settings.blacklist.pop(index)
        self._refresh_blacklist_display()
        self._show_toast(f"🗑️ 已移除 {removed}")

    def _build_footer(self, parent: tk.Frame) -> None:
        """建構底部按鈕列"""
        footer = tk.Frame(parent, bg=Colors.BG_DARK)
        footer.pack(fill="x", pady=(16, 4))

        # 重設按鈕
        reset_btn = tk.Label(
            footer,
            text="  重設預設值  ",
            font=("Segoe UI", 9),
            fg=Colors.TEXT_SECONDARY,
            bg=Colors.BG_CARD,
            cursor="hand2",
            padx=12, pady=6
        )
        reset_btn.pack(side="left")
        reset_btn.bind("<Button-1>", self._reset_defaults)
        reset_btn.bind("<Enter>", lambda e: reset_btn.configure(
            bg=Colors.BG_CARD_HOVER, fg=Colors.TEXT_PRIMARY))
        reset_btn.bind("<Leave>", lambda e: reset_btn.configure(
            bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY))

        # 儲存按鈕
        save_btn = tk.Label(
            footer,
            text="  💾 儲存設定  ",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=Colors.ACCENT,
            cursor="hand2",
            padx=16, pady=6
        )
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", self._save_settings)
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=Colors.ACCENT_HOVER))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=Colors.ACCENT))

    def _on_frame_configure(self, event=None) -> None:
        """當內容 Frame 尺寸改變時，更新 Canvas 的捲動區域"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None) -> None:
        """當 Canvas 尺寸改變時，讓內容 Frame 寬度跟著調整"""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _bind_mousewheel(self, event=None) -> None:
        """綁定滑鼠滾輪事件到 Canvas"""
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event=None) -> None:
        """解除綁定滑鼠滾輪事件"""
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        """處理滑鼠滾輪捲動設定視窗"""
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # 同步更新自訂捲軸
        self._scrollbar.update_thumb()

    def _create_card(self, parent: tk.Frame, pady=(0, 8)) -> tk.Frame:
        """建立一張卡片式容器"""
        card = tk.Frame(parent, bg=Colors.BG_CARD, padx=14, pady=10,
                       highlightbackground=Colors.BORDER, highlightthickness=1)
        card.pack(fill="x", pady=pady)
        return card

    def _toggle_engine(self, event=None) -> None:
        """切換引擎狀態"""
        if self.on_toggle_engine:
            new_state = self.on_toggle_engine()
            self.engine_running = new_state
            self._update_status_display()

    def _update_status_display(self) -> None:
        """更新狀態顯示"""
        if self.engine_running:
            self._status_dot.delete("all")
            self._status_dot.create_oval(1, 1, 11, 11, fill=Colors.SUCCESS, outline="")
            self._status_label.configure(text="平滑捲動已啟用")
            self._toggle_btn.configure(text="  停用  ")
        else:
            self._status_dot.delete("all")
            self._status_dot.create_oval(1, 1, 11, 11, fill=Colors.DANGER, outline="")
            self._status_label.configure(text="平滑捲動已停用")
            self._toggle_btn.configure(text="  啟用  ")

    def _save_settings(self, event=None) -> None:
        """儲存設定"""
        save_settings(self.settings)
        if self.on_save:
            self.on_save(self.settings)

        # 顯示儲存成功動畫
        self._show_toast("✅ 設定已儲存")

    def _reset_defaults(self, event=None) -> None:
        """重設為預設值"""
        self.settings = reset_settings()

        # 更新所有滑桿
        defaults = ScrollSettings()
        for key, var in self._sliders.items():
            var.set(getattr(defaults, key))

        # 更新所有開關
        for key, toggle in self._toggles.items():
            toggle.set_state(getattr(defaults, key))

        # 更新排除清單
        self._refresh_blacklist_display()

        self._show_toast("🔄 已重設為預設值")

    def _show_toast(self, message: str) -> None:
        """顯示暫時性的提示訊息"""
        toast = tk.Label(
            self.root,
            text=message,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=Colors.ACCENT,
            padx=20, pady=8
        )
        toast.place(relx=0.5, rely=0.95, anchor="center")

        def fade_out():
            try:
                toast.destroy()
            except Exception:
                pass

        self.root.after(1500, fade_out)

    def _on_close(self) -> None:
        """關閉設定視窗"""
        if self.root:
            try:
                # 解除全域滾輪綁定
                try:
                    self._canvas.unbind_all("<MouseWheel>")
                except Exception:
                    pass
                # 清除 tkinter 變數參考
                self._sliders.clear()
                self._toggles.clear()
                self.root.destroy()
            except Exception:
                pass
            finally:
                self.root = None

    def update_engine_status(self, running: bool) -> None:
        """外部更新引擎狀態"""
        self.engine_running = running
        if self.root and self.root.winfo_exists():
            self._update_status_display()


class ToggleSwitch(tk.Canvas):
    """自訂的切換開關元件"""

    WIDTH = 44
    HEIGHT = 24
    KNOB_RADIUS = 9
    PADDING = 3

    def __init__(self, parent, initial: bool = False, **kwargs):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                        bg=Colors.BG_CARD, highlightthickness=0,
                        cursor="hand2", **kwargs)
        self._state = initial
        self._callback = None
        self._animating = False

        self.bind("<Button-1>", self._on_click)
        self._draw()

    def set_callback(self, callback: Callable) -> None:
        self._callback = callback

    def set_state(self, state: bool) -> None:
        self._state = state
        self._draw()

    def _on_click(self, event=None) -> None:
        self._state = not self._state
        self._draw()
        if self._callback:
            self._callback(self._state)

    def _draw(self) -> None:
        self.delete("all")

        bg_color = Colors.TOGGLE_ON if self._state else Colors.TOGGLE_OFF
        knob_x = self.WIDTH - self.KNOB_RADIUS - self.PADDING if self._state \
            else self.KNOB_RADIUS + self.PADDING

        # 背景圓角矩形
        r = self.HEIGHT // 2
        self.create_arc(0, 0, self.HEIGHT, self.HEIGHT, start=90, extent=180,
                       fill=bg_color, outline="")
        self.create_arc(self.WIDTH - self.HEIGHT, 0, self.WIDTH, self.HEIGHT,
                       start=-90, extent=180, fill=bg_color, outline="")
        self.create_rectangle(r, 0, self.WIDTH - r, self.HEIGHT,
                            fill=bg_color, outline="")

        # 旋鈕
        self.create_oval(
            knob_x - self.KNOB_RADIUS,
            self.HEIGHT // 2 - self.KNOB_RADIUS,
            knob_x + self.KNOB_RADIUS,
            self.HEIGHT // 2 + self.KNOB_RADIUS,
            fill=Colors.TOGGLE_KNOB, outline=""
        )


class ModernScrollbar(tk.Canvas):
    """
    現代化自訂捲軸元件
    使用 Canvas 繪製圓角膠囊形滑塊，風格類似 macOS / Chrome 的 overlay scrollbar。
    """

    SCROLLBAR_WIDTH = 8       # 捲軸寬度
    SCROLLBAR_PAD = 2         # 內邊距
    MIN_THUMB_HEIGHT = 30     # 滑塊最小高度
    CORNER_RADIUS = 4         # 圓角半徑

    def __init__(self, parent, canvas: tk.Canvas, **kwargs):
        super().__init__(
            parent,
            width=self.SCROLLBAR_WIDTH + self.SCROLLBAR_PAD * 2,
            bg=Colors.BG_DARK,
            highlightthickness=0,
            borderwidth=0,
            **kwargs
        )
        self._canvas = canvas
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_pos = 0.0
        self._hovered = False

        # 設定 Canvas 的 yscrollcommand 來同步
        self._canvas.configure(yscrollcommand=self._on_scroll)

        # 互動事件
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", lambda e: self.update_thumb())

    def _on_scroll(self, first: str, last: str) -> None:
        """當主 Canvas 捲動時更新滑塊位置"""
        self._first = float(first)
        self._last = float(last)
        self.update_thumb()

    def update_thumb(self) -> None:
        """重繪捲軸滑塊"""
        self.delete("all")

        try:
            first, last = self._canvas.yview()
        except Exception:
            return

        # 如果內容沒有超出可見區域，不顯示捲軸
        if first <= 0.0 and last >= 1.0:
            return

        canvas_h = self.winfo_height()
        if canvas_h <= 0:
            return

        # 計算滑塊位置和高度
        thumb_height = max(self.MIN_THUMB_HEIGHT, int((last - first) * canvas_h))
        thumb_y = int(first * canvas_h)
        thumb_y_end = thumb_y + thumb_height

        # 確保不超出範圍
        if thumb_y_end > canvas_h:
            thumb_y_end = canvas_h
            thumb_y = thumb_y_end - thumb_height

        # 根據狀態切換顏色
        if self._dragging:
            thumb_color = Colors.ACCENT            # 拖曳時顯示主題色
        elif self._hovered:
            thumb_color = Colors.BG_CARD_HOVER     # 懸停時稍亮
        else:
            thumb_color = Colors.BG_CARD           # 預設狀態

        # 繪製圓角膠囊形滑塊
        x1 = self.SCROLLBAR_PAD
        x2 = self.SCROLLBAR_WIDTH + self.SCROLLBAR_PAD
        y1 = thumb_y + self.SCROLLBAR_PAD
        y2 = thumb_y_end - self.SCROLLBAR_PAD
        r = self.CORNER_RADIUS

        # 使用 create_arc + create_rectangle 繪製圓角矩形
        self._draw_rounded_rect(x1, y1, x2, y2, r, thumb_color)

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, color) -> None:
        """繪製圓角矩形"""
        # 若滑塊太小，無法繪製圓角時直接繪製矩形
        if (y2 - y1) < r * 2 or (x2 - x1) < r * 2:
            self.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            return

        # 上左圓角
        self.create_arc(x1, y1, x1 + r * 2, y1 + r * 2,
                       start=90, extent=90, fill=color, outline="")
        # 上右圓角
        self.create_arc(x2 - r * 2, y1, x2, y1 + r * 2,
                       start=0, extent=90, fill=color, outline="")
        # 下左圓角
        self.create_arc(x1, y2 - r * 2, x1 + r * 2, y2,
                       start=180, extent=90, fill=color, outline="")
        # 下右圓角
        self.create_arc(x2 - r * 2, y2 - r * 2, x2, y2,
                       start=270, extent=90, fill=color, outline="")
        # 中間填充
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=color, outline="")
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=color, outline="")

    def _on_click(self, event) -> None:
        """點擊捲軸區域"""
        try:
            first, last = self._canvas.yview()
        except Exception:
            return

        canvas_h = self.winfo_height()
        if canvas_h <= 0:
            return

        thumb_height = max(self.MIN_THUMB_HEIGHT, int((last - first) * canvas_h))
        thumb_y = int(first * canvas_h)

        # 判斷是否點在滑塊上
        if thumb_y <= event.y <= thumb_y + thumb_height:
            # 開始拖曳
            self._dragging = True
            self._drag_start_y = event.y
            self._drag_start_pos = first
        else:
            # 點擊滑塊以外的區域，跳躍到該位置
            total_ratio = event.y / canvas_h
            self._canvas.yview_moveto(total_ratio)

        self.update_thumb()

    def _on_drag(self, event) -> None:
        """拖曳滑塊"""
        if not self._dragging:
            return

        canvas_h = self.winfo_height()
        if canvas_h <= 0:
            return

        # 計算拖曳偏移量對應的捲動比例
        delta_y = event.y - self._drag_start_y
        delta_ratio = delta_y / canvas_h
        new_pos = self._drag_start_pos + delta_ratio
        new_pos = max(0.0, min(new_pos, 1.0))
        self._canvas.yview_moveto(new_pos)
        self.update_thumb()

    def _on_release(self, event) -> None:
        """釋放滑鼠"""
        self._dragging = False
        self.update_thumb()

    def _on_enter(self, event) -> None:
        """滑鼠進入捲軸區域"""
        self._hovered = True
        self.update_thumb()

    def _on_leave(self, event) -> None:
        """滑鼠離開捲軸區域"""
        if not self._dragging:
            self._hovered = False
            self.update_thumb()
