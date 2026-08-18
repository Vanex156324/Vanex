"""
系统监控悬浮窗库
可用于显示CPU、网络延迟、内存和FPS信息
"""

import sys
import psutil
import subprocess
import re
import time
# time and deque removed since FPS display was removed
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class SystemMonitor:
    """系统监控类，管理悬浮窗的显示和控制"""
    
    # 屏幕角落位置枚举
    CORNER_TOP_LEFT = "top_left"
    CORNER_TOP_RIGHT = "top_right"
    CORNER_BOTTOM_LEFT = "bottom_left"
    CORNER_BOTTOM_RIGHT = "bottom_right"
    
    def __init__(self, corner=CORNER_TOP_RIGHT, margin=10, auto_start=True):
        """
        初始化系统监控
        
        Args:
            corner: 显示位置，可选值:
                   SystemMonitor.CORNER_TOP_LEFT
                   SystemMonitor.CORNER_TOP_RIGHT
                   SystemMonitor.CORNER_BOTTOM_LEFT
                   SystemMonitor.CORNER_BOTTOM_RIGHT
            margin: 距离屏幕边缘的像素距离
            auto_start: 是否自动启动监控
        """
        self.corner = corner
        self.margin = margin
        self._widget = None
        self._app = None
        self._is_running = False
        
        if auto_start:
            self.start()
    
    def start(self):
        """启动监控显示"""
        if self._is_running:
            return
        
        # 如果还没有创建QApplication，创建一个
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
            self._app.setStyle("Fusion")
        else:
            self._app = QApplication.instance()
        
        # 创建悬浮窗
        self._widget = _OverlayWidget(self.corner, self.margin)
        self._widget.show()
        self._is_running = True
    
    def stop(self):
        """停止监控并关闭窗口"""
        if self._widget:
            self._widget.close()
            self._widget = None
        self._is_running = False
    
    def show(self):
        """显示窗口（如果已隐藏）"""
        if self._widget:
            self._widget.show()
    
    def hide(self):
        """隐藏窗口（不关闭）"""
        if self._widget:
            self._widget.hide()
    
    def toggle_visibility(self):
        """切换显示/隐藏"""
        if self._widget:
            if self._widget.isVisible():
                self._widget.hide()
            else:
                self._widget.show()
    
    def is_visible(self):
        """检查窗口是否可见"""
        return self._widget is not None and self._widget.isVisible()
    
    def set_corner(self, corner):
        """
        设置显示位置
        
        Args:
            corner: SystemMonitor.CORNER_TOP_LEFT 等
        """
        self.corner = corner
        if self._widget:
            self._widget.set_corner(corner)
    
    def set_margin(self, margin):
        """设置距边缘的距离"""
        self.margin = margin
        if self._widget:
            self._widget.set_margin(margin)
    
    def set_font_size(self, size):
        """设置字体大小"""
        if self._widget:
            self._widget.set_font_size(size)
    
    def set_font_color(self, color):
        """设置字体颜色，如 '#d0d0d0' 或 'white'"""
        if self._widget:
            self._widget.set_font_color(color)
    
    def exec_(self):
        """运行事件循环（用于独立使用）"""
        if self._app:
            sys.exit(self._app.exec_())
    
    def update_now(self):
        """立即更新一次数据"""
        if self._widget:
            self._widget.update_stats()


class _OverlayWidget(QWidget):
    """内部实现的悬浮窗组件"""
    
    def __init__(self, corner, margin):
        super().__init__()
        self.corner = corner
        self.margin = margin
        
        # 窗口设置：无边框、置顶、透明背景
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # 自动调整大小以适应内容
        self.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Expanding)
        
        # 水平布局
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 创建单行显示标签（无背景）
        self.info_label = QLabel("CPU: --% | PING: --ms | MEM: --%")
        self.info_label.setFont(QFont("Consolas", 10, QFont.Bold))
        self.info_label.setStyleSheet(
            "color: #d0d0d0; background: transparent; font-weight: bold;"
        )
        
        layout.addWidget(self.info_label)
        self.setLayout(layout)
        
        # 调整窗口大小以适应内容
        self.adjustSize()
        
        # 定位到指定角落
        self.move_to_corner()
        
        # 计时器更新数据（每秒刷新）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)
        
        # 无 FPS 显示相关逻辑（已移除）

        # 网络延迟缓存
        self._last_ping = "--"
        
        # 保存当前位置（用于恢复）
        self._saved_position = None
    
    def get_screen_geometry(self):
        """获取屏幕可用区域"""
        return QApplication.primaryScreen().availableGeometry()

    def format_uptime(self, seconds: float) -> str:
        """将秒数格式化为 天d HH:MM:SS 或 HH:MM:SS 的可读字符串"""
        try:
            seconds = int(seconds)
            days, rem = divmod(seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, secs = divmod(rem, 60)
            if days > 0:
                return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except Exception:
            return "--:--:--"
    
    def clamp_position(self, x, y):
        """限制窗口位置在屏幕范围内"""
        screen_geo = self.get_screen_geometry()
        
        width = self.width()
        height = self.height()
        
        x = max(screen_geo.x(), min(x, screen_geo.x() + screen_geo.width() - width))
        y = max(screen_geo.y(), min(y, screen_geo.y() + screen_geo.height() - height))
        
        return x, y
    
    def move_to_corner(self):
        """将窗口移动到指定的角落"""
        screen_geo = self.get_screen_geometry()
        
        if self.corner == SystemMonitor.CORNER_TOP_LEFT:
            x = screen_geo.x() + self.margin
            y = screen_geo.y() + self.margin
        elif self.corner == SystemMonitor.CORNER_TOP_RIGHT:
            x = screen_geo.x() + screen_geo.width() - self.width() - self.margin
            y = screen_geo.y() + self.margin
        elif self.corner == SystemMonitor.CORNER_BOTTOM_LEFT:
            x = screen_geo.x() + self.margin
            y = screen_geo.y() + screen_geo.height() - self.height() - self.margin
        else:  # BOTTOM_RIGHT
            x = screen_geo.x() + screen_geo.width() - self.width() - self.margin
            y = screen_geo.y() + screen_geo.height() - self.height() - self.margin
        
        x, y = self.clamp_position(x, y)
        self.move(x, y)
        self._saved_position = (x, y)
    
    def set_corner(self, corner):
        """设置角落位置"""
        self.corner = corner
        self.move_to_corner()
    
    def set_margin(self, margin):
        """设置边距"""
        self.margin = margin
        self.move_to_corner()
    
    def set_font_size(self, size):
        """设置字体大小"""
        font = self.info_label.font()
        font.setPointSize(size)
        self.info_label.setFont(font)
        self.adjustSize()
        self.move_to_corner()
    
    def set_font_color(self, color):
        """设置字体颜色"""
        self.info_label.setStyleSheet(
            f"color: {color}; background: transparent; font-weight: bold;"
        )
    
    def moveEvent(self, event):
        """当窗口移动时，确保不超出屏幕边界"""
        super().moveEvent(event)
        pos = self.pos()
        x, y = self.clamp_position(pos.x(), pos.y())
        if x != pos.x() or y != pos.y():
            self.move(x, y)
        else:
            self._saved_position = (x, y)
    
    def resizeEvent(self, event):
        """当窗口大小变化时，重新验证位置"""
        super().resizeEvent(event)
        if hasattr(self, '_saved_position') and self._saved_position:
            x, y = self._saved_position
            x, y = self.clamp_position(x, y)
            self.move(x, y)
            self._saved_position = (x, y)
    
    def get_network_latency_simple(self, target="www.baidu.com"):
        """简单版本的ping检测（快速）"""
        return self._ping_single(target)
    
    def _ping_single(self, target, timeout=2):
        """单次ping，返回延迟毫秒数"""
        try:
            if sys.platform == 'win32':
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), target]
                output = subprocess.check_output(cmd, timeout=timeout + 0.5,
                                                 stderr=subprocess.STDOUT,
                                                 text=True, encoding='gbk', errors='ignore')
                match = re.search(r'(?:时间|time)[=:]\s*(\d+\.?\d*)\s*ms', output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), target]
                output = subprocess.check_output(cmd, timeout=timeout + 0.5,
                                                 stderr=subprocess.STDOUT,
                                                 text=True, errors='ignore')
                match = re.search(r'time[=:]\s*(\d+\.?\d*)\s*ms', output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        return None
    
    def update_stats(self):
        """更新 CPU占用、网络延迟、内存占用"""
        try:
            # CPU占用率
            cpu = psutil.cpu_percent(interval=None)
            
            # 获取网络延迟
            ping = self.get_network_latency_simple("www.baidu.com")
            
            if ping is not None:
                if ping < 1:
                    ping_text = " <1ms"
                else:
                    ping_text = f"{round(ping):>4}ms"
                self._last_ping = ping_text
            else:
                ping_text = " N/A "
                self._last_ping = "--"
            
            # 内存占用
            mem = psutil.virtual_memory().percent
            
            # 计算并格式化开机时长
            try:
                uptime_seconds = time.time() - psutil.boot_time()
                uptime_text = self.format_uptime(uptime_seconds)
            except Exception:
                uptime_text = "--"

            # 更新显示文本（包含开机时长）
            self.info_label.setText(
                f"CPU: {cpu:>5.1f}% | PING: {ping_text} | MEM: {mem:>5.1f}% | UP: {uptime_text}"
            )
            
            # 保存当前位置
            if hasattr(self, '_saved_position') and self._saved_position:
                old_pos = self._saved_position
            else:
                old_pos = (self.x(), self.y())
            
            # 自动调整窗口大小以适应新文本
            self.adjustSize()
            
            # adjustSize后重新应用保存的位置
            if old_pos:
                x, y = self.clamp_position(old_pos[0], old_pos[1])
                self.move(x, y)
                self._saved_position = (x, y)
            
        except Exception as e:
            print(f"更新数据时出错: {e}")
    
    # FPS 相关的接口已移除
    
    def mousePressEvent(self, event):
        """禁用鼠标按下事件 - 窗口不可拖拽"""
        event.ignore()
    
    def mouseMoveEvent(self, event):
        """禁用鼠标移动事件 - 窗口不可拖拽"""
        event.ignore()