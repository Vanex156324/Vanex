# cloud_music_tracker.py
"""
网易云音乐歌词跟踪器 - Python库
使用方法:
    from cloud_music_tracker import CloudMusicTracker, start_tracker, stop_tracker
    
    # 启动跟踪器
    tracker = start_tracker()
    
    # 或者使用类
    tracker = CloudMusicTracker()
    tracker.show()
    
    # 停止跟踪器
    stop_tracker(tracker)
"""

import sys
import math
import os
import win32gui
import win32process
import win32con
import ctypes
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 引入Windows API
user32 = ctypes.windll.user32

# 全局应用实例
_app = None
_tracker_instance = None


class WaveWidget(QWidget):
    """海浪波动动画组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 35)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 动画参数
        self.wave_offset = 0
        self.wave_speed = 2
        self.amplitude = 5
        self.wave_length = 0.5
        
        # 启动动画
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)
        
    def update_wave(self):
        self.wave_offset += self.wave_speed
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        center_y = height - 8
        
        # 创建波浪路径
        path = QPainterPath()
        path.moveTo(0, height)
        
        for x in range(width + 1):
            y = center_y - self.amplitude * math.sin(
                (x + self.wave_offset) * self.wave_length * 0.1
            )
            path.lineTo(x, y)
        
        path.lineTo(width, height)
        path.closeSubpath()
        
        painter.setBrush(QColor(200, 200, 200, 50))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        # 第二条波浪
        path2 = QPainterPath()
        path2.moveTo(0, height)
        
        for x in range(width + 1):
            y = center_y - (self.amplitude * 1.6) * math.sin(
                (x + self.wave_offset * 1.3 + 50) * self.wave_length * 0.1
            )
            path2.lineTo(x, y)
        
        path2.lineTo(width, height)
        path2.closeSubpath()
        
        painter.setBrush(QColor(180, 180, 180, 30))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path2)


class CloudMusicTracker(QWidget):
    """网易云音乐歌词跟踪器主窗口"""
    
    # 自定义信号
    song_changed = pyqtSignal(str, str)  # 歌曲名, 艺术家
    play_state_changed = pyqtSignal(bool)  # 播放状态
    
    def __init__(self, parent=None, icon_dir=None):
        super().__init__(parent)
        self.icon_dir = icon_dir or os.path.dirname(os.path.abspath(__file__))
        self.current_song = ""
        self.is_playing = False
        self._stopped = False
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_music)
        self.timer.start(1000)
        
    def initUI(self):
        # 设置窗口为无边框、透明、置顶
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置窗口大小和位置
        self.setFixedSize(400, 195)
        self.move(QApplication.primaryScreen().geometry().width() - 420, 
                  QApplication.primaryScreen().geometry().height() - 215)
        
        # 设置等线字体
        font = QFont("等线", 13)
        font.setBold(True)
        self.setFont(font)
        
        # 样式
        self.setStyleSheet("""
            QWidget#main_widget {
                background-color: rgba(30, 30, 30, 200);
                border: none;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QLabel#song_label {
                font-size: 20px;
                color: #EEEEEE;
                padding: 12px 20px 2px 20px;
                font-family: '等线';
                font-weight: bold;
            }
            QLabel#artist_label {
                font-size: 16px;
                color: #AAAAAA;
                padding: 0px 20px 5px 20px;
                font-family: '等线';
                font-weight: bold;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 150);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 50, 200);
            }
        """)
        
        # 主容器
        main_widget = QWidget()
        main_widget.setObjectName('main_widget')
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 歌曲名称
        self.song_label = QLabel('等待播放...')
        self.song_label.setObjectName('song_label')
        self.song_label.setAlignment(Qt.AlignCenter)
        self.song_label.setWordWrap(True)
        layout.addWidget(self.song_label)
        
        # 作者名称
        self.artist_label = QLabel('')
        self.artist_label.setObjectName('artist_label')
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setWordWrap(True)
        layout.addWidget(self.artist_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        control_layout.setContentsMargins(20, 5, 20, 5)
        
        # 加载图标
        self.load_icons()
        
        # 上一首
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.left_icon)
        self.prev_btn.setIconSize(QSize(24, 24))
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setToolTip('上一首')
        self.prev_btn.clicked.connect(self.prev_song)
        control_layout.addWidget(self.prev_btn, alignment=Qt.AlignCenter)
        
        # 暂停/播放（放大）
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.stop_icon)
        self.play_btn.setIconSize(QSize(32, 32))
        self.play_btn.setFixedSize(50, 50)
        self.play_btn.setToolTip('暂停/播放')
        self.play_btn.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.play_btn, alignment=Qt.AlignCenter)
        
        # 下一首
        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.right_icon)
        self.next_btn.setIconSize(QSize(24, 24))
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setToolTip('下一首')
        self.next_btn.clicked.connect(self.next_song)
        control_layout.addWidget(self.next_btn, alignment=Qt.AlignCenter)
        
        layout.addLayout(control_layout)
        
        # 海浪动画
        self.wave_widget = WaveWidget()
        layout.addWidget(self.wave_widget, alignment=Qt.AlignBottom)
        
        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(main_widget)
        
        # 拖拽移动
        self.drag_pos = None
        self.mousePressEvent = self.mouse_press_event
        self.mouseMoveEvent = self.mouse_move_event
    
    def load_icons(self):
        """加载图标"""
        # 加载图片
        left_path = os.path.join(self.icon_dir, 'left.png')
        right_path = os.path.join(self.icon_dir, 'right.png')
        stop_path = os.path.join(self.icon_dir, 'stop.png')
        
        # 如果图片不存在，使用默认的emoji
        if os.path.exists(left_path):
            self.left_icon = QIcon(left_path)
        else:
            self.left_icon = self.create_text_icon('⏮')
        
        if os.path.exists(right_path):
            self.right_icon = QIcon(right_path)
        else:
            self.right_icon = self.create_text_icon('⏭')
        
        if os.path.exists(stop_path):
            self.stop_icon = QIcon(stop_path)
        else:
            self.stop_icon = self.create_text_icon('⏸')
    
    def create_text_icon(self, text):
        """创建文本图标（备用）"""
        pixmap = QPixmap(30, 30)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Segoe UI Symbol", 16))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)
        
    def send_media_key(self, key_code):
        """发送媒体控制按键"""
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
        
        hwnd = self.find_cloudmusic_window()
        if hwnd:
            app_command_map = {
                0xB3: 14,  # 暂停/播放
                0xB0: 11,  # 下一首
                0xB1: 12   # 上一首
            }
            if key_code in app_command_map:
                ctypes.windll.user32.SendMessageW(
                    hwnd, 0x0319, 0, app_command_map[key_code] * 0x10000
                )
    
    def find_cloudmusic_window(self):
        """查找网易云音乐窗口句柄"""
        try:
            def enum_callback(hwnd, hwnds):
                if win32gui.IsWindowVisible(hwnd):
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name == 'OrpheusBrowserHost':
                        hwnds.append(hwnd)
            hwnds = []
            win32gui.EnumWindows(enum_callback, hwnds)
            return hwnds[0] if hwnds else None
        except:
            return None
    
    def toggle_play(self):
        """暂停/播放"""
        self.send_media_key(0xB3)
        self.animate_button(self.play_btn)
        self.is_playing = not self.is_playing
        self.play_state_changed.emit(self.is_playing)
    
    def next_song(self):
        """下一首"""
        self.send_media_key(0xB0)
        self.animate_button(self.next_btn)
    
    def prev_song(self):
        """上一首"""
        self.send_media_key(0xB1)
        self.animate_button(self.prev_btn)
    
    def animate_button(self, btn):
        """按钮动画反馈"""
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 200);
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        QTimer.singleShot(300, lambda: btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 150);
            }
            QPushButton:pressed {
                background-color: rgba(50, 50, 50, 200);
            }
        """))
        
    def parse_song_info(self, window_title):
        if ' - ' in window_title:
            parts = window_title.split(' - ', 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        return window_title, ''
    
    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos()
    
    def mouse_move_event(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            delta = event.globalPos() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPos()
        
    def get_cloudmusic_window(self):
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name == 'OrpheusBrowserHost':
                        window_text = win32gui.GetWindowText(hwnd)
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        windows.append((hwnd, window_text, pid))
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            return windows
        except Exception as e:
            return []
    
    def check_music(self):
        if self._stopped:
            return
            
        try:
            windows = self.get_cloudmusic_window()
            
            if not windows:
                if self.current_song:
                    self.song_label.setText('未检测到网易云音乐')
                    self.song_label.setStyleSheet("color: #666666; font-size: 20px; font-weight: bold;")
                    self.artist_label.setText('')
                    self.wave_widget.timer.stop()
                self.current_song = ""
                return
            
            hwnd, window_title, pid = windows[0]
            
            if not win32gui.IsWindowVisible(hwnd):
                self.song_label.setText('窗口已隐藏')
                self.song_label.setStyleSheet("color: #666666; font-size: 20px; font-weight: bold;")
                self.artist_label.setText('')
                self.wave_widget.timer.stop()
                return
            
            song_name, artist = self.parse_song_info(window_title)
            song_key = f"{song_name}|{artist}"
            
            if song_key != self.current_song:
                self.song_label.setText(song_name)
                self.song_label.setStyleSheet("color: #EEEEEE; font-size: 20px; font-weight: bold;")
                
                if artist:
                    self.artist_label.setText(f'— {artist}')
                    self.artist_label.setStyleSheet("color: #AAAAAA; font-size: 16px; font-weight: bold;")
                else:
                    self.artist_label.setText('')
                
                self.current_song = song_key
                self.animate_update()
                self.song_changed.emit(song_name, artist)
                
                if not self.wave_widget.timer.isActive():
                    self.wave_widget.timer.start(30)
                    
        except Exception as e:
            self.song_label.setText('检测出错')
            self.artist_label.setText('')
            self.wave_widget.timer.stop()
    
    def animate_update(self):
        self.song_label.setStyleSheet("color: #AAAAAA; font-size: 20px; font-weight: bold;")
        QTimer.singleShot(300, lambda: self.song_label.setStyleSheet("color: #EEEEEE; font-size: 20px; font-weight: bold;"))
    
    def stop(self):
        """停止跟踪器"""
        self._stopped = True
        self.timer.stop()
        self.wave_widget.timer.stop()
        self.close()
    
    def set_position(self, x, y):
        """设置窗口位置"""
        self.move(x, y)
    
    def get_current_song(self):
        """获取当前歌曲信息"""
        return self.song_label.text(), self.artist_label.text().replace('— ', '')


def start_tracker(icon_dir=None):
    """
    启动网易云音乐歌词跟踪器
    
    Args:
        icon_dir: 图标文件夹路径，默认为当前目录
    
    Returns:
        CloudMusicTracker: 跟踪器实例
    """
    global _app, _tracker_instance
    
    if _app is None:
        _app = QApplication(sys.argv)
        _app.setStyle('Fusion')
    
    _tracker_instance = CloudMusicTracker(icon_dir=icon_dir)
    _tracker_instance.show()
    
    return _tracker_instance


def stop_tracker(tracker=None):
    """
    停止网易云音乐歌词跟踪器
    
    Args:
        tracker: CloudMusicTracker实例，如果为None则停止全局实例
    """
    global _tracker_instance
    
    if tracker is None:
        tracker = _tracker_instance
    
    if tracker:
        tracker.stop()
        _tracker_instance = None


def get_tracker_instance():
    """
    获取当前跟踪器实例
    
    Returns:
        CloudMusicTracker: 当前跟踪器实例，如果没有启动则返回None
    """
    global _tracker_instance
    return _tracker_instance


def main():
    """命令行入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    tracker = CloudMusicTracker()
    tracker.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()