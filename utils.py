"""
OpenSmoothScroll - 工具函數模組
提供開機啟動管理、單實例鎖定等輔助功能。
"""

import os
import sys
import ctypes
import winreg
import tempfile

# 程式名稱
APP_NAME = "OpenSmoothScroll"

def get_resource_path(relative_path: str) -> str:
    """
    取得資源檔案的絕對路徑。
    支援 PyInstaller 打包後的 _MEIPASS 路徑。
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ─── 開機啟動管理 ──────────────────────────────────────────────────────

def get_startup_registry_key():
    """取得或開啟開機啟動的登錄機碼"""
    try:
        return winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
    except OSError:
         # Fallback incase of permission issues or key missing
         return winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run"
         )


def is_startup_enabled() -> bool:
    """檢查是否已設定為開機啟動"""
    try:
        key = get_startup_registry_key()
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            try:
                winreg.CloseKey(key)
            except:
                pass
    except Exception:
        return False


def enable_startup() -> bool:
    """設定開機啟動"""
    try:
        # 判斷是否為 PyInstaller 打包的 EXE
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            command = f'"{exe_path}"'
        else:
            # 原始碼執行模式
            python_exe = sys.executable
            # 修正路徑處理，確保正確指向 main.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, "main.py")
            # 修正：使用 pythonw.exe (無主控台) 如果可能，或確保路徑正確引用
            command = f'"{python_exe}" "{script_path}"'

        key = get_startup_registry_key()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        print(f"[資訊] 已設定開機啟動: {command}")
        return True
    except Exception as e:
        print(f"[錯誤] 設定開機啟動失敗: {e}")
        return False


def disable_startup() -> bool:
    """取消開機啟動"""
    try:
        key = get_startup_registry_key()
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass  # 本來就沒設定
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[錯誤] 取消開機啟動失敗: {e}")
        return False


def toggle_startup() -> bool:
    """切換開機啟動，回傳新狀態"""
    if is_startup_enabled():
        disable_startup()
        return False
    else:
        enable_startup()
        return True


# ─── 單實例鎖定 ────────────────────────────────────────────────────────

_mutex_handle = None

def acquire_single_instance_lock() -> bool:
    """
    嘗試取得單實例鎖定。
    如果已有另一個實例正在執行，回傳 False。
    """
    global _mutex_handle
    mutex_name = "Global\\OpenSmoothScroll_SingleInstance_Mutex"

    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(
        None, True, mutex_name
    )

    ERROR_ALREADY_EXISTS = 183
    last_error = ctypes.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:
        # 已有其他實例在執行
        if _mutex_handle:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
        return False

    return True


def release_single_instance_lock() -> None:
    """釋放單實例鎖定"""
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.ReleaseMutex(_mutex_handle)
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
