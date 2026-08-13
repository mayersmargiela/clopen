from __future__ import annotations

import os
from collections.abc import Callable


class HotkeyError(RuntimeError):
    pass


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _WM_HOTKEY = 0x0312
    _PM_REMOVE = 0x0001
    _MOD_CONTROL = 0x0002
    _MOD_SHIFT = 0x0004
    _MOD_NOREPEAT = 0x4000
    _HOTKEY_ID = 0x434C  # "CL", inside the application-reserved ID range.

    class _Point(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class _Message(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", _Point),
            ("lPrivate", wintypes.DWORD),
        ]

    _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    _user32.RegisterHotKey.restype = wintypes.BOOL
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.UnregisterHotKey.restype = wintypes.BOOL
    _user32.PeekMessageW.argtypes = [
        ctypes.POINTER(_Message),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
        wintypes.UINT,
    ]
    _user32.PeekMessageW.restype = wintypes.BOOL


class GlobalHotkey:
    """Register Ctrl+Shift+E and dispatch it from the current thread queue."""

    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self.registered = False

    def register(self) -> None:
        if os.name != "nt":
            raise HotkeyError("全局快捷键只支持 Windows")
        if self.registered:
            return
        modifiers = _MOD_CONTROL | _MOD_SHIFT | _MOD_NOREPEAT
        if not _user32.RegisterHotKey(None, _HOTKEY_ID, modifiers, ord("E")):
            error = ctypes.get_last_error()
            raise HotkeyError(f"Ctrl+Shift+E 注册失败（Windows 错误 {error}）")
        self.registered = True

    def poll(self) -> None:
        if os.name != "nt" or not self.registered:
            return
        message = _Message()
        while _user32.PeekMessageW(
            ctypes.byref(message),
            None,
            _WM_HOTKEY,
            _WM_HOTKEY,
            _PM_REMOVE,
        ):
            if int(message.wParam) == _HOTKEY_ID:
                self.callback()

    def matches_native_message(self, message_address: int) -> bool:
        """Dispatch a WM_HOTKEY observed by Qt's native event filter."""
        if os.name != "nt" or not self.registered or not message_address:
            return False
        message = _Message.from_address(message_address)
        if int(message.message) != _WM_HOTKEY or int(message.wParam) != _HOTKEY_ID:
            return False
        self.callback()
        return True

    def unregister(self) -> None:
        if os.name == "nt" and self.registered:
            _user32.UnregisterHotKey(None, _HOTKEY_ID)
        self.registered = False
