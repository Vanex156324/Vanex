**项目描述：**<br>
一个基于 Flask 和 PyQt5 的桌面辅助工具集，通过 Web 界面统一管理多个可视化组件。提供键盘状态悬浮显示、雷达扫描窗口以及系统进程管理功能，适用于桌面美化、快捷操作等场景。

**项目结构：**<br>
项目根目录/<br>
├── keyinfo/<br>
│ └── key_display.py<br>#按键显示
│<br>
├── Radar/<br>
│ └── radar_display.py<br>#雷达显示
│<br>
├── Status_info/<br>
│ └── Status_Display.py<br>#系统信息显示
│<br>
├── web/<br>#前端
│ ├── index.html<br>
│ ├── slider.css<br>
│ ├── style.css<br>
│ └── toggle.css<br>
│<br>
├── windows_info/<br>
│ ├── admin.png<br>
│ ├── system.png<br>
│ ├── user.png<br>
│ └── windowsinfo.py<br>#窗口信息显示
│<br>
├── UI.py#主程序入口<br>
├── README.md#瑞德米<br>
├── requirements.txt#依赖库列表<br>
└── vanex.spec<br>
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
