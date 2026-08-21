"""
网络流量监控悬浮窗库
可用于显示实时上传/下载速度

使用方法:
    from traffic_monitor import TrafficMonitor
    
    # 创建监控器实例
    monitor = TrafficMonitor()
    
    # 显示悬浮窗
    monitor.show()
    
    # 隐藏悬浮窗
    monitor.hide()
    
    # 切换显示状态
    monitor.toggle()
    
    # 检查是否可见
    if monitor.is_visible():
        print("悬浮窗可见")
    
    # 更新位置到右上角
    monitor.move_to_top_right()
    
    # 关闭监控器
    monitor.close()

作者: AI Assistant
版本: 1.0.0
"""

import sys
import os
import psutil
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap

# 全局应用实例（确保只创建一个）
_app = None


class TrafficWidget(QWidget):
    """网络流量监控悬浮窗控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
        # 网络统计初始值
        self.prev_sent = psutil.net_io_counters().bytes_sent
        self.prev_recv = psutil.net_io_counters().bytes_recv
        
        # 定时器更新速度
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_speed)
        self.timer.start(1000)
        
        # 窗口拖拽相关
        self.dragging = False
        self.drag_position = QPoint()
        
        # 默认可见
        self._visible = True

    def initUI(self):
        # 窗口属性：透明背景，无边框，置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # 主布局：水平布局
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 下载图标标签
        self.download_icon_label = QLabel()
        self.download_icon_label.setAlignment(Qt.AlignCenter)
        down_icon = self.load_icon("down.png", script_dir)
        if down_icon:
            self.download_icon_label.setPixmap(down_icon)
        else:
            self.download_icon_label.setText("⬇")
        layout.addWidget(self.download_icon_label)
        
        # 下载速度数值标签
        self.download_speed_label = QLabel("0.0 KB/s")
        self.download_speed_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                font-family: "Consolas", "Courier New", monospace;
                background: transparent;
            }
        """)
        self.download_speed_label.setMinimumWidth(80)
        self.download_speed_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.download_speed_label)
        
        # 分隔符
        separator = QLabel("|")
        separator.setStyleSheet("color: #666666; font-size: 16px; background: transparent;")
        separator.setAlignment(Qt.AlignCenter)
        layout.addWidget(separator)
        
        # 上传图标标签
        self.upload_icon_label = QLabel()
        self.upload_icon_label.setAlignment(Qt.AlignCenter)
        up_icon = self.load_icon("up.png", script_dir)
        if up_icon:
            self.upload_icon_label.setPixmap(up_icon)
        else:
            self.upload_icon_label.setText("⬆")
        layout.addWidget(self.upload_icon_label)
        
        # 上传速度数值标签
        self.upload_speed_label = QLabel("0.0 KB/s")
        self.upload_speed_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                font-family: "Consolas", "Courier New", monospace;
                background: transparent;
            }
        """)
        self.upload_speed_label.setMinimumWidth(80)
        self.upload_speed_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.upload_speed_label)
        
        self.setLayout(layout)
        
        # 根据内容自适应宽度，固定高度
        self.setFixedHeight(45)
        self.adjustSize()
        
        # 设置默认位置（屏幕右上角）
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 50)

    def load_icon(self, filename, script_dir):
        """尝试多种方式加载图标"""
        # 方法1: 直接在当前目录加载
        pixmap = QPixmap(filename)
        if not pixmap.isNull():
            return pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 方法2: 使用完整路径
        full_path = os.path.join(script_dir, filename)
        pixmap = QPixmap(full_path)
        if not pixmap.isNull():
            return pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 方法3: 尝试当前工作目录
        cwd_path = os.path.join(os.getcwd(), filename)
        pixmap = QPixmap(cwd_path)
        if not pixmap.isNull():
            return pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 方法4: 尝试资源文件方式
        pixmap = QPixmap(f":/{filename}")
        if not pixmap.isNull():
            return pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        return None

    def paintEvent(self, event):
        """绘制半透明圆角背景 + 2px半透明灰色边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # 先绘制完全透明的背景
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(rect, Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # 绘制半透明深色背景
        painter.setBrush(QColor(30, 30, 30, 200))
        painter.setPen(Qt.NoPen)  # 关键：移除边框画笔
        
        # 绘制圆角矩形
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)
        
        super().paintEvent(event)

    def update_speed(self):
        """更新上传/下载速度"""
        try:
            net_io = psutil.net_io_counters()
            curr_sent = net_io.bytes_sent
            curr_recv = net_io.bytes_recv
            
            sent_speed = curr_sent - self.prev_sent
            recv_speed = curr_recv - self.prev_recv
            
            self.prev_sent = curr_sent
            self.prev_recv = curr_recv
            
            upload_text = self.format_speed(sent_speed)
            download_text = self.format_speed(recv_speed)
            
            self.upload_speed_label.setText(upload_text)
            self.download_speed_label.setText(download_text)
            
        except Exception as e:
            print(f"更新速度出错: {e}")

    def format_speed(self, bytes_per_sec):
        """格式化速度显示"""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.1f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

    # ========== 公共方法 ==========
    
    def show_widget(self):
        """显示悬浮窗"""
        self.show()
        self._visible = True
    
    def hide_widget(self):
        """隐藏悬浮窗"""
        self.hide()
        self._visible = False
    
    def toggle(self):
        """切换显示/隐藏状态"""
        if self._visible:
            self.hide_widget()
        else:
            self.show_widget()
    
    def is_visible(self):
        """检查悬浮窗是否可见"""
        return self._visible and self.isVisible()
    
    def move_to_top_right(self, offset_x=20, offset_y=50):
        """将窗口移动到屏幕右上角"""
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - offset_x, offset_y)
    
    def set_update_interval(self, milliseconds):
        """设置更新间隔（毫秒）"""
        self.timer.stop()
        self.timer.start(milliseconds)
    
    def close(self):
        """关闭监控器"""
        self.timer.stop()
        super().close()


class TrafficMonitor:
    """
    网络流量监控器主类
    
    使用方法:
        monitor = TrafficMonitor()
        monitor.show()
        monitor.hide()
        monitor.toggle()
    """
    
    def __init__(self):
        global _app
        
        # 检查是否已有QApplication实例
        if _app is None:
            _app = QApplication.instance()
            if _app is None:
                _app = QApplication(sys.argv)
                _app.setStyle('Fusion')
        
        self.widget = TrafficWidget()
    
    def show(self):
        """显示悬浮窗"""
        self.widget.show_widget()
    
    def hide(self):
        """隐藏悬浮窗"""
        self.widget.hide_widget()
    
    def toggle(self):
        """切换显示/隐藏状态"""
        self.widget.toggle()
    
    def is_visible(self):
        """检查悬浮窗是否可见"""
        return self.widget.is_visible()
    
    def move_to_top_right(self, offset_x=20, offset_y=50):
        """将窗口移动到屏幕右上角"""
        self.widget.move_to_top_right(offset_x, offset_y)
    
    def set_update_interval(self, milliseconds):
        """设置更新间隔（毫秒）"""
        self.widget.set_update_interval(milliseconds)
    
    def close(self):
        """关闭监控器（释放资源）"""
        self.widget.close()
    
    def get_widget(self):
        """获取底层QWidget实例（用于高级自定义）"""
        return self.widget
    
    def run(self):
        """运行事件循环（阻塞）"""
        global _app
        if _app:
            sys.exit(_app.exec_())


# ========== 使用示例 ==========
if __name__ == '__main__':
    # 创建监控器
    monitor = TrafficMonitor()
    
    # 显示
    monitor.show()
    
    # 运行事件循环
    monitor.run()