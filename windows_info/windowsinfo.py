"""
窗口信息显示库
提供前景窗口信息显示功能，可被其他应用调用
"""

import sys
import ctypes
import os
from ctypes import wintypes
import psutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPixmap, QPen


class WindowInfoCore:
    """
    窗口信息核心类 - 提供信息获取功能，不依赖UI
    可被其他应用直接使用
    """
    def __init__(self):
        self._init_win_api()
        self._icon_cache = {}  # 缓存图标路径
        self._current_info = {
            'hwnd': None,
            'title': '-',
            'pid': None,
            'process_name': '-',
            'size': '-x-',
            'icon_type': 'user'
        }

    def _init_win_api(self):
        """初始化Windows API"""
        self.user32 = ctypes.windll.user32
        self.psapi = ctypes.windll.psapi
        self.kernel32 = ctypes.windll.kernel32
        self.advapi32 = ctypes.windll.advapi32

        self.GetForegroundWindow = self.user32.GetForegroundWindow
        self.GetWindowTextW = self.user32.GetWindowTextW
        self.GetWindowTextLengthW = self.user32.GetWindowTextLengthW
        self.GetWindowThreadProcessId = self.user32.GetWindowThreadProcessId
        self.GetWindowRect = self.user32.GetWindowRect
        self.IsWindow = self.user32.IsWindow

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG)]

        self.RECT = RECT

    def is_process_elevated(self, pid):
        """检查进程是否以管理员权限运行"""
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            TOKEN_QUERY = 0x0008
            TokenElevation = 20

            OpenProcess = self.kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE

            hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not hProcess:
                return False

            hToken = wintypes.HANDLE()
            if not self.advapi32.OpenProcessToken(hProcess, TOKEN_QUERY, ctypes.byref(hToken)):
                self.kernel32.CloseHandle(hProcess)
                return False

            class TOKEN_ELEVATION(ctypes.Structure):
                _fields_ = [("TokenIsElevated", wintypes.DWORD)]

            te = TOKEN_ELEVATION()
            ret_len = wintypes.DWORD()
            ok = self.advapi32.GetTokenInformation(
                hToken, TokenElevation, ctypes.byref(te), 
                ctypes.sizeof(te), ctypes.byref(ret_len)
            )

            self.kernel32.CloseHandle(hToken)
            self.kernel32.CloseHandle(hProcess)

            return bool(ok and te.TokenIsElevated != 0)
        except Exception:
            return False

    def get_window_title(self, hwnd):
        """获取窗口标题"""
        length = self.GetWindowTextLengthW(hwnd)
        if length == 0:
            return "无标题"
        buff = ctypes.create_unicode_buffer(length + 1)
        self.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value

    def get_window_pid(self, hwnd):
        """获取窗口进程ID"""
        pid = wintypes.DWORD()
        self.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    def get_process_name(self, pid):
        """获取进程名称"""
        try:
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "未知进程"

    def get_window_size(self, hwnd):
        """获取窗口尺寸"""
        rect = self.RECT()
        if self.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            return f"{width}x{height}"
        return "-x-"

    def get_foreground_info(self):
        """获取当前前景窗口的所有信息"""
        hwnd = self.GetForegroundWindow()
        if not hwnd or not self.IsWindow(hwnd):
            return {
                'hwnd': None,
                'title': '-',
                'pid': None,
                'process_name': '-',
                'size': '-x-',
                'icon_type': 'user'
            }

        pid = self.get_window_pid(hwnd)
        title = self.get_window_title(hwnd)
        process_name = self.get_process_name(pid)
        size = self.get_window_size(hwnd)

        # 判断图标类型
        icon_type = 'user'
        try:
            proc = psutil.Process(pid)
            username = proc.username()
            if username and 'SYSTEM' in username.upper():
                icon_type = 'system'
            elif self.is_process_elevated(pid):
                icon_type = 'admin'
        except Exception:
            pass

        return {
            'hwnd': hwnd,
            'title': title,
            'pid': pid,
            'process_name': process_name,
            'size': size,
            'icon_type': icon_type
        }

    def get_icon_path(self, icon_type, base_dir=None):
        """获取图标路径"""
        icon_map = {
            'system': 'system.png',
            'admin': 'admin.png',
            'user': 'user.png'
        }
        filename = icon_map.get(icon_type, 'user.png')
        
        if base_dir:
            cache_key = f"{base_dir}_{filename}"
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = os.path.join(base_dir, filename)
            return self._icon_cache[cache_key]
        
        # 如果没有指定目录，返回文件名
        return filename


class WindowInfoDisplay(QWidget):
    """
    窗口信息显示组件 - 独立的UI显示
    可被其他应用嵌入或单独显示
    """
    
    def __init__(self, parent=None, auto_update=True, update_interval=500):
        """
        初始化显示组件
        
        Args:
            parent: 父窗口
            auto_update: 是否自动更新
            update_interval: 更新间隔（毫秒）
        """
        super().__init__(parent)
        self.core = WindowInfoCore()
        self._enabled = True
        self._update_interval = update_interval
        
        self.initUI()
        self.setupTimer(auto_update)
        
    def initUI(self):
        """初始化UI"""
        # 窗口设置：无边框、透明、置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.setFixedWidth(380)
        self.setMinimumHeight(80)
        self.move(50, 50)

        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        # 第一行：进程名称、PID、窗口大小
        self.line1Label = QLabel("-  |  -  |  -")
        self.line1Label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.line1Label.setStyleSheet("color: #E0E0E0; background: transparent;")
        self.line1Label.setAlignment(Qt.AlignLeft)

        # 第二行：图标 + 窗口标题
        self.iconLabel = QLabel()
        self.iconLabel.setFixedSize(50, 50)
        self.iconLabel.setStyleSheet("background: transparent; color: #E0E0E0;")
        self.iconLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.line2Label = QLabel("-")
        self.line2Label.setFont(QFont("Microsoft YaHei", 9))
        self.line2Label.setStyleSheet("color: #C0C0C0; background: transparent;")
        self.line2Label.setAlignment(Qt.AlignLeft)
        self.line2Label.setWordWrap(True)

        h2 = QHBoxLayout()
        h2.setContentsMargins(0, 0, 0, 0)
        h2.setSpacing(6)
        h2.addWidget(self.iconLabel)
        h2.addWidget(self.line2Label)

        layout.addWidget(self.line1Label)
        layout.addLayout(h2)
        self.setLayout(layout)

        self.dragPos = None

    def setupTimer(self, auto_update):
        """设置定时器"""
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.updateInfo)
        if auto_update:
            self.updateTimer.start(self._update_interval)

    def set_enabled(self, enabled):
        """
        启用或禁用显示更新
        
        Args:
            enabled: True启用，False禁用
        """
        self._enabled = enabled
        if enabled:
            self.updateTimer.start(self._update_interval)
            self.updateInfo()  # 立即更新一次
        else:
            self.updateTimer.stop()
            # 显示禁用状态
            self.line1Label.setText("⏸ 已禁用  |  -  |  -")
            self.line2Label.setText("窗口信息显示已禁用")
            self.iconLabel.setPixmap(QPixmap())
            self.iconLabel.setText("⏸")

    def is_enabled(self):
        """检查是否启用"""
        return self._enabled

    def set_update_interval(self, interval_ms):
        """
        设置更新间隔
        
        Args:
            interval_ms: 间隔毫秒数
        """
        self._update_interval = interval_ms
        if self._enabled:
            self.updateTimer.stop()
            self.updateTimer.start(interval_ms)

    def get_current_info(self):
        """获取当前显示的信息"""
        return {
            'title': self.line2Label.text(),
            'process_name': self.line1Label.text().split('|')[0].strip() if '|' in self.line1Label.text() else '-',
            'pid': self.line1Label.text().split('|')[1].strip() if '|' in self.line1Label.text() else '-',
            'size': self.line1Label.text().split('|')[2].strip() if '|' in self.line1Label.text() else '-'
        }

    def updateInfo(self):
        """更新信息"""
        if not self._enabled:
            return

        info = self.core.get_foreground_info()
        
        if info['hwnd']:
            # 第一行：进程名 | PID | 窗口大小
            self.line1Label.setText(f"{info['process_name']}  |  {info['pid']}  |  {info['size']}")
            
            # 第二行：窗口标题
            self.line2Label.setText(info['title'])
            
            # 设置图标
            self._set_icon(info['icon_type'])
        else:
            self.line1Label.setText("-  |  -  |  -")
            self.line2Label.setText("-")

    def _set_icon(self, icon_type):
        """设置图标"""
        icon_path = self.core.get_icon_path(icon_type, os.path.dirname(__file__))
        pix = QPixmap(icon_path)
        if not pix.isNull():
            self.iconLabel.setPixmap(pix.scaled(self.iconLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.iconLabel.setText('')
        else:
            self.iconLabel.setPixmap(QPixmap())
            # 使用字符图标作为备选
            icon_chars = {'system': '🖥️', 'admin': '🛡️', 'user': '👤'}
            self.iconLabel.setText(icon_chars.get(icon_type, '💻'))

    def paintEvent(self, event):
        """绘制背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 背景：半透明深色
        painter.setBrush(QBrush(QColor(30, 30, 30, 200)))
        # 边框：3px 半透明灰色
        pen = QPen(QColor(160, 160, 160, 50))
        pen.setWidth(3)
        painter.setPen(pen)
        # 将绘制区域内缩半个边框宽度以避免裁剪
        r = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(r, 10, 10)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragPos is not None:
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.dragPos = None


class WindowInfoManager:
    """
    窗口信息管理器 - 提供高级控制接口
    方便其他应用集成和管理
    """
    
    def __init__(self):
        self._app = None
        self._display = None
        self._is_running = False

    def start(self, parent=None, x=50, y=50, update_interval=500):
        """
        启动显示窗口
        
        Args:
            parent: 父窗口
            x, y: 窗口位置
            update_interval: 更新间隔（毫秒）
        
        Returns:
            WindowInfoDisplay: 显示组件实例
        """
        if self._display is None:
            # 如果没有QApplication实例，创建一个
            if QApplication.instance() is None:
                self._app = QApplication(sys.argv)
                self._app.setStyle("Fusion")
                self._setup_palette()
            
            self._display = WindowInfoDisplay(parent, auto_update=True, update_interval=update_interval)
            self._display.move(x, y)
            self._display.show()
            self._is_running = True
        
        return self._display

    def stop(self):
        """停止并关闭显示窗口"""
        if self._display is not None:
            self._display.close()
            self._display = None
            self._is_running = False

    def enable(self):
        """启用显示更新"""
        if self._display is not None:
            self._display.set_enabled(True)

    def disable(self):
        """禁用显示更新"""
        if self._display is not None:
            self._display.set_enabled(False)

    def toggle(self):
        """切换启用/禁用状态"""
        if self._display is not None:
            self._display.set_enabled(not self._display.is_enabled())

    def is_running(self):
        """检查是否正在运行"""
        return self._is_running

    def is_enabled(self):
        """检查是否启用"""
        if self._display is not None:
            return self._display.is_enabled()
        return False

    def get_display(self):
        """获取显示组件实例"""
        return self._display

    def get_core(self):
        """获取核心信息获取器"""
        if self._display is not None:
            return self._display.core
        return WindowInfoCore()

    def get_foreground_info(self):
        """直接获取前景窗口信息（无需显示窗口）"""
        core = WindowInfoCore()
        return core.get_foreground_info()

    @staticmethod
    def _setup_palette():
        """设置应用调色板"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.instance().setPalette(palette)


# 全局单例管理器
_manager = None

def get_manager():
    """获取全局管理器实例（单例模式）"""
    global _manager
    if _manager is None:
        _manager = WindowInfoManager()
    return _manager


# 便捷函数
def show_window_info(x=50, y=50, update_interval=500):
    """
    显示窗口信息窗（便捷函数）
    
    Args:
        x, y: 窗口位置
        update_interval: 更新间隔（毫秒）
    
    Returns:
        WindowInfoManager: 管理器实例
    """
    manager = get_manager()
    manager.start(x=x, y=y, update_interval=update_interval)
    return manager

def hide_window_info():
    """隐藏窗口信息窗"""
    manager = get_manager()
    manager.stop()

def enable_info():
    """启用信息更新"""
    manager = get_manager()
    manager.enable()

def disable_info():
    """禁用信息更新"""
    manager = get_manager()
    manager.disable()

def toggle_info():
    """切换信息更新"""
    manager = get_manager()
    manager.toggle()

def get_current_window_info():
    """
    获取当前前景窗口信息（不显示窗口）
    
    Returns:
        dict: 包含窗口信息的字典
    """
    core = WindowInfoCore()
    return core.get_foreground_info()


# 保持独立运行能力
def main():
    """独立运行主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = WindowInfoDisplay()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()