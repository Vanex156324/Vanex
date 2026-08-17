"""
RadarScanner - 局域网设备扫描雷达组件

使用方法:
    from radar_scanner import RadarScanner
    
    # 创建雷达窗口
    radar = RadarScanner()
    
    # 设置扫描间隔（秒）
    radar.set_scan_interval(30)
    
    # 设置窗口大小
    radar.set_window_size(300, 300)
    
    # 显示窗口
    radar.show_window()
    
    # 隐藏窗口
    radar.hide_window()
    
    # 关闭窗口
    radar.close_window()
"""

import sys
import math
import subprocess
import threading
import random
import platform
import socket
import time
import concurrent.futures
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QListWidget, 
                             QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

# 全局QApplication实例
_app = None


class ScanWorker(QObject):
    """在独立 QThread 中执行网络扫描，发出信号到主线程更新 UI"""
    device_found = pyqtSignal(str, str)
    scan_finished = pyqtSignal()

    def __init__(self, ip_prefix, parent=None):
        super().__init__(parent)
        self.ip_prefix = ip_prefix
        # 控制运行/停止
        self._running = True
        # 并发线程数（可调整）
        self.max_workers = 100
        # 单次 ping 超时（毫秒）
        self.ping_timeout_ms = 800

    def _get_hostname(self, ip):
        # 优先使用 nbtstat（Windows NetBIOS 名称），失败则尝试反向 DNS
        try:
            if platform.system().lower().startswith('win'):
                try:
                    result = subprocess.run(['nbtstat', '-A', ip],
                                            capture_output=True, text=True, encoding='gbk', timeout=2)
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '<00>' in line and 'UNIQUE' in line:
                            parts = line.split()
                            if len(parts) >= 1:
                                name = parts[0].strip()
                                if name and not name.startswith('..'):
                                    return name
                except Exception:
                    pass

            # 反向 DNS
            try:
                name = socket.gethostbyaddr(ip)[0]
                if name:
                    return name
            except Exception:
                pass
            return ip
        except Exception:
            return ip

    def stop(self):
        """请求停止扫描（线程安全）"""
        self._running = False

    def run(self):
        """
        更可靠与更快的扫描实现：使用线程池并发 ping，平台兼容性检测，
        对每次发现先去重再发射信号，支持外部中止请求。
        """
        try:
            found = set()

            # 选择 ping 参数（尽量让 ping 本身更快，同时依赖 subprocess.timeout 做最终裁决）
            is_win = platform.system().lower().startswith('win')
            # 单个 ping 的超时（秒）用于 subprocess.run timeout
            per_call_timeout = max(0.5, self.ping_timeout_ms / 1000.0 + 0.2)

            def _ping_and_check(i):
                if not self._running:
                    return None
                ip = f"{self.ip_prefix}.{i}"
                try:
                    if is_win:
                        cmd = ['ping', '-n', '1', '-w', str(self.ping_timeout_ms), ip]
                    else:
                        # -c 1 一次，-W 超时（秒）可能是小数但大部分系统要求整数
                        cmd = ['ping', '-c', '1', '-W', str(max(1, int(math.ceil(self.ping_timeout_ms / 1000.0)))), ip]

                    result = subprocess.run(cmd, capture_output=True, timeout=per_call_timeout)
                    if result.returncode == 0:
                        # 首选使用快速反向解析以获取更友好的名称
                        hostname = self._get_hostname(ip)
                        return (ip, hostname)
                except Exception:
                    return None
                return None

            # 使用线程池并发 ping，减少整体扫描时间
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = {ex.submit(_ping_and_check, i): i for i in range(1, 255)}
                for fut in concurrent.futures.as_completed(futures):
                    if not self._running:
                        break
                    try:
                        res = fut.result()
                        if res:
                            ip, hostname = res
                            if ip not in found:
                                found.add(ip)
                                # 直接发信号，UI 侧会批量处理
                                try:
                                    self.device_found.emit(ip, hostname)
                                except Exception:
                                    pass
                    except Exception:
                        # 忽略单个任务错误
                        pass

            # 完成或被中止后发出结束信号
            try:
                self.scan_finished.emit()
            except Exception:
                pass
        except Exception as e:
            print(f"ScanWorker 出错: {e}")
            try:
                self.scan_finished.emit()
            except Exception:
                pass


class RadarScanner(QWidget):
    """
    雷达扫描组件主类
    提供局域网设备扫描和可视化显示功能
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_scan()
        
    def _init_ui(self):
        """初始化UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 300)
        self.center = QPoint(self.width() // 2, self.height() // 2)
        self.radius = min(self.width(), self.height()) // 2 - 10

        # 拖拽相关
        self.dragging = False
        self.drag_position = QPoint()

        # 设备列表
        self.devices = []
        self.device_lock = threading.Lock()
        
        # 列表窗口
        self.device_list_window = None
        # 扫光动画相关
        self.sweep_active = False
        self.sweep_radius = 0.0
        self.sweep_speed = 6.0  # 每帧增加像素
        self.sweep_width = 6  # 环宽度
        self.sweep_timer = QTimer()
        self.sweep_timer.timeout.connect(self._on_sweep_tick)
        
    def _init_scan(self):
        """初始化扫描功能"""
        self.scanning = False
        self.scan_interval = 30
        
        # 启动扫描
        # 延迟不立即启动扫描，等窗口显示或外部调用 start_scan
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.start_scan)
        self.scan_timer.start(self.scan_interval * 1000)

        # 用于收集从 ScanWorker 发来的设备通知，批量处理以避免主线程被频繁打断
        self._pending_devices = []
        self._pending_lock = threading.Lock()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._flush_pending_devices)
        self._update_timer.start(100)  # 每100ms批量处理一次

    def _start_sweep(self):
        """开始一次从中心向外扩散的扫光动画"""
        try:
            # 重置并启动定时器（如果已经在运行则重启）
            self.sweep_radius = 0.0
            self.sweep_active = True
            if self.sweep_timer.isActive():
                self.sweep_timer.stop()
            # 大约每 30ms 更新一次动画，帧率约 33fps
            self.sweep_timer.start(30)
            # 触发重绘
            try:
                self.update()
            except Exception:
                pass
        except Exception:
            pass

    def _on_sweep_tick(self):
        """扫光定时器回调，推进动画并在完成时停止"""
        try:
            self.sweep_radius += self.sweep_speed
            # 当扫光完全超出雷达半径后停止动画
            if self.sweep_radius - self.sweep_width > self.radius:
                try:
                    self.sweep_timer.stop()
                except Exception:
                    pass
                self.sweep_active = False
                self.sweep_radius = 0.0
            # 请求重绘
            try:
                self.update()
            except Exception:
                pass
        except Exception:
            pass

    # ==================== 公开接口 ====================
    
    def show_window(self):
        """显示雷达窗口"""
        self.show()
        
    def hide_window(self):
        """隐藏雷达窗口"""
        self.hide()
        if self.device_list_window:
            self.device_list_window.hide()
            
    def close_window(self):
        """关闭雷达窗口并释放资源"""
        if self.scan_timer:
            self.scan_timer.stop()
        # 停止扫光动画定时器
        try:
            if hasattr(self, 'sweep_timer') and self.sweep_timer is not None:
                try:
                    self.sweep_timer.stop()
                except Exception:
                    pass
        except Exception:
            pass
        # 请求停止正在进行的扫描（如果有）
        try:
            if hasattr(self, '_scan_worker') and self._scan_worker is not None:
                try:
                    self._scan_worker.stop()
                except Exception:
                    pass
        except Exception:
            pass
        self.scanning = False
        if self.device_list_window:
            self.device_list_window.close()
            self.device_list_window = None
        self.close()
        
    def set_window_size(self, width, height):
        """
        设置窗口大小
        :param width: 窗口宽度（像素）
        :param height: 窗口高度（像素）
        """
        if width < 150 or height < 150:
            width = max(150, width)
            height = max(150, height)
        self.setFixedSize(width, height)
        self.center = QPoint(self.width() // 2, self.height() // 2)
        self.radius = min(self.width(), self.height()) // 2 - 10
        
        # 更新现有设备位置
        self._update_device_positions()
        self.update()
        
    def set_scan_interval(self, seconds):
        """
        设置扫描间隔
        :param seconds: 扫描间隔（秒），最小值为5秒
        """
        if seconds < 5:
            seconds = 5
        self.scan_interval = seconds
        if self.scan_timer:
            self.scan_timer.stop()
            self.scan_timer.start(self.scan_interval * 1000)
            
    def get_device_count(self):
        """
        获取当前在线设备数量
        :return: 在线设备数量
        """
        with self.device_lock:
            return sum(1 for d in self.devices if d[4])
            
    def get_devices(self):
        """
        获取当前在线设备列表
        :return: [(ip, hostname, x, y), ...] 设备列表
        """
        with self.device_lock:
            return [(d[0], d[1], d[2], d[3]) for d in self.devices if d[4]]
            
    def get_device_names(self):
        """
        获取当前在线设备名称列表
        :return: [hostname, ...] 设备名称列表
        """
        with self.device_lock:
            return [d[1] for d in self.devices if d[4]]

    # ==================== 私有方法 ====================
    
    def _update_device_positions(self):
        """更新设备在雷达上的位置"""
        with self.device_lock:
            for i in range(len(self.devices)):
                ip, hostname, _, _, online = self.devices[i]
                if online:
                    angle = random.uniform(0, 2 * math.pi)
                    r = random.uniform(self.radius * 0.2, self.radius * 0.85)
                    x = self.center.x() + r * math.cos(angle)
                    y = self.center.y() + r * math.sin(angle)
                    self.devices[i] = (ip, hostname, x, y, online)
                    
    def _get_ip_prefix(self):
        """获取本机IP段"""
        # 优先使用 socket 获取本机 IP（跨平台且通常可靠）
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # 不实际建立连接，只用于确定本地出口地址
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            if ip and '.' in ip:
                return '.'.join(ip.split('.')[:-1])
        except Exception:
            pass

        # 回退到解析 ipconfig（仅 Windows）
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4' in line or 'IP Address' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip()
                        if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                            return '.'.join(ip.split('.')[:-1])
            return '192.168.1'
        except Exception:
            return '192.168.1'
            
    def _get_hostname(self, ip):
        """获取主机名"""
        try:
            result = subprocess.run(['nbtstat', '-A', ip], 
                                  capture_output=True, text=True, encoding='gbk', timeout=2)
            lines = result.stdout.split('\n')
            for line in lines:
                if '<00>' in line and 'UNIQUE' in line:
                    parts = line.split()
                    if len(parts) >= 1:
                        name = parts[0].strip()
                        if name and not name.startswith('..'):
                            return name
            return ip
        except:
            return ip
            
    def _add_device(self, ip, hostname):
        """添加设备"""
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(self.radius * 0.2, self.radius * 0.85)
        x = self.center.x() + r * math.cos(angle)
        y = self.center.y() + r * math.sin(angle)
        
        with self.device_lock:
            self.devices.append([ip, hostname, x, y, True])

    # ==================== 事件处理 ====================
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_device_list()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            if self.device_list_window and self.device_list_window.isVisible():
                self._update_list_position()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景圆
        painter.setBrush(QBrush(QColor(40, 40, 40, 180)))
        painter.setPen(QPen(QColor(80, 80, 80), 1.5))
        painter.drawEllipse(self.center, self.radius, self.radius)

        # 同心圆
        painter.setPen(QPen(QColor(120, 120, 120, 150), 1, Qt.DashLine))
        for r in range(self.radius // 4, self.radius, self.radius // 4):
            painter.drawEllipse(self.center, r, r)

        # 十字线
        painter.setPen(QPen(QColor(120, 120, 120, 150), 1))
        painter.drawLine(self.center.x() - self.radius, self.center.y(),
                         self.center.x() + self.radius, self.center.y())
        painter.drawLine(self.center.x(), self.center.y() - self.radius,
                         self.center.x(), self.center.y() + self.radius)

        # 设备点
        with self.device_lock:
            for ip, hostname, x, y, online in self.devices:
                if not online:
                    continue
                painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
                painter.setPen(QPen(QColor(200, 200, 200, 150), 1))
                painter.drawEllipse(QPoint(int(x), int(y)), 5, 5)

        # 中心亮点
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.center, 4, 4)

        # 扫光动画：从中心向外扩散的环
        try:
            if getattr(self, 'sweep_active', False):
                # alpha 随半径增长衰减
                frac = min(1.0, max(0.0, self.sweep_radius / max(1.0, float(self.radius))))
                alpha = int(max(20, 180 * (1.0 - frac)))
                pen = QPen(QColor(255, 255, 255, alpha))
                pen.setWidth(self.sweep_width)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                r = int(self.sweep_radius)
                painter.drawEllipse(self.center, r, r)
        except Exception:
            pass

        # 边缘刻度
        painter.setPen(QPen(QColor(160, 160, 160, 180), 1.5))
        for deg in range(0, 360, 30):
            inner_r = self.radius - 12
            outer_r = self.radius - 4
            rad = math.radians(deg - 90)
            x1 = self.center.x() + inner_r * math.cos(rad)
            y1 = self.center.y() + inner_r * math.sin(rad)
            x2 = self.center.x() + outer_r * math.cos(rad)
            y2 = self.center.y() + outer_r * math.sin(rad)
            painter.drawLine(QPoint(int(x1), int(y1)), QPoint(int(x2), int(y2)))

    # ==================== 扫描功能 ====================
    
    def start_scan(self):
        """启动扫描"""
        if self.scanning:
            return
        self.scanning = True
        # 启动扫光动画提示
        try:
            self._start_sweep()
        except Exception:
            pass
        
        with self.device_lock:
            for i in range(len(self.devices)):
                self.devices[i] = (self.devices[i][0], self.devices[i][1], 
                                  self.devices[i][2], self.devices[i][3], False)
        
        # 使用 QThread + ScanWorker 执行扫描，确保与 Qt 事件循环兼容
        from PyQt5.QtCore import QThread

        ip_prefix = self._get_ip_prefix()

        self._scan_thread = QThread()
        self._scan_worker = ScanWorker(ip_prefix)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.device_found.connect(self._on_device_found)
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        # 清理线程对象
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.start()

    def _scan_network(self):
        """旧版扫描函数 - 已改用 ScanWorker + QThread 实现"""
        # 保留以防需要回退，但不再被调用
        pass

    def _on_device_found(self, ip, hostname):
        """将发现的设备放入待处理队列，由定时器批量处理，降低主线程压力"""
        with self._pending_lock:
            self._pending_devices.append((ip, hostname))

    def _on_scan_finished(self):
        # 清理 worker 和线程引用
        try:
            if hasattr(self, '_scan_worker') and self._scan_worker is not None:
                self._scan_worker.deleteLater()
        except Exception:
            pass
        try:
            if hasattr(self, '_scan_thread') and self._scan_thread is not None:
                try:
                    self._scan_thread.quit()
                    self._scan_thread.wait(500)
                except Exception:
                    pass
                self._scan_thread = None
        except Exception:
            pass
        # 移除不在线设备
        with self.device_lock:
            self.devices = [d for d in self.devices if d[4]]
        self.scanning = False

    def _flush_pending_devices(self):
        """批量将待处理设备合并到主设备列表并刷新 UI"""
        to_process = None
        with self._pending_lock:
            if not self._pending_devices:
                return
            to_process = self._pending_devices
            self._pending_devices = []

        updated = False
        with self.device_lock:
            for ip, hostname in to_process:
                exists = False
                for idx, (old_ip, old_hostname, x, y, online) in enumerate(self.devices):
                    if old_ip == ip:
                        self.devices[idx] = (ip, hostname, x, y, True)
                        exists = True
                        break
                if not exists:
                    # 新设备加入
                    angle = random.uniform(0, 2 * math.pi)
                    r = random.uniform(self.radius * 0.2, self.radius * 0.85)
                    x = self.center.x() + r * math.cos(angle)
                    y = self.center.y() + r * math.sin(angle)
                    self.devices.append([ip, hostname, x, y, True])
                updated = True

        if updated:
            try:
                self.update()
            except Exception:
                pass

    # ==================== 设备列表 ====================
    
    def _show_device_list(self):
        """显示设备列表"""
        if self.device_list_window is None:
            self.device_list_window = _DeviceListWindow(self)
        
        online_devices = []
        with self.device_lock:
            for ip, hostname, x, y, online in self.devices:
                if online:
                    online_devices.append((ip, hostname))
        
        self.device_list_window.update_list(online_devices)
        self._update_list_position()
        self.device_list_window.show()
        self.device_list_window.raise_()

    def _update_list_position(self):
        """更新列表位置"""
        if self.device_list_window:
            radar_pos = self.mapToGlobal(QPoint(0, self.height()))
            list_width = 280
            x = radar_pos.x() + (self.width() - list_width) // 2
            y = radar_pos.y() + 5
            self.device_list_window.move(x, y)


class _DeviceListWindow(QWidget):
    """设备列表窗口（内部使用）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgb(30, 30, 30);
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 0px;
                font-family: Microsoft YaHei;
                font-size: 12px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: rgba(100, 100, 100, 100);
            }
            QListWidget::item:hover {
                background-color: rgba(80, 80, 80, 80);
            }
        """)
        layout.addWidget(self.list_widget)

    def update_list(self, devices):
        """更新列表"""
        self.list_widget.clear()
        if not devices:
            item = QListWidgetItem("未发现设备")
            item.setTextAlignment(Qt.AlignCenter)
            self.list_widget.addItem(item)
            return
        
        for ip, hostname in devices:
            # 在同一行显示 主机名 (IP)
            display_text = f"{hostname} ({ip})"
            item = QListWidgetItem(display_text)
            # 方便复制或查看完整信息，使用 tooltip
            item.setToolTip(display_text)
            self.list_widget.addItem(item)

    def focusOutEvent(self, event):
        self.hide()
        super().focusOutEvent(event)


# ==================== 便捷函数 ====================

def create_radar():
    """
    创建雷达扫描组件
    :return: RadarScanner 实例
    """
    global _app
    if _app is None:
        _app = QApplication(sys.argv)
    return RadarScanner()


def run_radar(radar):
    """
    运行雷达组件（进入事件循环）
    :param radar: RadarScanner 实例
    """
    global _app
    if _app is None:
        _app = QApplication(sys.argv)
    radar.show_window()
    sys.exit(_app.exec_())


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例1：基本使用
    radar = create_radar()
    radar.set_window_size(300, 300)
    radar.set_scan_interval(30)
    radar.show_window()
    
    # 示例2：获取设备信息
    # print(f"设备数量: {radar.get_device_count()}")
    # print(f"设备名称: {radar.get_device_names()}")
    
    sys.exit(_app.exec_())