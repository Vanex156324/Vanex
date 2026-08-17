from flask import Flask, render_template, request, jsonify
import os
import subprocess
import sys
import json
import time
from multiprocessing import Process, Event as MPEvent
from multiprocessing import Queue as MPQueue
# 延迟加载 keyinfo.key_display，避免在子进程导入时触发 PyQt 或 QApplication 创建


app = Flask(__name__)

# 全局 manager 进程与控制变量
_key_process = None
_key_stop_event = None
_radar_process = None
_radar_stop_event = None
_radar_cmd_queue = None


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
    except Exception:
        # 子进程内部不抛出到 Flask，直接退出
        return


def _run_radar_process(stop_event, cmd_queue, width, height, interval):
    """在子进程中运行 RadarScanner 并监听控制命令（保证 QApplication 在子进程主线程中创建）。"""
    try:
        # 延迟导入 PyQt 相关和 RadarScanner，避免在主进程初始化时触发 QApplication
        import os as _os
        import importlib.util as _importlib_util
        from PyQt5.QtWidgets import QApplication

        # 动态加载 radar_display 模块，保证在不同运行环境下也能找到文件
        _this_dir = _os.path.dirname(__file__)
        _radar_path = _os.path.join(_this_dir, 'Radar', 'radar_display.py')
        spec = _importlib_util.spec_from_file_location('radar_display', _radar_path)
        radar_mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(radar_mod)
        RadarScanner = getattr(radar_mod, 'RadarScanner')
        import time as _time
        import queue as _queue

        app = QApplication([])
        radar = RadarScanner()
        radar.set_window_size(width, height)
        radar.set_scan_interval(interval)
        radar.show_window()

        # 使用 QTimer 在 Qt 主循环中定期轮询命令队列和停止事件，避免阻塞主线程
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

            # 如果父进程请求停止，则退出 Qt 事件循环
            try:
                if stop_event.is_set():
                    app.quit()
            except Exception:
                app.quit()

        timer = QTimer()
        timer.timeout.connect(_poll_commands)
        timer.start(100)  # 每100ms检查一次命令队列和停止事件

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
    except Exception:
        # 子进程内部不抛出到 Flask，直接退出
        return

# ===================== 路由 =====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/keyToggle_enable')
def keyToggle_enable():
    global _key_process, _key_stop_event

    if _key_process is not None and _key_process.is_alive():
        return jsonify({'success': False, 'message': 'KeyDisplay 已经在运行'})

    # 使用子进程运行 KeyDisplay，以确保 Qt 的 QApplication 在子进程的主线程中创建
    _key_stop_event = MPEvent()
    _key_process = Process(target=_run_manager_process, args=(_key_stop_event, 500, 300), daemon=True)
    _key_process.start()
    return jsonify({'success': True, 'message': 'KeyDisplay 已启动'})

@app.route('/keyToggle_disable')
def keyToggle_disable():
    global _key_process, _key_stop_event

    if _key_process is None or not _key_process.is_alive():
        return jsonify({'success': False, 'message': 'KeyDisplay 未在运行'})

    try:
        _key_stop_event.set()
        _key_process.join(timeout=2.0)
        if _key_process.is_alive():
            # 强制终止子进程（最后手段）
            _key_process.terminate()
            _key_process.join(timeout=1.0)
    except Exception:
        pass

    _key_process = None
    _key_stop_event = None
    return jsonify({'success': True, 'message': 'KeyDisplay 已停止'})

@app.route('/open_cmd')
def open_cmd():
    os.system('start cmd')
    print("CMD Open Successfully")
    return "CMD 已打开"


@app.route('/radar_enable')
def radar_enable():
    global _radar_process, _radar_stop_event, _radar_cmd_queue

    if _radar_process is not None and _radar_process.is_alive():
        return jsonify({'success': False, 'message': 'Radar 已经在运行'})

    _radar_stop_event = MPEvent()
    _radar_cmd_queue = MPQueue()
    # 默认大小与间隔
    _radar_process = Process(target=_run_radar_process, args=(_radar_stop_event, _radar_cmd_queue, 250, 250, 20), daemon=True)
    _radar_process.start()
    return jsonify({'success': True, 'message': 'Radar 已启动'})


@app.route('/radar_disable')
def radar_disable():
    global _radar_process, _radar_stop_event, _radar_cmd_queue

    if _radar_process is None or not _radar_process.is_alive():
        return jsonify({'success': False, 'message': 'Radar 未在运行'})

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
    return jsonify({'success': True, 'message': 'Radar 已停止'})


@app.route('/radar_set_interval', methods=['POST'])
def radar_set_interval():
    global _radar_process, _radar_cmd_queue
    try:
        data = request.get_json()
        interval = int(data.get('interval', 30))
        if _radar_process is None or not _radar_process.is_alive() or _radar_cmd_queue is None:
            return jsonify({'success': False, 'message': 'Radar 未在运行'})
        # 限制最小值为5
        if interval < 5:
            interval = 5
        _radar_cmd_queue.put(('set_interval', interval))
        return jsonify({'success': True, 'message': f'interval set to {interval}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误：{str(e)}'})


@app.route('/radar_set_size', methods=['POST'])
def radar_set_size():
    global _radar_process, _radar_cmd_queue
    try:
        data = request.get_json()
        width = int(data.get('width', 300))
        height = int(data.get('height', 300))
        if _radar_process is None or not _radar_process.is_alive() or _radar_cmd_queue is None:
            return jsonify({'success': False, 'message': 'Radar 未在运行'})
        # 限制范围
        width = max(150, min(800, width))
        height = max(150, min(800, height))
        _radar_cmd_queue.put(('set_size', width, height))
        return jsonify({'success': True, 'message': f'size set to {width}x{height}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误：{str(e)}'})

@app.route('/kill_process', methods=['POST'])
def kill_process():
    try:
        data = request.get_json()
        input_text = data.get('process_input', '').strip()
        if not input_text:
            return jsonify({'success': False, 'message': '请输入进程ID或名称'})
        if input_text.isdigit():
            return kill_by_pid(int(input_text))
        else:
            return kill_by_name(input_text)
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误：{str(e)}'})

def kill_by_pid(pid):
    try:
        result = subprocess.run(
            f'taskkill /F /PID {pid}',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            return jsonify({'success': True, 'message': f'killed (PID: {pid})'})
        else:
            return jsonify({'success': False, 'message': f'error：{result.stderr.strip()}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'error：{str(e)}'})

def kill_by_name(name):
    try:
        result = subprocess.run(
            f'tasklist /FI "IMAGENAME eq {name}.exe" /FO CSV',
            shell=True, capture_output=True, text=True
        )
        if name.lower() not in result.stdout.lower():
            return jsonify({'success': False, 'message': f'Can not find process：{name}'})
        result = subprocess.run(
            f'taskkill /F /IM {name}.exe',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            return jsonify({'success': True, 'message': f'killed all {name} processes'})
        else:
            return jsonify({'success': False, 'message': f'error：{result.stderr.strip()}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'error：{str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=True)
