import os
import sys
import time
import ctypes
import subprocess
import psutil

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

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
    """重启Windows资源管理器（带自动提权）"""
    try:
        # 我们改为通过临时批处理在独立进程中重启 explorer，避免在当前进程中直接杀进程
        # 这样不会强制结束与当前进程相关的其他线程/资源，且更稳定。
        bat_content = (
            "@echo off\r\n"
            "timeout /t 1 /nobreak >nul\r\n"
            "taskkill /f /im explorer.exe >nul 2>&1\r\n"
            "timeout /t 1 /nobreak >nul\r\n"
            "start \"\" \"C:\\Windows\\explorer.exe\"\r\n"
            "exit /b 0\r\n"
        )

        bat_path = os.path.join(os.environ.get('TEMP', '.'), 'restart_explorer.bat')
        try:
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(bat_content)
        except Exception:
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)

        # 如果当前没有管理员权限，则以管理员权限运行该批处理
        if not is_admin():
            # 使用 ShellExecuteW 以管理员权限运行批处理
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", bat_path, None, None, 0)
                return True, "正在请求管理员权限以重启资源管理器..."
            except Exception as e:
                return False, f"请求提权失败: {e}"

        # 如果已经是管理员，则直接静默启动批处理
        try:
            subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True, "资源管理器重启任务已启动"
        except Exception as e:
            try:
                # 退回到使用ShellExecute直接打开explorer作为最后手段
                explorer_path = r"C:\Windows\explorer.exe"
                ctypes.windll.shell32.ShellExecuteW(None, "open", explorer_path, None, None, 0)
                return True, "资源管理器已尝试重启（备用方法）"
            except Exception as e2:
                return False, f"重启失败: {e}; {e2}"
        
    except Exception as e:
        error_msg = f"重启失败: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg

__all__ = ['kill_explorer', 'reboot_explorer']

# 如果直接运行此脚本，执行重启
if __name__ == "__main__":
    reboot_explorer()