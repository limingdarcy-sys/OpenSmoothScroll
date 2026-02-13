"""
OpenSmoothScroll - 核心平滑捲動引擎
使用 Win32 低階滑鼠鉤子攔截滾輪事件，
並透過動畫執行緒實現平滑捲動效果。
"""

import ctypes
import ctypes.wintypes
import threading
import time
import math
from collections import deque
from typing import Optional, Callable

from config import ScrollSettings


# ─── Win32 常數 ──────────────────────────────────────────────────────
WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E

# SendInput 相關常數
INPUT_MOUSE = 0
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

# VK_SHIFT / VK_CONTROL 鍵
VK_SHIFT = 0x10
VK_CONTROL = 0x11

# ─── Win32 結構體 ────────────────────────────────────────────────────
# ULONG_PTR 型態（用於 dwExtraInfo）
if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", ctypes.wintypes.POINT),
        ("mouseData", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# ─── Win32 API 函數 ──────────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 定義 Windows 特殊型別（64位相容）
LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
WPARAM = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint
LPARAM = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
HHOOK = ctypes.c_void_p
HINSTANCE = ctypes.c_void_p

# 設定回呼函數型別（使用正確的 64 位型別）
HOOKPROC = ctypes.CFUNCTYPE(
    LRESULT,      # 回傳值
    ctypes.c_int, # nCode
    WPARAM,       # wParam
    LPARAM        # lParam
)

# 設定各 API 函數的參數與回傳型別
SetWindowsHookExW = user32.SetWindowsHookExW
SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, HINSTANCE, ctypes.wintypes.DWORD]
SetWindowsHookExW.restype = HHOOK

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL

CallNextHookEx = user32.CallNextHookEx
CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, WPARAM, LPARAM]
CallNextHookEx.restype = LRESULT

GetMessageW = user32.GetMessageW
GetMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG), ctypes.wintypes.HWND,
                        ctypes.c_uint, ctypes.c_uint]
GetMessageW.restype = ctypes.wintypes.BOOL

SendInput = user32.SendInput
SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = ctypes.c_uint

GetAsyncKeyState = user32.GetAsyncKeyState
GetAsyncKeyState.argtypes = [ctypes.c_int]
GetAsyncKeyState.restype = ctypes.c_short

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = ctypes.wintypes.HWND

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD

# 取得程序執行檔名稱的 API
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
OpenProcess.restype = ctypes.wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
CloseHandle.restype = ctypes.wintypes.BOOL

QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
QueryFullProcessImageNameW.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPWSTR,
    ctypes.POINTER(ctypes.wintypes.DWORD),
]
QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL


# ─── 緩動函數 ─────────────────────────────────────────────────────────
def ease_out_cubic(t: float) -> float:
    """三次方緩出函數 - 標準 UI 動畫曲線"""
    t -= 1
    return t * t * t + 1


def ease_out_quart(t: float) -> float:
    """四次方緩出函數 - 更強的減速效果"""
    t -= 1
    return -(t * t * t * t - 1)


def ease_out_quint(t: float) -> float:
    """
    [新增] 五次方緩出函數 (Quintic)
    這是被廣泛推薦的預設值，因為它具有極快的起步速度與極長的緩衝尾巴。
    """
    t -= 1
    return t * t * t * t * t + 1


def ease_in_out_cubic(t: float) -> float:
    """三次方緩入緩出函數 - 適用於非互動式動畫"""
    t *= 2
    if t < 1:
        return 0.5 * t * t * t
    t -= 2
    return 0.5 * (t * t * t + 2)


def ease_out_expo(t: float) -> float:
    """指數緩出函數 - 物理模擬摩擦力 (優化版)"""
    if t == 1.0:
        return 1.0
    # 使用 math.exp 替代 pow 提升效能
    return 1.0 - math.exp(-8.0 * t)


def custom_ease(t: float, tail_ratio: float) -> float:
    """
    自訂緩動函數 (Physics-based Normalized Exponential Ease-Out)
    
    設計邏輯：
    這個函數使用指數運算來模擬物理摩擦力。
    當 tail_ratio 設定在 4.0 ~ 5.0 之間時，其表現曲線與 ease_out_quint (五次方) 極為相似，
    但優點是它支援動態調整參數，可變長也可變短。
    
    參數：
    t: 時間進度 0.0 ~ 1.0
    tail_ratio: 控制摩擦係數。
                數值越大 -> 摩擦力越小 -> 尾巴越長 (滑行感強)
                數值越小 -> 摩擦力越大 -> 尾巴越短 (急停)
    """
    # 將 tail_ratio 對應為物理摩擦係數 k
    # 經驗公式：tail_ratio 4.0 約等於標準 Quintic 手感 (k=6.0)
    k = 24.0 / (tail_ratio + 1.0)
    
    # 避免除以零
    if k < 0.001: k = 0.001

    # 歸一化公式： (1 - e^(-kt)) / (1 - e^(-k))
    # 確保 t=0 時回傳 0，t=1 時回傳 1
    numerator = 1.0 - math.exp(-k * t)
    denominator = 1.0 - math.exp(-k)
    
    return numerator / denominator


# ─── 平滑捲動引擎 ─────────────────────────────────────────────────────
class SmoothScrollEngine:
    """平滑捲動引擎主類別"""

    # 用於識別由本程式發送的捲動事件的特殊標記
    INJECTED_FLAG = 0xBEEF

    def __init__(self, settings: ScrollSettings):
        self.settings = settings
        self._hook_handle = None
        self._hook_thread: Optional[threading.Thread] = None
        self._running = False

        # 動畫狀態
        self._animation_lock = threading.Lock()
        self._target_scroll_v = 0.0        # 垂直方向累積目標捲動量
        self._target_scroll_h = 0.0        # 水平方向累積目標捲動量
        self._current_scroll_v = 0.0       # 垂直方向目前已捲動量
        self._current_scroll_h = 0.0       # 水平方向目前已捲動量
        self._animation_thread_v: Optional[threading.Thread] = None
        self._animation_thread_h: Optional[threading.Thread] = None
        self._animating_v = False
        self._animating_h = False

        # 加速度追蹤
        self._last_scroll_time = 0.0
        self._scroll_velocity = 1.0        # 目前速度倍率

        # 保持回呼函數的參考（避免被垃圾回收）
        self._hook_proc = HOOKPROC(self._low_level_mouse_proc)

        # 狀態變更回呼
        self._on_status_change: Optional[Callable] = None

        # 黑名單快取（PID → 執行檔名稱），避免每次捲動都查詢程序資訊
        self._process_name_cache: dict[int, str] = {}
        self._cache_max_size = 128  # 快取最大容量

    def set_status_callback(self, callback: Callable) -> None:
        """設定狀態變更回呼函數"""
        self._on_status_change = callback

    def update_settings(self, settings: ScrollSettings) -> None:
        """更新設定"""
        self.settings = settings

    def start(self) -> None:
        """啟動平滑捲動引擎"""
        if self._running:
            return

        self._running = True
        self._hook_thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._hook_thread.start()

        if self._on_status_change:
            self._on_status_change(True)

    def stop(self) -> None:
        """停止平滑捲動引擎"""
        if not self._running:
            return

        self._running = False

        # 取消鉤子需要在鉤子執行緒中執行，
        # 透過送一個假訊息來讓 GetMessage() 返回
        if self._hook_handle:
            user32.PostThreadMessageW(
                self._hook_thread_id, 0x0012, 0, 0  # WM_QUIT
            )

        if self._hook_thread:
            self._hook_thread.join(timeout=5)

        if self._on_status_change:
            self._on_status_change(False)

    def toggle(self) -> bool:
        """切換啟用/停用，回傳新狀態"""
        if self._running:
            self.stop()
            return False
        else:
            self.start()
            return True

    @property
    def is_running(self) -> bool:
        return self._running

    def _hook_loop(self) -> None:
        """鉤子訊息迴圈（在獨立執行緒中執行）"""
        self._hook_thread_id = kernel32.GetCurrentThreadId()

        # 安裝低階滑鼠鉤子
        self._hook_handle = SetWindowsHookExW(
            WH_MOUSE_LL,
            self._hook_proc,
            None,
            0
        )

        if not self._hook_handle:
            error = ctypes.get_last_error()
            print(f"[錯誤] 安裝滑鼠鉤子失敗，錯誤碼: {error}")
            self._running = False
            return

        print("[資訊] 平滑捲動引擎已啟動")

        # 訊息迴圈（必須，否則鉤子不會運作）
        msg = ctypes.wintypes.MSG()
        while self._running:
            result = GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result <= 0:
                break

        # 清除鉤子
        if self._hook_handle:
            UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

        print("[資訊] 平滑捲動引擎已停止")

    def _low_level_mouse_proc(self, nCode, wParam, lParam) -> int:
        """低階滑鼠鉤子回呼函數"""
        if nCode < 0 or not self.settings.enabled:
            return CallNextHookEx(None, nCode, wParam, lParam)

        # 只處理滑鼠滾輪事件
        if wParam not in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
            return CallNextHookEx(None, nCode, wParam, lParam)

        # 取得鉤子資料（lParam 是指向 MSLLHOOKSTRUCT 的指標值）
        hook_struct = ctypes.cast(ctypes.c_void_p(lParam), ctypes.POINTER(MSLLHOOKSTRUCT)).contents

        # 忽略由本程式注入的事件（避免無限迴圈）
        extra_info = hook_struct.dwExtraInfo
        if extra_info == self.INJECTED_FLAG:
            return CallNextHookEx(None, nCode, wParam, lParam)

        # 檢查前景程式是否在黑名單中
        if self.settings.blacklist and self._is_foreground_blacklisted():
            return CallNextHookEx(None, nCode, wParam, lParam)

        # Ctrl + 滾輪 = 縮放操作，不放截，直接放行原始事件
        ctrl_pressed = (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        if ctrl_pressed:
            return CallNextHookEx(None, nCode, wParam, lParam)

        # 取得捲動方向和量
        # mouseData 的高位元組包含滾輪的 delta 值
        delta = ctypes.c_short(hook_struct.mouseData >> 16).value

        # 判斷是垂直還是水平捲動
        is_horizontal = (wParam == WM_MOUSEHWHEEL)

        # Shift + 垂直滾輪 → 水平捲動
        if self.settings.shift_horizontal and not is_horizontal:
            shift_pressed = (GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
            if shift_pressed:
                is_horizontal = True

        # 計算捲動量（考慮加速度）
        # 取得前景程式的個別設定（如果有的話）
        app_params = self._get_foreground_app_params()
        scroll_amount = self._calculate_scroll_amount(delta, app_params)

        # 啟動平滑動畫
        if is_horizontal and self.settings.horizontal_smoothness:
            self._add_smooth_scroll_h(scroll_amount, app_params)
        elif is_horizontal:
            # 水平但不使用平滑 → 直接發送
            self._send_scroll_event(int(scroll_amount), horizontal=True)
        else:
            self._add_smooth_scroll_v(scroll_amount, app_params)

        # 攔截原始事件（回傳 1 表示已處理）
        return 1

    def _get_process_name_by_pid(self, pid: int) -> str:
        """透過 PID 取得程式的執行檔名稱（僅回傳檔名，如 chrome.exe）"""
        # 先檢查快取
        if pid in self._process_name_cache:
            return self._process_name_cache[pid]

        exe_name = ""
        try:
            handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                try:
                    buf = ctypes.create_unicode_buffer(512)
                    buf_size = ctypes.wintypes.DWORD(512)
                    if QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_size)):
                        # 從完整路徑中擷取檔名
                        full_path = buf.value
                        exe_name = full_path.rsplit("\\", 1)[-1].lower()
                finally:
                    CloseHandle(handle)
        except Exception:
            pass

        # 寫入快取（限制快取大小）
        if len(self._process_name_cache) >= self._cache_max_size:
            # 清除一半快取
            keys_to_remove = list(self._process_name_cache.keys())[:self._cache_max_size // 2]
            for k in keys_to_remove:
                del self._process_name_cache[k]
        self._process_name_cache[pid] = exe_name

        return exe_name

    def _is_foreground_blacklisted(self) -> bool:
        """檢查目前前景視窗程式是否在黑名單中"""
        try:
            hwnd = GetForegroundWindow()
            if not hwnd:
                return False

            pid = ctypes.wintypes.DWORD(0)
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == 0:
                return False

            exe_name = self._get_process_name_by_pid(pid.value)
            if not exe_name:
                return False

            # 比對黑名單（不分大小寫）
            blacklist_lower = [name.lower() for name in self.settings.blacklist]
            return exe_name in blacklist_lower
        except Exception:
            return False

    def _get_foreground_app_params(self) -> dict:
        """
        取得前景程式的個別設定參數。
        如果該程式有個別設定，回傳覆蓋後的參數；否則回傳全域參數。
        """
        try:
            hwnd = GetForegroundWindow()
            if not hwnd:
                return self.settings.get_app_settings("")

            pid = ctypes.wintypes.DWORD(0)
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == 0:
                return self.settings.get_app_settings("")

            exe_name = self._get_process_name_by_pid(pid.value)
            return self.settings.get_app_settings(exe_name)
        except Exception:
            return self.settings.get_app_settings("")

    def _calculate_scroll_amount(self, delta: int, app_params: dict = None) -> float:
        """計算考慮加速度後的捲動量"""
        if app_params is None:
            app_params = self._get_foreground_app_params()

        now = time.perf_counter() * 1000  # 轉換為毫秒
        time_since_last = now - self._last_scroll_time

        # 標準化 delta（一般為 ±120，對應一個滾輪刻度）
        direction = 1 if delta > 0 else -1
        step_size = app_params.get('step_size', self.settings.step_size)
        base_amount = step_size * direction

        # 加速度計算
        accel_delta = app_params.get('acceleration_delta', self.settings.acceleration_delta)
        accel_max = app_params.get('acceleration_max', self.settings.acceleration_max)

        if time_since_last < accel_delta:
            # 快速連續捲動 → 加速
            accel_factor = 1.0 - (time_since_last / accel_delta)
            # 使用更平滑的加速度累加
            self._scroll_velocity = min(
                self._scroll_velocity + accel_factor * 0.8,
                accel_max
            )
        else:
            # 捲動間隔較長 → 快速衰減速度
            decay = min(time_since_last / 300.0, 1.0) # 300ms 內衰減完畢
            self._scroll_velocity = max(1.0, self._scroll_velocity * (1.0 - decay))

        self._last_scroll_time = now

        return base_amount * self._scroll_velocity

    def _add_smooth_scroll_v(self, amount: float, app_params: dict = None) -> None:
        """新增垂直平滑捲動目標"""
        with self._animation_lock:
            remaining = self._target_scroll_v - self._current_scroll_v

            # 偵測方向反轉：新的捲動量與剩餘動量方向相反
            if remaining != 0 and ((amount > 0) != (remaining > 0)):
                # 方向反轉 → 立即丟棄舊動量，以新方向重新出發
                self._target_scroll_v = amount
                self._current_scroll_v = 0
                self._scroll_velocity = 1.0  # 重置加速度
            else:
                # 同方向 → 正常疊加
                self._target_scroll_v += amount

            # 儲存當前的 app_params 供動畫執行緒使用
            self._current_app_params_v = app_params

            if not self._animating_v:
                self._animating_v = True
                self._current_scroll_v = 0
                self._animation_start_v = time.perf_counter()
                thread = threading.Thread(
                    target=self._animate_scroll_v,
                    daemon=True
                )
                thread.start()
            else:
                # 重設時間，實現「連續推動」的物理感
                self._current_scroll_v = 0
                self._animation_start_v = time.perf_counter()

    def _add_smooth_scroll_h(self, amount: float, app_params: dict = None) -> None:
        """新增水平平滑捲動目標"""
        with self._animation_lock:
            remaining = self._target_scroll_h - self._current_scroll_h

            # 偵測方向反轉：新的捲動量與剩餘動量方向相反
            if remaining != 0 and ((amount > 0) != (remaining > 0)):
                # 方向反轉 → 立即丟棄舊動量，以新方向重新出發
                self._target_scroll_h = amount
                self._current_scroll_h = 0
                self._scroll_velocity = 1.0
            else:
                self._target_scroll_h += amount

            # 儲存當前的 app_params 供動畫執行緒使用
            self._current_app_params_h = app_params

            if not self._animating_h:
                self._animating_h = True
                self._current_scroll_h = 0
                self._animation_start_h = time.perf_counter()
                thread = threading.Thread(
                    target=self._animate_scroll_h,
                    daemon=True
                )
                thread.start()
            else:
                self._current_scroll_h = 0
                self._animation_start_h = time.perf_counter()

    def _animate_scroll_v(self) -> None:
        """垂直捲動動畫執行緒"""
        self._animate_scroll(vertical=True)

    def _animate_scroll_h(self) -> None:
        """水平捲動動畫執行緒"""
        self._animate_scroll(vertical=False)

    def _animate_scroll(self, vertical: bool = True) -> None:
        """通用的捲動動畫邏輯"""
        # 使用 240Hz 更新率以確保高更新頻率螢幕的流暢度
        FRAME_INTERVAL = 1.0 / 240
        accumulated_remainder = 0.0

        # 取得該方向的 app_params
        if vertical:
            app_params = getattr(self, '_current_app_params_v', None)
        else:
            app_params = getattr(self, '_current_app_params_h', None)

        # 決定動畫時間和緩動參數
        if app_params:
            anim_time = app_params.get('animation_time', self.settings.animation_time)
            tail_ratio = app_params.get('tail_head_ratio', self.settings.tail_head_ratio)
        else:
            anim_time = self.settings.animation_time
            tail_ratio = self.settings.tail_head_ratio

        while self._running:
            with self._animation_lock:
                if vertical:
                    total_target = self._target_scroll_v
                    current = self._current_scroll_v
                    start_time = self._animation_start_v
                else:
                    total_target = self._target_scroll_h
                    current = self._current_scroll_h
                    start_time = self._animation_start_h

            remaining = total_target - current
            
            # 停止條件：當剩餘像素極小且時間已超過動畫長度
            if abs(remaining) < 0.5:
                with self._animation_lock:
                    if vertical:
                        self._target_scroll_v = 0
                        self._current_scroll_v = 0
                        self._animating_v = False
                    else:
                        self._target_scroll_h = 0
                        self._current_scroll_h = 0
                        self._animating_h = False
                break

            # 計算動畫進度
            elapsed = (time.perf_counter() - start_time) * 1000  # 毫秒
            duration = anim_time
            
            # 安全防護：避免 duration 為 0
            if duration <= 0: duration = 1.0

            if elapsed >= duration:
                progress = 1.0
            else:
                progress = elapsed / duration

            # 套用緩動函數
            if self.settings.animation_easing:
                eased = custom_ease(progress, tail_ratio)
            else:
                eased = progress  # 線性

            # 計算當前幀應達到的絕對位置
            target_pos = total_target * eased
            
            # 計算本幀增量 (Delta)
            delta = target_pos - current

            # 加上之前累積的小數部分 (Sub-pixel rendering)
            delta += accumulated_remainder
            int_delta = int(delta)
            accumulated_remainder = delta - int_delta

            if int_delta != 0:
                self._send_scroll_event(int_delta, horizontal=not vertical)
                with self._animation_lock:
                    if vertical:
                        self._current_scroll_v += int_delta
                    else:
                        self._current_scroll_h += int_delta

            if progress >= 1.0:
                # 動畫結束，處理剩餘殘差
                final_remaining = int(remaining - int_delta) # 修正剩餘量計算
                if abs(final_remaining) > 0:
                    self._send_scroll_event(final_remaining, horizontal=not vertical)
                
                with self._animation_lock:
                    if vertical:
                        self._target_scroll_v = 0
                        self._current_scroll_v = 0
                        self._animating_v = False
                    else:
                        self._target_scroll_h = 0
                        self._current_scroll_h = 0
                        self._animating_h = False
                break

            time.sleep(FRAME_INTERVAL)

    def _send_scroll_event(self, delta: int, horizontal: bool = False) -> None:
        """發送模擬的滾輪捲動事件"""
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = 0
        inp.union.mi.dy = 0
        # 這裡將 delta 轉為 unsigned long，避免 ctypes 報錯
        inp.union.mi.mouseData = ctypes.wintypes.DWORD(delta & 0xFFFFFFFF)
        inp.union.mi.dwFlags = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
        inp.union.mi.time = 0
        inp.union.mi.dwExtraInfo = ULONG_PTR(self.INJECTED_FLAG)

        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))