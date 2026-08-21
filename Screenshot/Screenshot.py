# screenshot_tool.py - 可被其他应用调用的截屏库

import os
from datetime import datetime
from pynput import keyboard
import pyscreeze
import pygame
import threading

class ScreenshotTool:
    """截屏工具类，可被外部应用调用"""
    
    def __init__(self, save_dir=None, sound_file="Screenshot.mp3", hotkey=keyboard.Key.print_screen, play_sound=True):
        """
        初始化截屏工具
        
        Args:
            save_dir: 保存目录，默认 ~/Vanex-p
            sound_file: 音效文件路径，默认 Screenshot.mp3
            hotkey: 快捷键，默认 PrintScreen
        """
        self.save_dir = save_dir or os.path.join(os.path.expanduser("~"), "Vanex-p")
        # 如果不播放音效，则不加载音效文件
        self.sound_file = None
        if play_sound:
            self.sound_file = self._find_sound(sound_file)
        self.hotkey = hotkey
        self.enabled = False
        self.listener = None
        self._listener_thread = None
        
        # 初始化音效（仅当需要播放音效时初始化）
        if self.sound_file:
            try:
                pygame.mixer.init()
            except Exception:
                # 忽略音效初始化失败
                self.sound_file = None
        
        # 确保目录存在
        os.makedirs(self.save_dir, exist_ok=True)
    
    def _find_sound(self, sound_file):
        """查找音效文件"""
        if os.path.exists(sound_file):
            return sound_file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, sound_file)
        if os.path.exists(alt_path):
            return alt_path
        return None
    
    def _take_screenshot(self):
        """执行截图"""
        try:
            # 播放音效
            if self.sound_file:
                try:
                    pygame.mixer.Sound(self.sound_file).play()
                except:
                    pass
            
            # 截图保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"截图_{timestamp}.png"
            filepath = os.path.join(self.save_dir, filename)
            
            pyscreeze.screenshot().save(filepath)
            print(f"✅ 截图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return None
    
    def _on_press(self, key):
        """键盘按下事件"""
        if self.enabled and key == self.hotkey:
            self._take_screenshot()
    
    def _on_release(self, key):
        """键盘释放事件"""
        if key == keyboard.Key.esc and self.enabled:
            self.disable()
            return False
        return True
    
    def enable(self):
        """启用截屏功能"""
        if self.enabled:
            print("⚠️  截屏功能已启用")
            return
        
        self.enabled = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print(f"✅ 截屏功能已启用 (快捷键: {self.hotkey})")
        print(f"📁 保存位置: {self.save_dir}")
    
    def disable(self):
        """禁用截屏功能"""
        if not self.enabled:
            print("⚠️  截屏功能已禁用")
            return
        
        self.enabled = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        print("✅ 截屏功能已禁用")
    
    def toggle(self):
        """切换截屏功能开关"""
        if self.enabled:
            self.disable()
        else:
            self.enable()
    
    def is_enabled(self):
        """检查截屏功能是否启用"""
        return self.enabled
    
    def set_hotkey(self, hotkey):
        """设置新的快捷键（需先禁用再启用）"""
        if self.enabled:
            print("⚠️  请先禁用截屏功能再修改快捷键")
            return False
        self.hotkey = hotkey
        print(f"✅ 快捷键已设置为: {hotkey}")
        return True
    
    def set_save_dir(self, save_dir):
        """设置新的保存目录"""
        if self.enabled:
            print("⚠️  请先禁用截屏功能再修改保存目录")
            return False
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        print(f"✅ 保存目录已设置为: {save_dir}")
        return True