# clock_widget.py
import sys
import math
from datetime import datetime
from typing import Optional, Literal

from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics
from PyQt5.QtWidgets import QApplication, QWidget


class TransparentClock(QWidget):
    """透明时钟组件，支持模拟时钟和数字时钟两种模式"""
    
    def __init__(
        self,
        mode: Literal["analog", "digital"] = "analog",
        parent: Optional[QWidget] = None,
        size: int = 300,
        bg_color: tuple = (80, 80, 80, 120),
        border_color: tuple = (180, 180, 180),
        text_color: tuple = (255, 255, 255),
        **kwargs
    ):
        """
        初始化时钟
        
        Args:
            mode: 时钟模式，"analog" 模拟时钟 或 "digital" 数字时钟
            parent: 父窗口
            size: 窗口大小（模拟时钟为直径，数字时钟为宽度）
            bg_color: 背景颜色 (R, G, B, A)
            border_color: 边框颜色 (R, G, B)
            text_color: 文字/指针颜色 (R, G, B)
            **kwargs: 其他样式参数
                - digital_height: 数字时钟高度（默认80）
                - corner_radius: 圆角半径（默认10）
                - font_family: 字体（默认"Arial"）
                - font_size: 数字时钟字体大小（默认40）
                - show_seconds: 是否显示秒针/秒数（默认True）
        """
        super().__init__(parent)
        
        self.mode = mode
        self.bg_color = bg_color
        self.border_color = border_color
        self.text_color = text_color
        
        # 样式参数
        self.digital_height = kwargs.get("digital_height", 80)
        self.corner_radius = kwargs.get("corner_radius", 10)
        self.font_family = kwargs.get("font_family", "Arial")
        self.font_size = kwargs.get("font_size", 40)
        self.show_seconds = kwargs.get("show_seconds", True)
        
        # 窗口属性：无边框，透明背景，置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 根据模式设置大小：
        # - 模拟模式：size 表示窗口直径
        # - 数字模式：size 表示文字字号（font size），窗口根据字体自动调整
        if mode == "analog":
            self.setFixedSize(size, size)
        else:
            # treat `size` as font size for digital mode
            self.font_size = size
            # compute suitable window size based on font metrics
            try:
                font = QFont(self.font_family, self.font_size, QFont.Bold)
                fm = QFontMetrics(font)
                sample = "00:00:00" if self.show_seconds else "00:00"
                rect = fm.boundingRect(sample)
                w = rect.width() + 40
                h = rect.height() + 20
                self.setFixedSize(max(100, w), max(30, h))
            except Exception:
                self.setFixedSize(size, self.digital_height)
        
        # 拖动相关变量
        self.dragging = False
        self.drag_position = QPoint()
        
        # 是否可见
        self._visible = True
        
        # 计时器：每秒更新一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        
        self.update()

    # ---- 公共控制方法 ----
    def show_clock(self):
        """显示时钟"""
        self._visible = True
        self.show()
    
    def hide_clock(self):
        """隐藏时钟"""
        self._visible = False
        self.hide()
    
    def toggle_visibility(self):
        """切换显示/隐藏"""
        if self._visible:
            self.hide_clock()
        else:
            self.show_clock()
    
    def set_mode(self, mode: Literal["analog", "digital"]):
        """切换时钟模式"""
        self.mode = mode
        # 当切换到数字模式时，调整窗口以匹配当前 font_size
        try:
            if mode == "digital":
                self.set_font_size(self.font_size)
            else:
                # 回到模拟模式：保持当前宽度作为直径
                s = max(100, min(1000, getattr(self, 'width', self.width())))
                self.setFixedSize(s, s)
        except Exception:
            pass
        self.update()

    def set_font_size(self, font_size: int):
        """设置数字模式下的文字大小并调整窗口尺寸"""
        try:
            self.font_size = int(font_size)
            font = QFont(self.font_family, self.font_size, QFont.Bold)
            fm = QFontMetrics(font)
            sample = "00:00:00" if self.show_seconds else "00:00"
            rect = fm.boundingRect(sample)
            w = rect.width() + 40
            h = rect.height() + 20
            self.setFixedSize(max(80, w), max(24, h))
            self.update()
        except Exception:
            pass
    
    def set_bg_color(self, r: int, g: int, b: int, a: int = 120):
        """设置背景颜色"""
        self.bg_color = (r, g, b, a)
        self.update()
    
    def set_border_color(self, r: int, g: int, b: int):
        """设置边框颜色"""
        self.border_color = (r, g, b)
        self.update()
    
    def set_text_color(self, r: int, g: int, b: int):
        """设置文字/指针颜色"""
        self.text_color = (r, g, b)
        self.update()
    
    def set_always_on_top(self, on_top: bool):
        """设置是否置顶显示"""
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()  # 需要重新显示才能生效

    # ---- 鼠标事件：实现拖动 ----
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
    
    # 双击切换模式
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_mode()

    def toggle_mode(self):
        """切换模拟/数字模式"""
        if self.mode == "analog":
            self.set_mode("digital")
        else:
            self.set_mode("analog")

    def paintEvent(self, event):
        if not self._visible:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.mode == "analog":
            self.draw_analog_clock(painter)
        else:
            self.draw_digital_clock(painter)

    def draw_analog_clock(self, painter):
        """绘制模拟时钟（圆形）"""
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 10
        
        r, g, b, a = self.bg_color
        br, bg, bb = self.border_color
        tr, tg, tb = self.text_color
        
        # 绘制半透明刻度盘背景 + 边框
        painter.setBrush(QBrush(QColor(r, g, b, a)))
        painter.setPen(QPen(QColor(br, bg, bb), 2))
        painter.drawEllipse(center, radius, radius)

        # 绘制刻度
        painter.setPen(QPen(QColor(tr, tg, tb), 2))
        painter.setBrush(QBrush(QColor(tr, tg, tb)))

        # 12个主刻度
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            inner_radius = radius - 20
            outer_radius = radius - 5

            x1 = int(center.x() + inner_radius * math.cos(angle))
            y1 = int(center.y() + inner_radius * math.sin(angle))
            x2 = int(center.x() + outer_radius * math.cos(angle))
            y2 = int(center.y() + outer_radius * math.sin(angle))

            painter.drawLine(x1, y1, x2, y2)

        # 60个副刻度
        painter.setPen(QPen(QColor(200, 200, 200, 180), 1))
        for i in range(60):
            if i % 5 == 0:
                continue
            angle = math.radians(i * 6 - 90)
            inner_radius = radius - 15
            outer_radius = radius - 5

            x1 = int(center.x() + inner_radius * math.cos(angle))
            y1 = int(center.y() + inner_radius * math.sin(angle))
            x2 = int(center.x() + outer_radius * math.cos(angle))
            y2 = int(center.y() + outer_radius * math.sin(angle))

            painter.drawLine(x1, y1, x2, y2)

        # 获取当前时间
        now = datetime.now()
        hour = now.hour % 12
        minute = now.minute
        second = now.second

        hour_angle = math.radians((hour + minute / 60) * 30 - 90)
        minute_angle = math.radians(minute * 6 - 90)
        second_angle = math.radians(second * 6 - 90)

        # 时针
        hour_length = radius * 0.5
        painter.setPen(QPen(QColor(tr, tg, tb), 6, Qt.SolidLine, Qt.RoundCap))
        hour_x = int(center.x() + hour_length * math.cos(hour_angle))
        hour_y = int(center.y() + hour_length * math.sin(hour_angle))
        painter.drawLine(center.x(), center.y(), hour_x, hour_y)

        # 分针
        minute_length = radius * 0.7
        painter.setPen(QPen(QColor(min(tr+20,255), min(tg+20,255), min(tb+20,255)), 4, Qt.SolidLine, Qt.RoundCap))
        minute_x = int(center.x() + minute_length * math.cos(minute_angle))
        minute_y = int(center.y() + minute_length * math.sin(minute_angle))
        painter.drawLine(center.x(), center.y(), minute_x, minute_y)

        # 秒针（如果启用）
        if self.show_seconds:
            second_length = radius * 0.8
            painter.setPen(QPen(QColor(180, 180, 180), 2, Qt.SolidLine, Qt.RoundCap))
            second_x = int(center.x() + second_length * math.cos(second_angle))
            second_y = int(center.y() + second_length * math.sin(second_angle))
            painter.drawLine(center.x(), center.y(), second_x, second_y)

        # 中心圆点
        painter.setBrush(QBrush(QColor(tr, tg, tb)))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawEllipse(center, 5, 5)

    def draw_digital_clock(self, painter):
        """绘制数字时钟（长方形背景，只显示时间）"""
        rect = self.rect()
        center = rect.center()
        # 数字模式不显示背景板，只绘制时间文字
        tr, tg, tb = self.text_color

        # 获取当前时间字符串
        now = datetime.now()
        if self.show_seconds:
            time_str = now.strftime("%H:%M:%S")
        else:
            time_str = now.strftime("%H:%M")

        # 绘制时间文字
        painter.setPen(QPen(QColor(tr, tg, tb), 1))
        font = QFont(self.font_family, self.font_size, QFont.Bold)
        painter.setFont(font)

        fm = painter.fontMetrics()
        time_rect = fm.boundingRect(time_str)
        time_x = center.x() - time_rect.width() // 2
        # 基于 font metrics 计算垂直居中
        time_y = center.y() + (time_rect.height() - fm.descent()) // 2

        painter.drawText(time_x, time_y, time_str)

    def sizeHint(self):
        return self.size()


# ---- 便捷函数 ----
def create_clock(
    mode: Literal["analog", "digital"] = "analog",
    size: int = 300,
    **kwargs
) -> TransparentClock:
    """
    创建时钟组件的便捷函数
    
    Args:
        mode: "analog" 或 "digital"
        size: 窗口大小
        **kwargs: 其他样式参数
    
    Returns:
        TransparentClock 实例
    """
    return TransparentClock(mode=mode, size=size, **kwargs)


def run_clock(
    mode: Literal["analog", "digital"] = "analog",
    size: int = 300,
    **kwargs
):
    """
    独立运行时钟（创建QApplication并启动事件循环）
    
    Args:
        mode: "analog" 或 "digital"
        size: 窗口大小
        **kwargs: 其他样式参数
    """
    app = QApplication(sys.argv)
    clock = TransparentClock(mode=mode, size=size, **kwargs)
    clock.show()
    sys.exit(app.exec_())


# ---- 独立运行入口 ----
def main():
    """命令行入口，支持参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="透明时钟")
    parser.add_argument(
        "-m", "--mode",
        choices=["analog", "digital"],
        default="analog",
        help="时钟模式: analog(模拟) 或 digital(数字)"
    )
    parser.add_argument(
        "-s", "--size",
        type=int,
        default=300,
        help="窗口大小"
    )
    parser.add_argument(
        "--bg-color",
        nargs=3,
        type=int,
        default=[80, 80, 80],
        help="背景颜色 RGB (0-255)"
    )
    parser.add_argument(
        "--bg-alpha",
        type=int,
        default=120,
        help="背景透明度 (0-255)"
    )
    parser.add_argument(
        "--border-color",
        nargs=3,
        type=int,
        default=[180, 180, 180],
        help="边框颜色 RGB (0-255)"
    )
    parser.add_argument(
        "--text-color",
        nargs=3,
        type=int,
        default=[255, 255, 255],
        help="文字颜色 RGB (0-255)"
    )
    
    args = parser.parse_args()
    
    run_clock(
        mode=args.mode,
        size=args.size,
        bg_color=(*args.bg_color, args.bg_alpha),
        border_color=tuple(args.border_color),
        text_color=tuple(args.text_color)
    )


if __name__ == "__main__":
    main()