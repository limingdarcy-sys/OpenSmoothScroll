"""
OpenSmoothScroll - 設定管理模組
負責讀取、儲存與管理所有程式設定。
支援全域設定和個別程式的專屬參數覆蓋。
"""

import json
import os
import configparser
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict


# 設定檔路徑（存放在使用者的 AppData 目錄）
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", "."), "OpenSmoothScroll")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


@dataclass
class ScrollSettings:
    """捲動設定資料類別"""

    # 基本參數
    step_size: int = 100           # 每次滾輪滾動的像素數
    animation_time: int = 400      # 動畫持續時間（毫秒）
    acceleration_delta: int = 50   # 觸發加速的最小間隔（毫秒）
    acceleration_max: float = 3.0  # 最大加速倍率
    tail_head_ratio: float = 4.0   # 減速與加速的時間比例

    # 功能開關
    animation_easing: bool = True          # 緩動動畫
    shift_horizontal: bool = True          # Shift 鍵水平捲動
    horizontal_smoothness: bool = True     # 水平方向也套用平滑

    # 排除清單（黑名單）
    blacklist: List[str] = field(default_factory=list)  # 排除的程式執行檔名稱

    # 個別程式設定（覆蓋全域參數）
    # 格式：{"chrome.exe": {"step_size": 120, "animation_time": 300, ...}, ...}
    per_app_settings: Dict[str, dict] = field(default_factory=dict)

    # 快捷鍵
    hotkey: str = "ctrl+alt+shift+s"  # 切換啟用/停用的全域快捷鍵

    # 程式狀態
    enabled: bool = True                   # 總開關

    def get_app_settings(self, exe_name: str) -> dict:
        """
        取得特定程式的有效設定參數。
        如果該程式有個別設定，則以個別設定覆蓋全域設定。
        回傳包含所有捲動參數的字典。
        """
        # 全域參數作為基礎
        base = {
            'step_size': self.step_size,
            'animation_time': self.animation_time,
            'acceleration_delta': self.acceleration_delta,
            'acceleration_max': self.acceleration_max,
            'tail_head_ratio': self.tail_head_ratio,
        }
        # 如果有個別設定，覆蓋對應的鍵
        if exe_name and exe_name.lower() in self.per_app_settings:
            app_overrides = self.per_app_settings[exe_name.lower()]
            base.update(app_overrides)
        return base


def load_settings() -> ScrollSettings:
    """從設定檔載入設定，若不存在則回傳預設值"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 只取 ScrollSettings 中有的欄位，忽略多餘的
                defaults = ScrollSettings()
                valid_keys = asdict(defaults).keys()
                filtered = {k: v for k, v in data.items() if k in valid_keys}
                return ScrollSettings(**filtered)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"[警告] 設定檔讀取失敗，使用預設值: {e}")
    return ScrollSettings()


def save_settings(settings: ScrollSettings) -> None:
    """將設定儲存至設定檔"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, indent=4, ensure_ascii=False)


def reset_settings() -> ScrollSettings:
    """重設為預設值並儲存"""
    settings = ScrollSettings()
    save_settings(settings)
    return settings


# ─── config.ini 匯出/匯入 ──────────────────────────────────────────────

# 個別程式設定中可覆蓋的參數鍵和型態對照
_PER_APP_PARAM_TYPES = {
    'step_size': int,
    'animation_time': int,
    'acceleration_delta': int,
    'acceleration_max': float,
    'tail_head_ratio': float,
}


def export_config_ini(settings: ScrollSettings, filepath: str) -> None:
    """
    將設定匯出為 config.ini 格式。
    
    格式範例：
    [Global]
    step_size = 100
    animation_time = 400
    ...
    blacklist = chrome.exe, firefox.exe
    
    [PerApp:notepad.exe]
    step_size = 120
    animation_time = 300
    """
    config = configparser.ConfigParser()

    # [Global] 區段
    config['Global'] = {
        'step_size': str(settings.step_size),
        'animation_time': str(settings.animation_time),
        'acceleration_delta': str(settings.acceleration_delta),
        'acceleration_max': str(settings.acceleration_max),
        'tail_head_ratio': str(settings.tail_head_ratio),
        'animation_easing': str(settings.animation_easing),
        'shift_horizontal': str(settings.shift_horizontal),
        'horizontal_smoothness': str(settings.horizontal_smoothness),
        'hotkey': settings.hotkey,
        'enabled': str(settings.enabled),
        'blacklist': ', '.join(settings.blacklist) if settings.blacklist else '',
    }

    # [PerApp:xxx.exe] 區段
    for exe_name, params in settings.per_app_settings.items():
        section_name = f"PerApp:{exe_name}"
        config[section_name] = {}
        for key, value in params.items():
            config[section_name][key] = str(value)

    with open(filepath, 'w', encoding='utf-8') as f:
        # 寫入註解標頭
        f.write("; OpenSmoothScroll 設定檔\n")
        f.write("; 可手動編輯此檔案，或透過程式匯入\n")
        f.write("; [PerApp:程式名稱.exe] 區段可針對特定程式覆蓋全域參數\n\n")
        config.write(f)


def import_config_ini(filepath: str) -> ScrollSettings:
    """
    從 config.ini 匯入設定。
    回傳新的 ScrollSettings 物件。
    """
    config = configparser.ConfigParser()
    config.read(filepath, encoding='utf-8')

    settings = ScrollSettings()

    # 讀取 [Global] 區段
    if config.has_section('Global'):
        g = config['Global']
        settings.step_size = g.getint('step_size', settings.step_size)
        settings.animation_time = g.getint('animation_time', settings.animation_time)
        settings.acceleration_delta = g.getint('acceleration_delta', settings.acceleration_delta)
        settings.acceleration_max = g.getfloat('acceleration_max', settings.acceleration_max)
        settings.tail_head_ratio = g.getfloat('tail_head_ratio', settings.tail_head_ratio)
        settings.animation_easing = g.getboolean('animation_easing', settings.animation_easing)
        settings.shift_horizontal = g.getboolean('shift_horizontal', settings.shift_horizontal)
        settings.horizontal_smoothness = g.getboolean('horizontal_smoothness', settings.horizontal_smoothness)
        settings.hotkey = g.get('hotkey', settings.hotkey)
        settings.enabled = g.getboolean('enabled', settings.enabled)

        # 讀取排除清單
        blacklist_str = g.get('blacklist', '')
        if blacklist_str.strip():
            settings.blacklist = [name.strip() for name in blacklist_str.split(',') if name.strip()]

    # 讀取 [PerApp:xxx.exe] 區段
    per_app = {}
    for section in config.sections():
        if section.startswith('PerApp:'):
            exe_name = section.split(':', 1)[1].strip().lower()
            params = {}
            for key in config[section]:
                if key in _PER_APP_PARAM_TYPES:
                    vtype = _PER_APP_PARAM_TYPES[key]
                    try:
                        params[key] = vtype(config[section][key])
                    except (ValueError, TypeError):
                        pass  # 跳過無法解析的值
            if params:
                per_app[exe_name] = params
    settings.per_app_settings = per_app

    return settings
