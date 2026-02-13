# 🖱️ OpenSmoothScroll

**一套開源、輕量化的 Windows 系統級平滑捲動工具。**

讓你的滑鼠滾輪滑如絲綢 ✨
*(Inspired by SmoothScroll, purely Python implementation)*

## 📖 專案簡介

OpenSmoothScroll 是一個旨在改善 Windows 預設滾動體驗的開源專案。透過底層鉤子技術與物理慣性演算法，讓所有應用程式（Chrome, Discord, VS Code 等）都能擁有如 Mac 觸控板般的流暢捲動感。

> ⚠️ **注意**：本專案與付費軟體 "SmoothScroll" 無任何關聯，所有程式碼皆為獨立撰寫的開源實作。

## 功能特色

- 🎯 **全域平滑捲動** — 系統級攔截，所有應用程式通用
- ⚡ **智慧加速** — 快速滾動時自動加速，精確操控
- 🎨 **自訂緩動曲線** — 可調整加速/減速比例，打造您專屬的手感
- ↔️ **水平捲動支援** — Shift + 滾輪水平捲動
- 🔄 **反向滾輪** — 一鍵切換滾輪方向
- 🚫 **排除清單（黑名單）** — 指定特定程式不套用平滑捲動
- 🔍 **Ctrl+滾輪 自動繞過** — 縮放操作時自動停用平滑捲動
- ⚡ **反向捲動零延遲** — 智慧偵測方向反轉，立即切換無黏滯感
- ⌨️ **全域快捷鍵** — 預設 `Ctrl+Alt+Shift+S`，隨時切換啟用/停用
- 🖥️ **系統匣常駐** — 低調運行，雙擊圖示開啟設定，右鍵快速操作
- 🎛️ **深色主題設定面板** — 現代化 UI，深色標題列、自訂捲軸、可垂直捲動

## 可調參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| Step Size | 100 px | 每次滾輪滾動的像素數 |
| Animation Time | 400 ms | 動畫時間（越大越慢） |
| Acceleration Delta | 50 ms | 觸發加速的最小捲動間隔 |
| Acceleration Max | 3x | 最大加速倍率 |
| Tail/Head Ratio | 4x | 減速尾巴長度（越大滑行越遠） |

## 功能開關

| 開關 | 預設 | 說明 |
|------|------|------|
| 緩動動畫 | ✅ 開啟 | 使用自訂緩動曲線，關閉則為線性移動 |
| Shift 水平捲動 | ✅ 開啟 | Shift + 滾輪轉換為水平捲動 |
| 水平方向平滑 | ✅ 開啟 | 水平捲動也套用平滑動畫 |
| 反向滾輪方向 | ❌ 關閉 | 反轉滾輪捲動方向 |

## ⌨️ 快捷鍵

| 快捷鍵 | 功能 | 說明 |
|--------|------|------|
| `Ctrl + Alt + Shift + S` | 切換啟用/停用 | 預設快捷鍵，可在設定檔中自訂 |

> 💡 快捷鍵可在Win+R貼上路徑 `%APPDATA%\OpenSmoothScroll\settings.json` ，找到 `hotkey` 欄位修改，
> 支援的修飾鍵：`ctrl`、`alt`、`shift`、`win`，支援的按鍵：`a`-`z`、`0`-`9`、`f1`-`f12`、方向鍵等。

## 快速開始

### 方式一：使用預編譯 EXE（推薦）

1. 從 [Releases](https://github.com/user/opensmoothscroll/releases) 下載 `OpenSmoothScroll.exe`
2. 雙擊執行即可，程式會常駐於系統匣
3. 雙擊系統匣圖示開啟設定面板

### 方式二：從原始碼執行

#### 安裝相依套件

```bash
pip install -r requirements.txt
```

#### 啟動程式

```bash
python main.py
```

#### 命令列選項

```bash
python main.py          # 啟動系統匣常駐程式
python main.py --ui     # 直接開啟設定視窗（調試用）
python main.py --help   # 顯示說明
```

### 打包為 EXE

```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
# 產出位於 dist/OpenSmoothScroll.exe（約 17MB）
```

## 排除清單（黑名單）

在設定面板的「排除清單」區段，可以指定不套用平滑捲動的程式：

- **瀏覽加入** — 手動選取 `.exe` 檔案
- **偵測程式** — 自動偵測目前前景應用程式並加入
- **移除選中** — 從清單中移除

> 💡 Ctrl+滾輪（縮放操作）會自動繞過平滑捲動，無需手動排除。

## 系統需求

- Windows 10 (1809+) / Windows 11
- Python 3.10+（從原始碼執行時）

## 相依套件

| 套件 | 用途 |
|------|------|
| [pystray](https://pypi.org/project/pystray/) | 系統匣圖示與選單 |
| [Pillow](https://pypi.org/project/Pillow/) | 繪製系統匣圖示 |

> 所有 Win32 API 呼叫均使用 Python 內建的 `ctypes`，不需要 `pywin32`。

## 技術架構

```
opensmoothscroll/
├── main.py                  # 主程式入口、命令列處理
├── smooth_scroll_engine.py  # 核心平滑捲動引擎（Win32 Hook）
├── settings_ui.py           # 設定介面（tkinter 深色主題）
├── tray_app.py              # 系統匣應用（線程管理）
├── config.py                # 設定管理（JSON 讀寫）
├── utils.py                 # 工具函數（開機啟動、單實例鎖定）
├── build.spec               # PyInstaller 打包配置
├── requirements.txt         # 相依套件
└── README.md                # 本文件
```

### 線程架構

```
主線程 (Main Thread)
├── tk.Tk() 隱藏根視窗 + mainloop()
└── tk.Toplevel() 設定視窗

背景線程 (Daemon Thread)
├── pystray 系統匣圖示
├── SmoothScrollEngine 滑鼠鉤子 + 訊息迴圈
└── Global Hotkey Listener 全域快捷鍵監聽

動畫線程 (Per-scroll, Daemon)
├── 垂直捲動動畫線程
└── 水平捲動動畫線程
```

### 核心技術

- **Win32 Low-Level Mouse Hook** (`SetWindowsHookEx` + `WH_MOUSE_LL`)
  - 全域攔截滑鼠滾輪事件
  - 使用 `dwExtraInfo` 標記避免無限迴圈
  - 支援 `WM_MOUSEWHEEL`（垂直）與 `WM_MOUSEHWHEEL`（水平）
- **動畫引擎**
  - 240fps 更新頻率
  - 自訂緩動函數 `custom_ease()`（Physics-based Normalized Exponential Ease-Out）
  - 累積小數（Sub-pixel rendering）防止捲動量遺失
  - 方向反轉偵測，立即丟棄舊動量避免黏滯感
- **加速度系統**
  - 基於連續捲動間隔計算加速倍率
  - 300ms 線性衰減回到基準速度
  - 方向反轉時自動重置加速度
- **黑名單機制**
  - 使用 `OpenProcess` + `QueryFullProcessImageNameW` 取得前景程式名稱
  - PID → 程式名稱快取，避免效能損耗
  - 不分大小寫比對
- **Ctrl+滾輪繞過**
  - `GetAsyncKeyState(VK_CONTROL)` 偵測 Ctrl 鍵
  - 按住 Ctrl 時放行原始滾輪事件，不攔截
- **深色主題 UI**
  - Windows DWM API（`DWMWA_CAPTION_COLOR`）自訂標題列顏色
  - 自訂 Canvas 捲軸元件（`ModernScrollbar`）
  - 可捲動的設定面板（Canvas + Toplevel）

## 設定檔位置

```
%APPDATA%\OpenSmoothScroll\settings.json
```

## ⚠️ 免責聲明

本軟體以「現狀」（AS IS）提供，不附帶任何形式的明示或暗示擔保，包括但不限於適銷性、特定用途適用性及非侵權性的擔保。

- 本程式使用 **Windows 低階滑鼠鉤子**（`SetWindowsHookEx` + `WH_MOUSE_LL`）攔截系統層級的滑鼠事件。此為 Windows 作業系統提供的標準 API，但部分防毒軟體可能會對此類行為發出警告，此屬正常現象。
- 使用者應自行評估在其環境中使用本軟體的風險。對於因使用或無法使用本軟體而產生的任何損害，作者概不負責。

## 📋 商標聲明

- **OpenSmoothScroll** 是一個**獨立的開源專案**，與商業軟體「SmoothScroll」或其開發商 **無任何關聯、從屬或背書關係**。
- 「SmoothScroll」之名稱及商標歸其各自所有者所有。本專案提及該名稱僅為功能描述之目的，並非宣稱任何商業關聯。
- 本專案的所有程式碼均為獨立編寫，未使用、參考或逆向工程任何商業軟體的原始碼。

## 🔒 安全性與隱私

- 本程式**不會收集、傳輸或儲存**任何使用者資料。
- 所有設定均儲存在本地 `%APPDATA%\OpenSmoothScroll\settings.json`。
- 本程式**不會連接網路**，無任何遠端通訊功能。
- 程式碼完全開源，歡迎審查。

## 📜 第三方授權

本專案使用以下第三方開源套件：

| 套件 | 授權 | 用途 |
|------|------|------|
| [pystray](https://github.com/moses-palmer/pystray) | LGPL-3.0 | 系統匣圖示與選單 |
| [Pillow](https://github.com/python-pillow/Pillow) | HPND (Historical Permission Notice and Disclaimer) | 繪製系統匣圖示 |

> ⚠️ **注意**：`pystray` 採用 **LGPL-3.0** 授權。本專案以動態載入方式使用 `pystray`，符合 LGPL 的使用條件。若您基於本專案進行再發佈，請確保遵守 LGPL-3.0 的相關規範。

## 授權

本專案採用 [MIT License](LICENSE) 授權。

Copyright © 2026 OpenSmoothScroll Contributors



