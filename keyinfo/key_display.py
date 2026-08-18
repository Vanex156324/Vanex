import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPainterPath
from pynput import keyboard, mouse

class KeyDisplay(QWidget):
    """按键显示窗口类"""
    key_signal = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
        self.keys = {
            'W': False, 'A': False, 'S': False, 'D': False,
            'Space': False, 'LMB': False, 'RMB': False,
        }
        
        self.key_signal.connect(self.update_key_state)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
        
        self.dragging = False
        self.drag_position = QPoint()
        
        self._listeners_started = False
        
    def initUI(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 450, 220)
        self.font = QFont("Arial", 14, QFont.Bold)
        
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
            if button == mouse.Button.left:
                self.key_signal.emit('LMB', pressed)
            elif button == mouse.Button.right:
                self.key_signal.emit('RMB', pressed)
        
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
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font)
        
        padding = 10
        spacing = 10
        key_size = 50
        
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
        space_height = int(key_height * 0.6)
        self.draw_key(painter, int(space_x), int(space_y), space_width, space_height, "——", self.keys['Space'])
        
        # 鼠标按键
        mouse_x = padding + 3 * (key_width + spacing) + 20
        mouse_y = padding + 20
        
        mouse_width = int(key_width * 2.0)
        mouse_height = int(key_height * 2.0)
        
        self.draw_mouse_key(painter, int(mouse_x), int(mouse_y), 
                           mouse_width // 2, mouse_height, 
                           "L", self.keys['LMB'], is_left=True)
        
        self.draw_mouse_key(painter, int(mouse_x + mouse_width // 2), int(mouse_y), 
                           mouse_width // 2, mouse_height, 
                           "R", self.keys['RMB'], is_left=False)
        
    def draw_key(self, painter, x, y, width, height, text, pressed):
        if pressed:
            bg_color = QColor(255, 255, 255, 220)
            text_color = QColor(0, 0, 0, 255)
            border_color = QColor(200, 200, 200, 200)
        else:
            bg_color = QColor(50, 50, 50, 200)
            text_color = QColor(180, 180, 180, 200)
            border_color = QColor(80, 80, 80, 150)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        # 绘制圆角矩形
        painter.drawRoundedRect(x, y, width, height, 5, 5)
        
        painter.setPen(text_color)
        painter.drawText(x, y, width, height, Qt.AlignCenter, text)
    
    def draw_mouse_key(self, painter, x, y, width, height, text, pressed, is_left):
        path = QPainterPath()
        
        if is_left:
            path.moveTo(x + 8, y)
            path.lineTo(x + width, y)
            path.lineTo(x + width, y + height)
            path.lineTo(x + 8, y + height)
            path.quadTo(x, y + height, x, y + height - 8)
            path.lineTo(x, y + 8)
            path.quadTo(x, y, x + 8, y)
            path.closeSubpath()
        else:
            path.moveTo(x, y)
            path.lineTo(x + width - 8, y)
            path.quadTo(x + width, y, x + width, y + 8)
            path.lineTo(x + width, y + height - 8)
            path.quadTo(x + width, y + height, x + width - 8, y + height)
            path.lineTo(x, y + height)
            path.closeSubpath()
        
        if pressed:
            bg_color = QColor(255, 255, 255, 220)
            text_color = QColor(0, 0, 0, 255)
            border_color = QColor(200, 200, 200, 200)
        else:
            bg_color = QColor(50, 50, 50, 200)
            text_color = QColor(180, 180, 180, 200)
            border_color = QColor(80, 80, 80, 150)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        painter.drawPath(path)
        
        if is_left:
            painter.setPen(QPen(QColor(80, 80, 80, 150), 1))
            painter.drawLine(x + width, y + 5, x + width, y + height - 5)
        
        painter.setPen(text_color)
        if len(text) <= 3:
            font_size = 11
        else:
            font_size = 9
        font = painter.font()
        font.setPointSize(font_size)
        painter.setFont(font)
        painter.drawText(x, y, width, height, Qt.AlignCenter, text)

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