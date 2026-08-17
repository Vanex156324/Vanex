项目描述：
一个基于 Flask 和 PyQt5 的桌面辅助工具集，通过 Web 界面统一管理多个可视化组件。提供键盘状态悬浮显示、雷达扫描窗口以及系统进程管理功能，适用于桌面美化、快捷操作等场景。

项目结构：
Vanex_recode/<br>
├── UI_code/                                          # UI相关代码存放文件夹<br>
│   ├── keyinfo                                      # 存放按键显示相关信息的文件夹<br>
│	          └── key_display.py                    # 按键显示相关代码<br>
│   ├── Radar                                         #存放雷达显示相关信息的文件夹<br>
│          └──radar_display.py                   # 雷达显示相关代码<br>
│   ├── templates                                   # 存放html文档的文件夹<br>
│          └──index.html                            # web主页<br>
│   ├── static                                          # 存放静态文件的文件夹<br>
│          ├── slider.css                             # 滑块样式<br>
│          ├── style.css                              # 主样式<br>
│          └──toggle.css                            # 拨片开关样式<br>
│   └── UI.py                                          # 主要的UI逻辑文件<br>
├── main.py                                            # 程序入口（目前版本为空文件，若以后增加其他功能，则可能被作为主入口）<br>
├── LICENSE                                           # 许可证文件<br>
├── README.md                                    # 项目介绍<br>
└── requirements.txt                              # 所需库<br>

**安装所需依赖库：**
pip install -r requirements.txt

**打包项目：**
pyinstaller vanex.spec