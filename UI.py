from waitress import serve
import os
import subprocess
import sys
import json
import time
from multiprocessing import Process, Event as MPEvent
from multiprocessing import Queue as MPQueue

# 延迟加载 keyinfo.key_display，避免在子进程导入时触发 PyQt 或 QApplication 创建

# 全局 manager 进程与控制变量
_key_process = None
_key_stop_event = None
_radar_process = None
_radar_stop_event = None
_radar_cmd_queue = None
_status_process = None
_status_stop_event = None
_status_cmd_queue = None
_windowinfo_process = None
_windowinfo_stop_event = None
_windowinfo_pid = None
_traffic_process = None
_traffic_stop_event = None
_clock_process = None
_clock_stop_event = None
_clock_cmd_queue = None
_music_process = None
_music_stop_event = None
_music_cmd_queue = None
_screenshot_process = None
_screenshot_stop_event = None


def _run_manager_process(stop_event, x, y):
    """在子进程中运行 KeyDisplayManager（保证 QApplication 在子进程主线程中创建）。"""
    try:
        from keyinfo.key_display import KeyDisplayManager
        manager = KeyDisplayManager()
        manager.start(x=x, y=y)
        try:
            while not stop_event.is_set():
                manager.process_events()
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            try:
                manager.stop()
            except Exception:
                pass
    except Exception as e:
        print(f"KeyDisplay 子进程错误: {e}")
        return


def _run_windowinfo_process(stop_event, x, y, interval):
    """在子进程中运行 WindowInfoManager 并监听停止事件。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer

        # 优先尝试常规包导入（方便 PyInstaller 静态分析识别），失败则回退到按文件路径加载
        try:
            from windows_info.windowsinfo import WindowInfoManager
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _wi_path = _os.path.join(_this_dir, 'windows_info', 'windowsinfo.py')
            spec = _importlib_util.spec_from_file_location('windowsinfo', _wi_path)
            wi_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(wi_mod)
            WindowInfoManager = getattr(wi_mod, 'WindowInfoManager')

        app = QApplication([])
        manager = WindowInfoManager()
        manager.start(x=x, y=y, update_interval=interval)

        def _poll_stop():
            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_stop)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                manager.stop()
            except Exception:
                pass
    except Exception as e:
        print(f"WindowInfo 子进程错误: {e}")
        return


def _run_status_process(stop_event, cmd_queue, corner, margin):
    """在子进程中运行 SystemMonitor 并监听控制命令（保证 QApplication 在子进程主线程中创建）。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication
        import queue as _queue

        # 优先常规导入，回退到文件路径加载以兼容打包情况
        try:
            from Status_info.Status_Display import SystemMonitor
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _status_path = _os.path.join(_this_dir, 'Status_info', 'Status_Display.py')
            spec = _importlib_util.spec_from_file_location('Status_Display', _status_path)
            status_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(status_mod)
            SystemMonitor = getattr(status_mod, 'SystemMonitor')

        app = QApplication([])
        monitor = SystemMonitor(corner=corner, margin=margin, auto_start=True)

        from PyQt5.QtCore import QTimer

        def _poll_commands():
            try:
                while True:
                    cmd = cmd_queue.get_nowait()
                    if not cmd:
                        continue
                    action = cmd[0]
                    if action == 'set_corner' and len(cmd) > 1:
                        try:
                            monitor.set_corner(cmd[1])
                        except Exception:
                            pass
                    elif action == 'set_margin' and len(cmd) > 1:
                        try:
                            monitor.set_margin(int(cmd[1]))
                        except Exception:
                            pass
            except _queue.Empty:
                pass

            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_commands)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                monitor.stop()
            except Exception:
                pass
    except Exception as e:
        print(f"Status Monitor 子进程错误: {e}")
        return


def _run_radar_process(stop_event, cmd_queue, width, height, interval):
    """在子进程中运行 RadarScanner 并监听控制命令（保证 QApplication 在子进程主线程中创建）。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication

        # 优先常规导入模块，便于 PyInstaller 检测；失败则按文件路径加载
        try:
            from Radar.radar_display import RadarScanner
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _radar_path = _os.path.join(_this_dir, 'Radar', 'radar_display.py')
            spec = _importlib_util.spec_from_file_location('radar_display', _radar_path)
            radar_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(radar_mod)
            RadarScanner = getattr(radar_mod, 'RadarScanner')
        import queue as _queue

        app = QApplication([])
        radar = RadarScanner()
        radar.set_window_size(width, height)
        radar.set_scan_interval(interval)
        radar.show_window()

        from PyQt5.QtCore import QTimer

        def _poll_commands():
            try:
                while True:
                    cmd = cmd_queue.get_nowait()
                    if not cmd:
                        continue
                    action = cmd[0]
                    if action == 'set_interval' and len(cmd) > 1:
                        try:
                            radar.set_scan_interval(int(cmd[1]))
                        except Exception:
                            pass
                    elif action == 'set_size' and len(cmd) > 2:
                        try:
                            radar.set_window_size(int(cmd[1]), int(cmd[2]))
                        except Exception:
                            pass
            except _queue.Empty:
                pass

            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_commands)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                radar.close_window()
            except Exception:
                pass
    except Exception as e:
        print(f"Radar 子进程错误: {e}")
        return


def _run_traffic_process(stop_event):
    """在子进程中运行 TrafficWidget 并监听停止事件。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication

        # 尝试常规导入，回退到文件路径加载以兼容打包情况
        try:
            from traffic.traffic_display import TrafficWidget
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _traffic_path = _os.path.join(_this_dir, 'traffic', 'traffic_display.py')
            spec = _importlib_util.spec_from_file_location('traffic_display', _traffic_path)
            traffic_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(traffic_mod)
            TrafficWidget = getattr(traffic_mod, 'TrafficWidget')

        app = QApplication([])
        widget = TrafficWidget()
        widget.show()

        from PyQt5.QtCore import QTimer

        def _poll_stop():
            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_stop)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                widget.close()
            except Exception:
                pass
    except Exception as e:
        print(f"Traffic 子进程错误: {e}")
        return


def _run_clock_process(stop_event, cmd_queue, size, mode):
    """在子进程中运行 TransparentClock 并监听控制命令。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication

        try:
            from clock.clock import TransparentClock
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _clock_path = _os.path.join(_this_dir, 'clock', 'clock.py')
            spec = _importlib_util.spec_from_file_location('clock', _clock_path)
            clock_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(clock_mod)
            TransparentClock = getattr(clock_mod, 'TransparentClock')

        app = QApplication([])

        # 创建时钟实例
        try:
            widget = TransparentClock(mode=mode, size=int(size))
        except Exception:
            widget = TransparentClock(mode=mode)

        # 默认显示
        try:
            widget.show_clock()
        except Exception:
            widget.show()

        from PyQt5.QtCore import QTimer

        def _poll_commands():
            import queue as _queue
            try:
                while True:
                    cmd = cmd_queue.get_nowait()
                    if not cmd:
                        continue
                    action = cmd[0]
                    if action == 'set_size' and len(cmd) > 1:
                        try:
                            new_size = int(cmd[1])
                            if getattr(widget, 'mode', 'analog') == 'analog':
                                widget.setFixedSize(new_size, new_size)
                            else:
                                # digital: interpret size as font size
                                try:
                                    widget.set_font_size(new_size)
                                except Exception:
                                    # fallback: adjust width
                                    h = getattr(widget, 'digital_height', 80)
                                    widget.setFixedSize(new_size, h)
                            try:
                                widget.update()
                            except Exception:
                                pass
                        except Exception:
                            pass
                    elif action == 'set_mode' and len(cmd) > 1:
                        try:
                            widget.set_mode(cmd[1])
                            # 调整大小以适配新模式
                            try:
                                if cmd[1] == 'analog':
                                    s = getattr(widget, 'width', widget.width())
                                    widget.setFixedSize(s, s)
                                else:
                                    w = widget.width()
                                    h = getattr(widget, 'digital_height', 80)
                                    widget.setFixedSize(w, h)
                            except Exception:
                                pass
                        except Exception:
                            pass
            except _queue.Empty:
                pass

            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_commands)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                widget.close()
            except Exception:
                pass
    except Exception as e:
        print(f"Clock 子进程错误: {e}")
        return


def _run_music_process(stop_event, cmd_queue, width):
    """在子进程中运行 CloudMusicTracker 并监听控制命令（宽度通过命令设置）。"""
    try:
        import os as _os
        import sys as _sys
        from PyQt5.QtWidgets import QApplication

        try:
            from music.musicinfo import CloudMusicTracker
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _music_path = _os.path.join(_this_dir, 'music', 'musicinfo.py')
            spec = _importlib_util.spec_from_file_location('musicinfo', _music_path)
            music_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(music_mod)
            CloudMusicTracker = getattr(music_mod, 'CloudMusicTracker')

        app = QApplication([])
        tracker = CloudMusicTracker()
        try:
            tracker.show()
        except Exception:
            try:
                tracker.show()
            except Exception:
                pass

        from PyQt5.QtCore import QTimer

        def _poll_commands():
            import queue as _queue
            try:
                while True:
                    cmd = cmd_queue.get_nowait()
                    if not cmd:
                        continue
                    action = cmd[0]
                    if action == 'set_size' and len(cmd) > 1:
                        try:
                            new_w = int(cmd[1])
                            ratio = 195 / 400.0
                            new_h = max(50, int(new_w * ratio))
                            try:
                                tracker.setFixedSize(new_w, new_h)
                            except Exception:
                                try:
                                    tracker.resize(new_w, new_h)
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except _queue.Empty:
                pass

            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_commands)
        timer.start(100)

        try:
            app.exec_()
        finally:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                tracker.close()
            except Exception:
                pass
    except Exception as e:
        print(f"Music 子进程错误: {e}")
        return


def _run_screenshot_process(stop_event):
    """在子进程中运行 ScreenshotTool 并监听停止事件。"""
    try:
        import os as _os
        import sys as _sys
        import time as _time

        try:
            from Screenshot.Screenshot import ScreenshotTool
        except Exception:
            import importlib.util as _importlib_util
            if getattr(_sys, 'frozen', False):
                _this_dir = _sys._MEIPASS
            else:
                _this_dir = _os.path.dirname(__file__)
            _ss_path = _os.path.join(_this_dir, 'Screenshot', 'Screenshot.py')
            spec = _importlib_util.spec_from_file_location('screenshot', _ss_path)
            ss_mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(ss_mod)
            ScreenshotTool = getattr(ss_mod, 'ScreenshotTool')

        tool = ScreenshotTool()
        try:
            tool.enable()
        except Exception:
            try:
                tool.enable()
            except Exception as e:
                print(f"Screenshot enable failed: {e}")

        try:
            while not stop_event.is_set():
                _time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            try:
                tool.disable()
            except Exception:
                pass
    except Exception as e:
        print(f"Screenshot 子进程错误: {e}")
        return


def parse_query_string(query_string):
    """解析查询字符串，返回 dict"""
    params = {}
    if query_string:
        for pair in query_string.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
            else:
                params[pair] = ''
    return params


def parse_json_body(environ):
    """从 WSGI environ 中解析 JSON 请求体"""
    try:
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length > 0:
            body = environ['wsgi.input'].read(content_length).decode('utf-8')
            return json.loads(body)
    except Exception:
        pass
    return {}


def json_response(data, status='200 OK'):
    """生成 JSON 响应"""
    body = json.dumps(data, ensure_ascii=False)
    return [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Content-Length', str(len(body.encode('utf-8'))))
    ], body.encode('utf-8')


def html_response(body, status='200 OK'):
    """生成 HTML 响应"""
    return [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body.encode('utf-8'))))
    ], body.encode('utf-8')


def plain_response(body, status='200 OK'):
    """生成纯文本响应"""
    return [
        ('Content-Type', 'text/plain; charset=utf-8'),
        ('Content-Length', str(len(body.encode('utf-8'))))
    ], body.encode('utf-8')


def serve_static_file(file_path):
    """服务静态文件，自动检测 MIME 类型"""
    try:
        # 获取文件扩展名
        ext = os.path.splitext(file_path)[1].lower()
        
        # MIME 类型映射
        mime_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.txt': 'text/plain; charset=utf-8',
            '.xml': 'text/xml; charset=utf-8',
            '.pdf': 'application/pdf',
            '.zip': 'application/zip',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }
        
        content_type = mime_types.get(ext, 'application/octet-stream')
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return [
            ('Content-Type', content_type),
            ('Content-Length', str(len(content)))
        ], content
    except FileNotFoundError:
        return None, None
    except Exception as e:
        print(f"读取静态文件错误: {e}")
        return None, None


def render_template_file(template_name):
    """读取模板文件内容（从 web 文件夹）"""
    # 获取当前文件所在目录
    base_dir = os.path.dirname(__file__)
    # web 文件夹路径
    web_dir = os.path.join(base_dir, 'web')
    template_path = os.path.join(web_dir, template_name)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f'<h1>Template {template_name} not found</h1><p>请检查 web 文件夹中是否存在该文件</p>'


# ===================== WSGI 应用 =====================

def application(environ, start_response):
    """纯 WSGI 应用，替代 Flask"""
    
    # 声明全局变量（必须在函数开头）
    global _key_process, _key_stop_event
    global _radar_process, _radar_stop_event, _radar_cmd_queue
    global _status_process, _status_stop_event, _status_cmd_queue
    global _windowinfo_process, _windowinfo_stop_event, _windowinfo_pid
    global _traffic_process, _traffic_stop_event
    global _clock_process, _clock_stop_event, _clock_cmd_queue
    global _music_process, _music_stop_event, _music_cmd_queue
    global _screenshot_process, _screenshot_stop_event
    
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    query_string = environ.get('QUERY_STRING', '')
    
    # 打印请求日志（用于调试）
    print(f"[{time.strftime('%H:%M:%S')}] {method} {path}")
    
    params = parse_query_string(query_string)
    
    # 对于 POST 请求，解析 JSON body
    post_data = {}
    if method == 'POST':
        post_data = parse_json_body(environ)
    
    # ==================== 静态文件服务 ====================
    # 如果请求的是 web 文件夹中的静态文件
    if path.startswith('/web/'):
        # 移除 /web/ 前缀
        static_path = path[5:]  # 去掉 '/web/'
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, 'web', static_path)
        
        # 安全检查：防止路径遍历攻击
        real_path = os.path.realpath(file_path)
        web_real_path = os.path.realpath(os.path.join(base_dir, 'web'))
        if not real_path.startswith(web_real_path):
            headers, body = html_response('<h1>403 Forbidden</h1>', '403 Forbidden')
            start_response('403 Forbidden', headers)
            return [body]
        
        # 服务文件
        headers, content = serve_static_file(real_path)
        if headers is not None:
            start_response('200 OK', headers)
            return [content]
        else:
            headers, body = html_response('<h1>404 Not Found</h1>', '404 Not Found')
            start_response('404 Not Found', headers)
            return [body]
    
    # ==================== API 路由 ====================
    
    # 测试路由 - 用于检查服务器是否正常运行
    if path == '/test' and method == 'GET':
        headers, body = plain_response("Server is working! 服务器正常运行！\n时间: " + time.strftime('%Y-%m-%d %H:%M:%S'))
        start_response('200 OK', headers)
        return [body]

    # Screenshot 启用
    elif path == '/screenshot_enable' and method == 'GET':
        if _screenshot_process is not None and _screenshot_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Screenshot 已经在运行'})
            start_response('200 OK', headers)
            return [body]

        _screenshot_stop_event = MPEvent()
        _screenshot_process = Process(target=_run_screenshot_process, args=(_screenshot_stop_event,), daemon=True)
        _screenshot_process.start()
        headers, body = json_response({'success': True, 'message': 'Screenshot 已启动'})
        start_response('200 OK', headers)
        return [body]

    # Screenshot 禁用
    elif path == '/screenshot_disable' and method == 'GET':
        if _screenshot_process is None or not _screenshot_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Screenshot 未在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            _screenshot_stop_event.set()
            _screenshot_process.join(timeout=2.0)
            if _screenshot_process.is_alive():
                _screenshot_process.terminate()
                _screenshot_process.join(timeout=1.0)
        except Exception:
            pass

        _screenshot_process = None
        _screenshot_stop_event = None
        headers, body = json_response({'success': True, 'message': 'Screenshot 已停止'})
        start_response('200 OK', headers)
        return [body]

    # Screenshot 状态
    elif path == '/screenshot_status' and method == 'GET':
        running = False
        try:
            if _screenshot_process is not None and _screenshot_process.is_alive():
                running = True
        except Exception:
            pass
        headers, body = json_response({'running': running})
        start_response('200 OK', headers)
        return [body]

    # Music 启用
    elif path == '/music_enable' and method == 'POST':
        if _music_process is not None and _music_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Music 已经在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            width = int(post_data.get('width', 400))
        except Exception:
            width = 400

        _music_stop_event = MPEvent()
        _music_cmd_queue = MPQueue()
        _music_process = Process(target=_run_music_process, args=(_music_stop_event, _music_cmd_queue, width), daemon=True)
        _music_process.start()
        headers, body = json_response({'success': True, 'message': 'Music 已启动'})
        start_response('200 OK', headers)
        return [body]

    # Music 禁用
    elif path == '/music_disable' and method == 'GET':
        if _music_process is None or not _music_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Music 未在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            _music_stop_event.set()
            _music_process.join(timeout=2.0)
            if _music_process.is_alive():
                _music_process.terminate()
                _music_process.join(timeout=1.0)
        except Exception:
            pass

        _music_process = None
        _music_stop_event = None
        _music_cmd_queue = None
        headers, body = json_response({'success': True, 'message': 'Music 已停止'})
        start_response('200 OK', headers)
        return [body]

    # Music 设置大小
    elif path == '/music_set_size' and method == 'POST':
        try:
            width = int(post_data.get('width', 400))
            if _music_process is None or not _music_process.is_alive() or _music_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Music 未在运行'})
                start_response('200 OK', headers)
                return [body]
            width = max(100, min(1200, width))
            _music_cmd_queue.put(('set_size', width))
            headers, body = json_response({'success': True, 'message': f'width set to {width}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]

    # Music 状态
    elif path == '/music_status' and method == 'GET':
        running = False
        try:
            if _music_process is not None and _music_process.is_alive():
                running = True
        except Exception:
            pass
        headers, body = json_response({'running': running})
        start_response('200 OK', headers)
        return [body]

    if path =='/triggerBlueScreen' and method == 'GET':
        from bluescreen.bluescreen import trigger_blue_screen
        trigger_blue_screen()

    
    # 健康检查
    if path == '/health' and method == 'GET':
        headers, body = json_response({
            'status': 'ok',
            'message': 'Server is running',
            'timestamp': time.time()
        })
        start_response('200 OK', headers)
        return [body]
    
    # 首页 - 从 web 文件夹读取 index.html
    if path == '/' and method == 'GET':
        headers, body = html_response(render_template_file('index.html'))
        start_response('200 OK', headers)
        return [body]
    
    # KeyDisplay 启用
    elif path == '/keyToggle_enable' and method == 'GET':
        if _key_process is not None and _key_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'KeyDisplay 已经在运行'})
            start_response('200 OK', headers)
            return [body]
        
        _key_stop_event = MPEvent()
        _key_process = Process(target=_run_manager_process, args=(_key_stop_event, 500, 300), daemon=True)
        _key_process.start()
        headers, body = json_response({'success': True, 'message': 'KeyDisplay 已启动'})
        start_response('200 OK', headers)
        return [body]
    
    # KeyDisplay 禁用
    elif path == '/keyToggle_disable' and method == 'GET':
        if _key_process is None or not _key_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'KeyDisplay 未在运行'})
            start_response('200 OK', headers)
            return [body]
        
        try:
            _key_stop_event.set()
            _key_process.join(timeout=2.0)
            if _key_process.is_alive():
                _key_process.terminate()
                _key_process.join(timeout=1.0)
        except Exception:
            pass
        
        _key_process = None
        _key_stop_event = None
        headers, body = json_response({'success': True, 'message': 'KeyDisplay 已停止'})
        start_response('200 OK', headers)
        return [body]
    
    # WindowInfo 启用
    elif path == '/windowinfo_enable' and method == 'GET':
        if _windowinfo_process is not None and _windowinfo_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'WindowInfo 已经在运行'})
            start_response('200 OK', headers)
            return [body]
        
        _windowinfo_stop_event = MPEvent()
        _windowinfo_process = Process(target=_run_windowinfo_process, args=(_windowinfo_stop_event, 50, 50, 500), daemon=True)
        _windowinfo_process.start()
        try:
            _windowinfo_pid = _windowinfo_process.pid
        except Exception:
            _windowinfo_pid = None
        headers, body = json_response({'success': True, 'message': 'WindowInfo 已启动'})
        start_response('200 OK', headers)
        return [body]
    
    # WindowInfo 禁用
    elif path == '/windowinfo_disable' and method == 'GET':
        if _windowinfo_process is None or not _windowinfo_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'WindowInfo 未在运行'})
            start_response('200 OK', headers)
            return [body]
        
        try:
            _windowinfo_stop_event.set()
            _windowinfo_process.join(timeout=2.0)
            if _windowinfo_process.is_alive():
                _windowinfo_process.terminate()
                _windowinfo_process.join(timeout=1.0)
        except Exception:
            pass
        
        try:
            if _windowinfo_process is not None and _windowinfo_process.is_alive():
                pid = getattr(_windowinfo_process, 'pid', None)
                if pid:
                    try:
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=False)
                    except Exception:
                        pass
        except Exception:
            pass
        
        _windowinfo_process = None
        _windowinfo_stop_event = None
        _windowinfo_pid = None
        headers, body = json_response({'success': True, 'message': 'WindowInfo 已停止'})
        start_response('200 OK', headers)
        return [body]
    
    # WindowInfo 状态
    elif path == '/windowinfo_status' and method == 'GET':
        running = False
        pid = None
        try:
            if _windowinfo_process is not None and _windowinfo_process.is_alive():
                running = True
                pid = _windowinfo_process.pid
            elif _windowinfo_pid:
                running = True
                pid = _windowinfo_pid
        except Exception:
            pass
        headers, body = json_response({'running': running, 'pid': pid})
        start_response('200 OK', headers)
        return [body]
    
    # 打开 CMD
    elif path == '/open_cmd' and method == 'GET':
        os.system('start cmd')
        print("CMD Open Successfully")
        headers, body = plain_response("CMD 已打开")
        start_response('200 OK', headers)
        return [body]

    # Kill Explorer
    elif path == '/killexplorer' and method == 'GET':
        try:
            # 延迟导入 explorermanager，避免启动时额外依赖
            try:
                from explorermanager.explorermanager import kill_explorer
            except Exception:
                # 回退到相对导入路径
                import importlib.util as _importlib_util
                _this_dir = os.path.dirname(__file__)
                _em_path = os.path.join(_this_dir, 'explorermanager', 'explorermanager.py')
                spec = _importlib_util.spec_from_file_location('explorermanager', _em_path)
                em_mod = _importlib_util.module_from_spec(spec)
                spec.loader.exec_module(em_mod)
                kill_explorer = getattr(em_mod, 'kill_explorer')

            success, msg = kill_explorer()
            status_msg = msg if isinstance(msg, str) else str(msg)
            headers, body = plain_response(status_msg)
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = plain_response(f'错误：{e}')
            start_response('200 OK', headers)
            return [body]

    # Reboot Explorer (kill then start)
    elif path == '/rebootexplorer' and method == 'GET':
        try:
            try:
                from explorermanager.explorermanager import reboot_explorer
            except Exception:
                import importlib.util as _importlib_util
                _this_dir = os.path.dirname(__file__)
                _em_path = os.path.join(_this_dir, 'explorermanager', 'explorermanager.py')
                spec = _importlib_util.spec_from_file_location('explorermanager', _em_path)
                em_mod = _importlib_util.module_from_spec(spec)
                spec.loader.exec_module(em_mod)
                reboot_explorer = getattr(em_mod, 'reboot_explorer')

            success, msg = reboot_explorer()
            status_msg = msg if isinstance(msg, str) else str(msg)
            headers, body = plain_response(status_msg)
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = plain_response(f'错误：{e}')
            start_response('200 OK', headers)
            return [body]
    
    # Radar 启用
    elif path == '/radar_enable' and method == 'GET':
        if _radar_process is not None and _radar_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Radar 已经在运行'})
            start_response('200 OK', headers)
            return [body]
        
        _radar_stop_event = MPEvent()
        _radar_cmd_queue = MPQueue()
        _radar_process = Process(target=_run_radar_process, args=(_radar_stop_event, _radar_cmd_queue, 250, 250, 20), daemon=True)
        _radar_process.start()
        headers, body = json_response({'success': True, 'message': 'Radar 已启动'})
        start_response('200 OK', headers)
        return [body]
    
    # Radar 禁用
    elif path == '/radar_disable' and method == 'GET':
        if _radar_process is None or not _radar_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Radar 未在运行'})
            start_response('200 OK', headers)
            return [body]
        
        try:
            _radar_stop_event.set()
            _radar_process.join(timeout=2.0)
            if _radar_process.is_alive():
                _radar_process.terminate()
                _radar_process.join(timeout=1.0)
        except Exception:
            pass
        
        _radar_process = None
        _radar_stop_event = None
        _radar_cmd_queue = None
        headers, body = json_response({'success': True, 'message': 'Radar 已停止'})
        start_response('200 OK', headers)
        return [body]
    
    # Radar 设置间隔
    elif path == '/radar_set_interval' and method == 'POST':
        try:
            interval = int(post_data.get('interval', 30))
            if _radar_process is None or not _radar_process.is_alive() or _radar_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Radar 未在运行'})
                start_response('200 OK', headers)
                return [body]
            if interval < 5:
                interval = 5
            _radar_cmd_queue.put(('set_interval', interval))
            headers, body = json_response({'success': True, 'message': f'interval set to {interval}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]
    
    # Radar 设置大小
    elif path == '/radar_set_size' and method == 'POST':
        try:
            width = int(post_data.get('width', 300))
            height = int(post_data.get('height', 300))
            if _radar_process is None or not _radar_process.is_alive() or _radar_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Radar 未在运行'})
                start_response('200 OK', headers)
                return [body]
            width = max(150, min(800, width))
            height = max(150, min(800, height))
            _radar_cmd_queue.put(('set_size', width, height))
            headers, body = json_response({'success': True, 'message': f'size set to {width}x{height}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]

    # Traffic 启用
    elif path == '/traffic_enable' and method == 'GET':
        if _traffic_process is not None and _traffic_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Traffic 已经在运行'})
            start_response('200 OK', headers)
            return [body]

        _traffic_stop_event = MPEvent()
        _traffic_process = Process(target=_run_traffic_process, args=(_traffic_stop_event,), daemon=True)
        _traffic_process.start()
        headers, body = json_response({'success': True, 'message': 'Traffic 已启动'})
        start_response('200 OK', headers)
        return [body]

    # Traffic 禁用
    elif path == '/traffic_disable' and method == 'GET':
        if _traffic_process is None or not _traffic_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Traffic 未在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            _traffic_stop_event.set()
            _traffic_process.join(timeout=2.0)
            if _traffic_process.is_alive():
                _traffic_process.terminate()
                _traffic_process.join(timeout=1.0)
        except Exception:
            pass

        _traffic_process = None
        _traffic_stop_event = None
        headers, body = json_response({'success': True, 'message': 'Traffic 已停止'})
        start_response('200 OK', headers)
        return [body]

    # Traffic 状态
    elif path == '/traffic_status' and method == 'GET':
        running = False
        try:
            if _traffic_process is not None and _traffic_process.is_alive():
                running = True
        except Exception:
            pass
        headers, body = json_response({'running': running})
        start_response('200 OK', headers)
        return [body]

    # Clock 启用
    elif path == '/clock_enable' and method == 'POST':
        if _clock_process is not None and _clock_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Clock 已经在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            size = int(post_data.get('size', 200))
        except Exception:
            size = 200
        mode = post_data.get('mode', 'analog')

        _clock_stop_event = MPEvent()
        _clock_cmd_queue = MPQueue()
        _clock_process = Process(target=_run_clock_process, args=(_clock_stop_event, _clock_cmd_queue, size, mode), daemon=True)
        _clock_process.start()
        headers, body = json_response({'success': True, 'message': 'Clock 已启动'})
        start_response('200 OK', headers)
        return [body]

    # Clock 禁用
    elif path == '/clock_disable' and method == 'GET':
        if _clock_process is None or not _clock_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Clock 未在运行'})
            start_response('200 OK', headers)
            return [body]

        try:
            _clock_stop_event.set()
            _clock_process.join(timeout=2.0)
            if _clock_process.is_alive():
                _clock_process.terminate()
                _clock_process.join(timeout=1.0)
        except Exception:
            pass

        _clock_process = None
        _clock_stop_event = None
        _clock_cmd_queue = None
        headers, body = json_response({'success': True, 'message': 'Clock 已停止'})
        start_response('200 OK', headers)
        return [body]

    # Clock 设置大小
    elif path == '/clock_set_size' and method == 'POST':
        try:
            size = int(post_data.get('size', 200))
            if _clock_process is None or not _clock_process.is_alive() or _clock_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Clock 未在运行'})
                start_response('200 OK', headers)
                return [body]
            size = max(50, min(1000, size))
            _clock_cmd_queue.put(('set_size', size))
            headers, body = json_response({'success': True, 'message': f'size set to {size}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]

    # Clock 设置模式
    elif path == '/clock_set_mode' and method == 'POST':
        try:
            mode = post_data.get('mode', 'analog')
            if _clock_process is None or not _clock_process.is_alive() or _clock_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Clock 未在运行'})
                start_response('200 OK', headers)
                return [body]
            if mode not in ('analog', 'digital'):
                headers, body = json_response({'success': False, 'message': 'invalid mode'})
                start_response('200 OK', headers)
                return [body]
            _clock_cmd_queue.put(('set_mode', mode))
            headers, body = json_response({'success': True, 'message': f'mode set to {mode}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]

    # Clock 状态
    elif path == '/clock_status' and method == 'GET':
        running = False
        try:
            if _clock_process is not None and _clock_process.is_alive():
                running = True
        except Exception:
            pass
        headers, body = json_response({'running': running})
        start_response('200 OK', headers)
        return [body]
    
    # Status Monitor 启用
    elif path == '/status_enable' and method == 'POST':
        if _status_process is not None and _status_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Status Monitor 已经在运行'})
            start_response('200 OK', headers)
            return [body]
        
        try:
            corner = post_data.get('corner', 'top_right')
            margin = int(post_data.get('margin', 10))
        except Exception:
            corner = 'top_right'
            margin = 10
        
        _status_stop_event = MPEvent()
        _status_cmd_queue = MPQueue()
        _status_process = Process(target=_run_status_process, args=(_status_stop_event, _status_cmd_queue, corner, margin), daemon=True)
        _status_process.start()
        headers, body = json_response({'success': True, 'message': 'Status Monitor 已启动'})
        start_response('200 OK', headers)
        return [body]
    
    # Status Monitor 禁用
    elif path == '/status_disable' and method == 'GET':
        if _status_process is None or not _status_process.is_alive():
            headers, body = json_response({'success': False, 'message': 'Status Monitor 未在运行'})
            start_response('200 OK', headers)
            return [body]
        
        try:
            _status_stop_event.set()
            _status_process.join(timeout=2.0)
            if _status_process.is_alive():
                _status_process.terminate()
                _status_process.join(timeout=1.0)
        except Exception:
            pass
        
        _status_process = None
        _status_stop_event = None
        _status_cmd_queue = None
        headers, body = json_response({'success': True, 'message': 'Status Monitor 已停止'})
        start_response('200 OK', headers)
        return [body]
    
    # Status Monitor 设置角标位置
    elif path == '/status_set_corner' and method == 'POST':
        try:
            corner = post_data.get('corner')
            if not corner:
                headers, body = json_response({'success': False, 'message': 'missing corner'})
                start_response('200 OK', headers)
                return [body]
            if _status_process is None or not _status_process.is_alive() or _status_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Status Monitor 未在运行'})
                start_response('200 OK', headers)
                return [body]
            _status_cmd_queue.put(('set_corner', corner))
            headers, body = json_response({'success': True, 'message': f'corner set to {corner}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]
    
    # Status Monitor 设置边距
    elif path == '/status_set_margin' and method == 'POST':
        try:
            margin = int(post_data.get('margin', 10))
            if _status_process is None or not _status_process.is_alive() or _status_cmd_queue is None:
                headers, body = json_response({'success': False, 'message': 'Status Monitor 未在运行'})
                start_response('200 OK', headers)
                return [body]
            _status_cmd_queue.put(('set_margin', margin))
            headers, body = json_response({'success': True, 'message': f'margin set to {margin}'})
            start_response('200 OK', headers)
            return [body]
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]
    
    # 杀进程
    elif path == '/kill_process' and method == 'POST':
        try:
            input_text = post_data.get('process_input', '').strip()
            if not input_text:
                headers, body = json_response({'success': False, 'message': '请输入进程ID或名称'})
                start_response('200 OK', headers)
                return [body]
            if input_text.isdigit():
                return kill_by_pid(int(input_text), start_response)
            else:
                return kill_by_name(input_text, start_response)
        except Exception as e:
            headers, body = json_response({'success': False, 'message': f'错误：{str(e)}'})
            start_response('200 OK', headers)
            return [body]
    
    # 404
    else:
        print(f"404 Not Found: {path}")
        headers, body = html_response(
            f'<h1>404 Not Found</h1>'
            f'<p>Path: {path}</p>'
            f'<p>尝试访问: <a href="/">首页</a> | <a href="/test">测试</a> | <a href="/health">健康检查</a></p>'
            f'<p>静态文件示例: <a href="/web/style.css">/web/style.css</a></p>',
            '404 Not Found'
        )
        start_response('404 Not Found', headers)
        return [body]


def kill_by_pid(pid, start_response):
    try:
        result = subprocess.run(
            f'taskkill /F /PID {pid}',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            headers, body = json_response({'success': True, 'message': f'killed (PID: {pid})'})
        else:
            headers, body = json_response({'success': False, 'message': f'error：{result.stderr.strip()}'})
        start_response('200 OK', headers)
        return [body]
    except Exception as e:
        headers, body = json_response({'success': False, 'message': f'error：{str(e)}'})
        start_response('200 OK', headers)
        return [body]


def kill_by_name(name, start_response):
    try:
        result = subprocess.run(
            f'tasklist /FI "IMAGENAME eq {name}.exe" /FO CSV',
            shell=True, capture_output=True, text=True
        )
        if name.lower() not in result.stdout.lower():
            headers, body = json_response({'success': False, 'message': f'Can not find process：{name}'})
            start_response('200 OK', headers)
            return [body]
        result = subprocess.run(
            f'taskkill /F /IM {name}.exe',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            headers, body = json_response({'success': True, 'message': f'killed all {name} processes'})
        else:
            headers, body = json_response({'success': False, 'message': f'error：{result.stderr.strip()}'})
        start_response('200 OK', headers)
        return [body]
    except Exception as e:
        headers, body = json_response({'success': False, 'message': f'error：{str(e)}'})
        start_response('200 OK', headers)
        return [body]


if __name__ == '__main__':
    # 使用 Waitress 作为 WSGI 服务器
    # 在冻结（pyinstaller）环境中确保子进程能正确启动
    from multiprocessing import freeze_support
    freeze_support()

    host = '127.0.0.1'
    port = 1203
    
    print("=" * 60)
    print("Waitress WSGI 服务器启动中...")
    print("=" * 60)
    print(f"服务器地址: http://{host}:{port}")
    print(f"首页地址: http://{host}:{port}/")
    print(f"测试地址: http://{host}:{port}/test")
    print(f"健康检查: http://{host}:{port}/health")
    print(f"静态文件: http://{host}:{port}/web/")
    print("=" * 60)
    
    # 检查 web 文件夹是否存在（支持 PyInstaller 单文件运行）
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(__file__)
    web_dir = os.path.join(base_dir, 'web')
    if os.path.exists(web_dir):
        print(f"✓ web 文件夹已找到: {web_dir}")
        # 列出 web 文件夹中的文件
        files = os.listdir(web_dir)
        if files:
            print(f"✓ 发现文件: {', '.join(files[:5])}")
            if len(files) > 5:
                print(f"  以及 {len(files) - 5} 个其他文件")
        else:
            print("⚠ web 文件夹为空")
    else:
        print(f"✗ web 文件夹不存在: {web_dir}")
        print("请创建 web 文件夹并放入您的 HTML/CSS/JS 文件")
    
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        serve(application, host=host, port=port, threads=4)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")