**项目描述：**<br>
一个基于 Flask 和 PyQt5 的桌面辅助工具集，通过 Web 界面统一管理多个可视化组件。提供键盘状态悬浮显示、雷达扫描窗口以及系统进程管理功能，适用于桌面美化、快捷操作等场景。

**项目结构：**<br>
项目根目录/<br>
├── bluescreen<br>
│ └── bluescreen.py#奔溃触发器<br>
│ <br>
├── clock<br>
│ └── clock.py#时钟显示<br>
│ <br>
├── explorermanager<br>
│ └── explorermanager.py#资源管理器控制器<br>
│ <br>
├── keyinfo<br>
│ ├── key_display.py#按键显示<br>
│ ├── lmb.png<br>
│ └── rmb.png<br>
│<br>
├── music<br>
│ ├── left.png<br>
│ ├── musicinfo.py#音乐信息显示<br>
│ ├── right.py<br>
│ └── stop.png<br>
│<br>
├── Radar<br>
│ └── radar_display.py#雷达显示<br>
│<br>
├── Screenshot<br>
│ ├── Screenshot.mp3<br>
│ └── Screenshot.py#截屏相关<br>
│<br>
├── Status_info<br>
│ └── Status_Display.py#系统信息显示<br>
│<br>
├── traffic<br>
│ ├── down.png<br>
│ ├── traffic_display.py#流量信息显示<br>
│ └── up.png<br>
│<br>
├── UACpypass<br>
│ └── UacBypAsS.py#UAC绕过<br>
│<br>
├── web#前端<br>
│ ├── index.html<br>
│ ├── slider.css<br>
│ ├── style.css<br>
│ └── toggle.css<br>
│<br>
├── windows_info<br>
│ ├── admin.png<br>
│ ├── system.png<br>
│ ├── user.png<br>
│ └── windowsinfo.py#窗口信息显示<br>
│<br>
├── UI.py#主程序入口<br>
├── README.md#瑞德米<br>
├── requirements.txt#依赖库列表<br>
├── appicon.ico#程序图标<br>
└── vanex.spec#打包文件<br>

> **说明**：项目中包含的 `__pycache__` 目录为 Python 自动生成的字节码缓存，已在上述结构图中省略。

<font color="red">确保您已安装 Python 3.x 环境。建议使用虚拟环境来管理依赖。</font>

**在项目根目录下执行以下命令安装所需库：**
```bash
pip install -r requirements.txt
```
**打包项目：**
```bash
pyinstaller vanex.spec
```
**运行项目：**
```bash
python UI.py
```