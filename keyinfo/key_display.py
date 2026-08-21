import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPixmap
from pynput import keyboard, mouse
import time

class KeyDisplay(QWidget):
    """按键显示窗口类"""
    key_signal = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
        self.keys = {
            'W': False, 'A': False, 'S': False, 'D': False,
            'Space': False,
            'LMB': False, 'RMB': False,
        }
        
        # CPS 相关变量 - 存储最近1秒内的点击时间戳
        self.lmb_clicks = []  # 存储左键点击时间戳
        self.rmb_clicks = []  # 存储右键点击时间戳
        self.lmb_cps = 0.0
        self.rmb_cps = 0.0
        
        # 加载鼠标图片
        self.lmb_pixmap = self.load_image("lmb.png")
        self.rmb_pixmap = self.load_image("rmb.png")
        
        # 如果图片加载失败，创建默认图案
        if self.lmb_pixmap.isNull():
            print("警告: 无法加载 lmb.png，使用默认图案")
            self.lmb_pixmap = self.create_default_image("L")
        if self.rmb_pixmap.isNull():
            print("警告: 无法加载 rmb.png，使用默认图案")
            self.rmb_pixmap = self.create_default_image("R")
        
        self.key_signal.connect(self.update_key_state)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
        
        # CPS 更新定时器（每秒更新10次，更流畅）
        self.cps_timer = QTimer()
        self.cps_timer.timeout.connect(self.update_cps)
        self.cps_timer.start(100)  # 100ms更新一次
        
        self.dragging = False
        self.drag_position = QPoint()
        
        self._listeners_started = False
        
    def load_image(self, filename):
        """尝试多种方式加载图片"""
        # 方式1: 直接加载
        pixmap = QPixmap(filename)
        if not pixmap.isNull():
            print(f"✓ 成功加载: {filename}")
            return pixmap
        
        # 方式2: 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            print(f"✓ 成功加载: {filepath}")
            return pixmap
        
        # 方式3: 获取当前工作目录
        cwd = os.getcwd()
        filepath = os.path.join(cwd, filename)
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            print(f"✓ 成功加载: {filepath}")
            return pixmap
        
        print(f"✗ 无法加载图片: {filename}")
        print(f"  当前工作目录: {os.getcwd()}")
        print(f"  脚本所在目录: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"  请确保图片文件在这些目录下")
        
        return QPixmap()
    
    def create_default_image(self, text):
        """创建默认图片"""
        pixmap = QPixmap(50, 50)
        pixmap.fill(QColor(60, 60, 60, 200))
        
        from PyQt5.QtGui import QPainter, QColor, QFont
        painter = QPainter(pixmap)
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()
        
        return pixmap
        
    def initUI(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 370, 200)  # 增加高度以容纳CPS显示
        self.font = QFont("Arial", 14, QFont.Bold)
        self.cps_font = QFont("Arial", 12, QFont.Bold)
        
    def start_listeners(self):
        """启动键盘和鼠标监听"""
        if self._listeners_started:
            return
            
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char:
                    key_name = key.char.upper()
                    if key_name in ['W', 'A', 'S', 'D']:
                        self.key_signal.emit(key_name, True)
                elif key == keyboard.Key.space:
                    self.key_signal.emit('Space', True)
            except:
                pass
                
        def on_release(key):
            try:
                if hasattr(key, 'char') and key.char:
                    key_name = key.char.upper()
                    if key_name in ['W', 'A', 'S', 'D']:
                        self.key_signal.emit(key_name, False)
                elif key == keyboard.Key.space:
                    self.key_signal.emit('Space', False)
            except:
                pass
                
        def on_mouse_click(x, y, button, pressed):
            if pressed:  # 只在按下时记录
                current_time = time.time()
                if button == mouse.Button.left:
                    self.lmb_clicks.append(current_time)
                    self.key_signal.emit('LMB', True)
                elif button == mouse.Button.right:
                    self.rmb_clicks.append(current_time)
                    self.key_signal.emit('RMB', True)
            else:
                if button == mouse.Button.left:
                    self.key_signal.emit('LMB', False)
                elif button == mouse.Button.right:
                    self.key_signal.emit('RMB', False)
        
        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        
        self.keyboard_listener.daemon = True
        self.mouse_listener.daemon = True
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        self._listeners_started = True
        
    def stop_listeners(self):
        """停止监听器"""
        if self._listeners_started:
            if hasattr(self, 'keyboard_listener'):
                self.keyboard_listener.stop()
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
            self._listeners_started = False
        
    def update_key_state(self, key_name, is_pressed):
        if key_name in self.keys:
            self.keys[key_name] = is_pressed
            self.update()
    
    def update_cps(self):
        """更新CPS值 - 使用更精确的计算方法"""
        current_time = time.time()
        time_window = 1.0  # 1秒时间窗口
        
        # 清理超过时间窗口的记录
        self.lmb_clicks = [t for t in self.lmb_clicks if current_time - t <= time_window]
        self.rmb_clicks = [t for t in self.rmb_clicks if current_time - t <= time_window]
        
        # 精确计算CPS：使用时间窗口内的点击次数除以实际时间跨度
        if len(self.lmb_clicks) >= 2:
            # 如果有至少2次点击，使用第一次和最后一次的时间差计算
            time_span = self.lmb_clicks[-1] - self.lmb_clicks[0]
            if time_span > 0:
                # 精确计算：点击次数 / 时间跨度
                self.lmb_cps = (len(self.lmb_clicks) - 1) / time_span
            else:
                self.lmb_cps = len(self.lmb_clicks)
        elif len(self.lmb_clicks) == 1:
            # 只有1次点击，检查是否在1秒内
            if current_time - self.lmb_clicks[0] < time_window:
                self.lmb_cps = 1.0
            else:
                self.lmb_cps = 0.0
        else:
            self.lmb_cps = 0.0
        
        # 右键同样计算
        if len(self.rmb_clicks) >= 2:
            time_span = self.rmb_clicks[-1] - self.rmb_clicks[0]
            if time_span > 0:
                self.rmb_cps = (len(self.rmb_clicks) - 1) / time_span
            else:
                self.rmb_cps = len(self.rmb_clicks)
        elif len(self.rmb_clicks) == 1:
            if current_time - self.rmb_clicks[0] < time_window:
                self.rmb_cps = 1.0
            else:
                self.rmb_cps = 0.0
        else:
            self.rmb_cps = 0.0
        
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font)
        
        padding = 8
        spacing = 8
        key_size = 45
        
        key_width = key_size
        key_height = key_size
        
        # WASD 布局
        w_x = padding + key_width + spacing
        self.draw_key(painter, int(w_x), padding, key_width, key_height, "W", self.keys['W'])
        
        a_x = padding
        s_x = padding + key_width + spacing
        d_x = padding + 2 * (key_width + spacing)
        y_pos = padding + key_height + spacing
        
        self.draw_key(painter, int(a_x), int(y_pos), key_width, key_height, "A", self.keys['A'])
        self.draw_key(painter, int(s_x), int(y_pos), key_width, key_height, "S", self.keys['S'])
        self.draw_key(painter, int(d_x), int(y_pos), key_width, key_height, "D", self.keys['D'])
        
        # 空格键
        space_x = padding
        space_y = y_pos + key_height + spacing
        space_width = 3 * key_width + 2 * spacing
        space_height = int(key_height * 0.55)
        self.draw_key(painter, int(space_x), int(space_y), space_width, space_height, "——", self.keys['Space'])
        
        # 鼠标按键 - 放在右侧，贴近放置
        mouse_x = padding + 3 * (key_width + spacing) + spacing * 2
        mouse_y = padding + 10  # 稍微上移给CPS留空间
        
        mouse_width = 80
        mouse_height = 80
        mouse_spacing = -18  # 减小两张图片之间的距离
        
        # 左键 - 无背景框
        self.draw_mouse_key(painter, int(mouse_x), int(mouse_y), 
                           mouse_width, mouse_height, 
                           self.lmb_pixmap, self.keys['LMB'])
        
        # 右键 - 无背景框
        self.draw_mouse_key(painter, int(mouse_x + mouse_width + mouse_spacing), int(mouse_y), 
                           mouse_width, mouse_height, 
                           self.rmb_pixmap, self.keys['RMB'])
        
        # 绘制CPS显示（带背景）
        self.draw_cps(painter, mouse_x, mouse_y + mouse_height + 5, mouse_width, mouse_spacing)
        
    def draw_key(self, painter, x, y, width, height, text, pressed):
        if pressed:
            bg_color = QColor(255, 255, 255, 220)
            text_color = QColor(0, 0, 0, 255)
        else:
            bg_color = QColor(50, 50, 50, 200)
            text_color = QColor(180, 180, 180, 200)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, width, height, 5, 5)
        
        painter.setPen(text_color)
        painter.drawText(x, y, width, height, Qt.AlignCenter, text)
    
    def draw_mouse_key(self, painter, x, y, width, height, pixmap, pressed):
        """绘制鼠标按键 - 无背景框"""
        # 缩放图片
        scaled_pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 计算居中位置
        offset_x = (width - scaled_pixmap.width()) // 2
        offset_y = (height - scaled_pixmap.height()) // 2
        
        if pressed:
            # 点击时完全显示
            painter.setOpacity(1.0)
        else:
            # 未点击时降低亮度
            painter.setOpacity(0.4)
        
        # 直接绘制图片，不绘制背景框
        painter.drawPixmap(x + offset_x, y + offset_y, scaled_pixmap)
        
        # 重置透明度
        painter.setOpacity(1.0)
    
    def draw_cps(self, painter, start_x, y, width, spacing):
        """绘制CPS显示（带半透明灰色背景）"""
        painter.setFont(self.cps_font)
        
        # 计算CPS显示区域
        cps_height = 28
        cps_padding = -10
        total_width = width * 2 + spacing + cps_padding * 2
        
        # 绘制半透明灰色背景
        bg_rect_x = start_x - cps_padding
        bg_rect_y = y - 2
        bg_rect_width = total_width
        bg_rect_height = cps_height + 4
        
        painter.setBrush(QBrush(QColor(40, 40, 40, 180)))  # 半透明灰色
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(bg_rect_x), int(bg_rect_y), 
                               int(bg_rect_width), int(bg_rect_height), 
                               4, 4)  # 圆角
        
        # 计算文本位置
        text_y = y + 2
        lmb_x = start_x + width // 2 - 15
        rmb_x = start_x + width + spacing + width // 2 - 15
        sep_x = start_x + width + spacing // 2
        
        # 左键CPS - 白色，显示一位小数
        painter.setPen(QColor(255, 255, 255, 230))
        lmb_text = f"{self.lmb_cps:.1f}"
        painter.drawText(int(lmb_x), int(text_y), 30, cps_height, Qt.AlignCenter, lmb_text)
        
        # 分隔符 | - 灰色
        painter.setPen(QColor(200, 200, 200, 150))
        painter.drawText(int(sep_x - 5), int(text_y), 10, cps_height, Qt.AlignCenter, "|")
        
        # 右键CPS - 白色，显示一位小数
        painter.setPen(QColor(255, 255, 255, 230))
        rmb_text = f"{self.rmb_cps:.1f}"
        painter.drawText(int(rmb_x), int(text_y), 30, cps_height, Qt.AlignCenter, rmb_text)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_position)
            
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.stop_listeners()
        event.accept()


class KeyDisplayManager:
    """按键显示管理器 - 用于从其他文件调用的主要接口"""
    
    _instance = None
    _app = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def start(self, x=None, y=None):
        """启动按键显示窗口
        
        Args:
            x: 窗口X坐标（可选）
            y: 窗口Y坐标（可选）
        """
        if self._app is None:
            self._app = QApplication.instance()
            if self._app is None:
                self._app = QApplication(sys.argv)
        
        self.window = KeyDisplay()
        if x is not None and y is not None:
            self.window.move(x, y)
        self.window.start_listeners()
        self.window.show()
        
        print("✓ 按键显示已启动！")
        print("  - WASD 和 空格键 会高亮显示")
        print("  - 鼠标左键/右键 会高亮显示")
        print("  - 鼠标下方显示 CPS (每秒点击次数，精确到0.1)")
        print("  - 拖动窗口可以移动位置")
        
        return self.window
    
    def stop(self):
        """停止按键显示"""
        if hasattr(self, 'window') and self.window:
            self.window.close()
            self.window = None
        if self._app:
            self._app.quit()
            self._app = None
        print("✓ 按键显示已停止")
    
    def is_running(self):
        """检查是否正在运行"""
        return hasattr(self, 'window') and self.window is not None
    
    def run_forever(self):
        """进入事件循环（阻塞）"""
        if self._app:
            sys.exit(self._app.exec_())
    
    def process_events(self):
        """处理挂起的事件（非阻塞）"""
        if self._app:
            self._app.processEvents()


# 全局便捷函数
def show_key_display(x=None, y=None):
    """显示按键显示窗口（非阻塞）"""
    manager = KeyDisplayManager()
    return manager.start(x, y)

def hide_key_display():
    """隐藏按键显示窗口"""
    manager = KeyDisplayManager()
    manager.stop()

def is_key_display_running():
    """检查按键显示是否正在运行"""
    manager = KeyDisplayManager()
    return manager.is_running()


if __name__ == '__main__':
    # 直接运行时启动
    manager = KeyDisplayManager()
    manager.start()
    manager.run_forever()