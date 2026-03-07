# CSCaseFarm2

## 项目介绍 (Introduction)

CSCaseFarm2 是一个针对 Counter-Strike 2 (CS2) 的自动化挂机与辅助工具。该项目通过读取游戏内存获取实时数据，并模拟鼠标和键盘操作来实现自动瞄准、自动射击、自动行走以及地图识别等功能。主要用于挂机刷箱子或自动化测试。

## 目前功能 (Features)

1. **智能自动击杀 (Smart Auto-Kill)**
   - 通过内存读取获取敌人位置。
   - 自动瞄准并进行点射 (Tap Firing)，包含后坐力控制逻辑。
   - 优先攻击逻辑：当发现可射击目标时，优先进行战斗，暂停行走。
2. **自动行走与防 AFK (Auto Walk & Anti-AFK)**
   - 随机移动逻辑：在没有战斗时，随机进行视角转动和 WASD 移动。
   - 模拟真实玩家操作：随机的按键时长和视角转动幅度。
   - 互斥逻辑：战斗状态下自动停止行走，确保射击精度。
3. **自动化流程控制 (Automated Flow Control)**
   - **地图识别**：通过屏幕截图匹配，自动识别当前地图 (Dust2, Mirage, Inferno, Vertigo)。
   - **自动选队**：进入游戏后自动选择队伍。
4. **训练模式 (Training Mode)**
   - 提供 `mainTraining.py` 用于从控制台日志 (console.log) 中采集数据，用于优化导航或行为逻辑。

## 运行方法 (How to Run)

### 前置条件

- Windows 操作系统
- Python 3.x
- 安装必要的 Python 依赖库 (如 `pynput`, `opencv-python`, `pillow`, `requests` 等，视具体导入而定)
- 确保 CS2 游戏以支持截图的模式运行 (建议窗口化并使用1280×720分辨率)
- 建议使用以下CS2命令，确保可以高效的执行与训练

```
bind "j" "buy ak47; buy m4a1_s; buy m4a1_silencer"

mp_logdetail 3
log on
developer 1
con_logfile console.log
bot_difficulty 3
bot_allow_rogues 1
```



### 启动自动挂机

1. 打开 CS2 并进入游戏大厅或直接开始匹配。
2. 运行主程序：
   ```bash
   python main.py
   ```
3. 程序将自动识别地图、选择队伍并开始自动击杀循环。
4. 按 `END` 键可安全退出程序并保存数据。

### 启动训练模式

1. 确保控制台日志路径配置正确 (在 `AutoKill/Training.py` 中设置 `input_file`)。
2. 运行训练程序：
   ```bash
   python mainTraining.py
   ```
3. 根据提示输入 `1` 确认开始。

## 致谢 (Acknowledgments)

*   本项目中的 Offsets 数据以及 `cs2-dumper.exe` 程序来源于 [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper.git) 项目。

## 声明 (Disclaimer)

- **AI 辅助开发**：本项目大部分代码由人工智能 (AI) 编写和生成。
- **仅供学习与研究使用**：本项目旨在研究游戏内存结构与自动化控制技术。
- **风险自负**：在受 Valve 反作弊系统 (VAC) 保护的服务器上使用此类工具极大概率会导致账号被封禁 (VAC Ban)。
- **免责条款**：作者不对因使用本软件导致的任何账号损失、硬件损坏或法律后果负责。请勿在官方匹配或破坏他人游戏体验的场合使用。

