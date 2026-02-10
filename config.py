"""
OpenSmoothScroll - 設定管理模組
負責讀取、儲存與管理所有程式設定。
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List


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
    enable_for_all_apps: bool = True      # 為所有應用程式啟用
    animation_easing: bool = True          # 緩動動畫
    shift_horizontal: bool = True          # Shift 鍵水平捲動
    horizontal_smoothness: bool = True     # 水平方向也套用平滑
    reverse_direction: bool = False        # 反向滾輪方向

    # 排除清單（黑名單）
    blacklist: List[str] = field(default_factory=list)  # 排除的程式執行檔名稱

    # 程式狀態
    enabled: bool = True                   # 總開關


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
