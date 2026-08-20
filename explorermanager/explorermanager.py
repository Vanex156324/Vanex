import subprocess
import os


def kill_explorer():
    """强制结束 explorer.exe。返回 (success, message)。"""
    try:
        try:
            subprocess.run('taskkill /F /IM explorer.exe', shell=True, check=False)
        except Exception:
            try:
                os.system('taskkill /F /IM explorer.exe')
            except Exception as e:
                return False, f"无法结束 Explorer: {e}"
        return True, 'Explorer 已终止'
    except Exception as e:
        return False, f'错误：{e}'


def reboot_explorer():
    """重启 explorer.exe（先 kill 再启动）。返回 (success, message)。"""
    try:
        # 先尝试结束
        try:
            subprocess.run('taskkill /F /IM explorer.exe', shell=True, check=False)
        except Exception:
            try:
                os.system('taskkill /F /IM explorer.exe')
            except Exception:
                # 如果无法结束也继续尝试启动
                pass

        # 再启动 explorer
        try:
            subprocess.Popen(['explorer.exe'])
        except Exception:
            try:
                os.system('start explorer')
            except Exception as e:
                return False, f'无法启动 Explorer: {e}'

        return True, 'Explorer 已重启'
    except Exception as e:
        return False, f'错误：{e}'


__all__ = ['kill_explorer', 'reboot_explorer']
