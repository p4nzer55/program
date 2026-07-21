import mss
import numpy as np
import cv2

class WindowCapture:
    def __init__(self, window_title=None):
        self.sct = mss.mss()
        self.window_title = window_title
        self.monitor = self.sct.monitors[1]
    
    def capture_full_screen(self):
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def capture_region(self, x, y, width, height):
        monitor = {
            "top": y,
            "left": x,
            "width": width,
            "height": height
        }
        screenshot = self.sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def find_window(self, title_pattern):
        try:
            import win32gui
            def callback(handle, extra):
                if title_pattern.lower() in win32gui.GetWindowText(handle).lower():
                    extra.append(handle)
                return True
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                rect = win32gui.GetWindowRect(windows[0])
                self.monitor = {
                    "top": rect[1],
                    "left": rect[0],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1]
                }
                return True
            return False
        except ImportError:
            print("警告: pywin32未安装，无法自动查找窗口")
            return False
    
    def release(self):
        self.sct.close()