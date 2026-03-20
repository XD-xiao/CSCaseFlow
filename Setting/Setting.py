"""
集中管理项目配置：
- 尽量把会经常调整的参数都放在这里，避免散落在业务代码里
- 坐标/尺寸默认单位为像素(px)
"""


"""
窗口配置
"""
CS2_TITLE = "Counter-Strike 2"  # 游戏窗口标题

CS2_PROCESS_NAME = "cs2.exe"  # 游戏进程名


"""
输入模拟配置
"""
MOUSEEVENTF_MOVE = 0x0001  # 鼠标相对移动标志


"""
内存读取配置
"""
ENTITY_COUNT = 64  # 最大实体数量
ENTITY_ENTRY_SIZE = 112  # EntityList 单条结构大小(byte)


"""
主程序配置
"""
MAX_MATCH_COUNT = 3
WaitTime = 12
ActivationToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJDU0Nhc2VGbG93Iiwic3ViIjoiYWN0aXZhdGlvbiIsImlhdCI6MTc3NDAxMjQzOSwibmJmIjoxNzc0MDEyNDM5LCJleHAiOjE3NzQwOTg4Mzl9.pUgVSPTsS119V3eup5HJPERR5JQLTXESOva-cpmXNCA"


"""
偏移文件配置
"""
OFFSETS_DIR_NAME = "Offsets"  # 偏移数据目录名（相对项目根目录），由 cs2-dumper 相关文件生成/存放
OFFSETS_OUTPUT_DIR_NAME = "output"  # 偏移输出目录名（Offsets/output）
OFFSETS_OFFSETS_JSON = "offsets.json"  # offsets.json：常用全局偏移汇总（Utility.extract_offsets 读取）
OFFSETS_CLIENT_DLL_JSON = "client_dll.json"  # client_dll.json：类/字段信息（用于按字段名提取结构偏移）
OFFSETS_BUTTONS_JSON = "buttons.json"  # buttons.json：按键相关偏移（如 jump 等）

"""
地图数据配置
"""
MAP_DATA_DIR_NAME = "mapData"  # 地图数据目录名（相对于项目根目录）
MAP_DATA_FILE_EXT = "pkl"  # 地图数据文件扩展名
MAP_GRID_SIZE = 32  # 世界坐标 -> 网格坐标的单位大小
MAP_AUTO_SAVE_INTERVAL_SEC = 10  # 自动保存间隔(秒)

"""
地图识别配置
"""
MAP_SCREENSHOT_OFFSET_X = 13    # 小地图截图区域相对游戏窗口左上角的偏移X（ControlMain.mapRecognition 使用）
MAP_SCREENSHOT_OFFSET_Y = 36    # 小地图截图区域相对游戏窗口左上角的偏移Y（ControlMain.mapRecognition 使用）
MAP_SCREENSHOT_WIDTH = 276     # 小地图截图区域宽度（像素）
MAP_SCREENSHOT_HEIGHT = 276    # 小地图截图区域高度（像素）
MAP_SCREENSHOT_PATH = "screenshot.png"  # 小地图截图保存文件名（ControlMain.mapRecognition 写入/读取）
MAP_IMAGE_DIR = "UiPic/map"  # 地图模板图片目录（存放 Dust2/Mirage 等模板，ControlMain.mapRecognition 遍历）
MAP_SIMILARITY_THRESHOLD = 0.7  # 地图识别相似度阈值


"""
界面操作配置
"""
CHOOSE_TEAM_OFFSET_X = 700    # 选择队伍偏移量X
CHOOSE_TEAM_OFFSET_Y = 450    # 选择队伍偏移量Y


"""
AutoKill/训练数据采集配置
"""
AUTOKILL_CONSOLE_LOG_PATH = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"  # CS2 控制台日志路径（AutoMain.read_log_file 训练模式读取）
# AUTOKILL_CONSOLE_LOG_PATH = r"D:\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"

AUTOKILL_ATTACK_LOG_REGEX = (
    r"(?P<time>\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?"
    r'"(?P<attacker>.+?)<\d+><.*?><(?P<attacker_team>\w+)>" '
    r"\[(?P<ax>-?\d+) (?P<ay>-?\d+) (?P<az>-?\d+)\] "
    r"attacked "
    r'"(?P<victim>.+?)<\d+><.*?><(?P<victim_team>\w+)>" '
    r"\[(?P<vx>-?\d+) (?P<vy>-?\d+) (?P<vz>-?\d+)\]"
 )  # 解析 console.log 中 “attacked” 行的正则（提取时间、攻击者/被攻击者与坐标）

AUTOKILL_MONITOR_MAP_INTERVAL_SEC = 30  # 地图监控线程轮询间隔（AutoMain.monitor_map）
AUTOKILL_READ_LOG_IDLE_SLEEP_SEC = 0.1  # 日志线程无新行时的等待时间（AutoMain.read_log_file）
AUTOKILL_INFO_LOOP_INTERVAL_SEC = 0.5  # 信息/学习线程打印与采样间隔（logLoop/spottedLearn/walkLearn）

AUTOKILL_MAIN_UPDATE_PLAYER_FAIL_SLEEP_SEC = 0.5  # 主循环读取玩家失败时的退避等待（AutoMain.start）
AUTOKILL_MAIN_WAIT_MAP_MANAGER_SLEEP_SEC = 0.05  # 主循环等待 map_manager 就绪的等待时间（AutoMain.start）
AUTOKILL_MAIN_LOOP_SLEEP_SEC = 0.003  # 主循环每轮末尾的基础停顿（降低 CPU 占用）

AUTOKILL_SMART_KILL_LOOP_SLEEP_SEC = 0.004  # 智能击杀线程基础循环间隔（AutoMain.smart_kill）
AUTOKILL_AIM_CHECK_RETRY_COUNT = 5  # 判断“准星在敌人身上”的最大重试次数（AutoMain.smart_kill）
AUTOKILL_AIM_CHECK_RETRY_SLEEP_SEC = 0.002  # 每次重试间隔（给视角/判定一点同步时间）
AUTOKILL_TAP_FIRE_INTERVAL_SEC = 0.08  # 点射间隔（影响后坐力控制与稳定性）
AUTOKILL_NO_TARGET_SLEEP_SEC = 0.02  # 无可射击目标时的等待时间（避免空转占用 CPU）

AUTOKILL_ANTI_AFK_KEY = "j"  # 防 AFK/自动购买等绑定键（AutoMain.walk 中调用 Utility.tap_key）
AUTOKILL_ANTI_AFK_HOLD_SEC = 0.02  # 防 AFK 按键按下持续时间（tap_key 的 hold 参数）

"""
AutoKill 行走/拟人化配置（AutoMain.walk）
"""
AUTOKILL_WALK_SLEEP_MIN_SEC = 0.1  # 每轮行走逻辑开始前的随机等待最小值
AUTOKILL_WALK_SLEEP_MAX_SEC = 2.0  # 每轮行走逻辑开始前的随机等待最大值
AUTOKILL_WALK_COMBAT_PAUSE_SEC = 0.1  # 战斗状态下暂停行走逻辑的等待时间（让出控制权给击杀逻辑）
AUTOKILL_WALK_TURN_PROBABILITY = 0.5  # 行走逻辑中“转动视角”概率，其余为随机 WASD
AUTOKILL_WALK_TURN_YAW_MIN = -100  # 随机转视角的 yaw 最小值（左右）
AUTOKILL_WALK_TURN_YAW_MAX = 100  # 随机转视角的 yaw 最大值（左右）
AUTOKILL_WALK_TURN_PITCH_MIN = -2  # 随机转视角的 pitch 最小值（上下）
AUTOKILL_WALK_TURN_PITCH_MAX = 2  # 随机转视角的 pitch 最大值（上下）
AUTOKILL_WALK_TURN_SENS = 1.0  # Utility.move 使用的游戏内灵敏度参数（影响换算幅度）
AUTOKILL_WALK_MOVE_KEYS = ("w", "s", "a", "d")  # 随机移动可选方向键集合
AUTOKILL_WALK_MOVE_KEY_WEIGHTS = (0.60, 0.08, 0.16, 0.16)  # 对应 WASD 的权重（更偏向前进）
AUTOKILL_WALK_MOVE_HOLD_MIN_SEC = 0.1  # 随机移动按键按下最短时间
AUTOKILL_WALK_MOVE_HOLD_MAX_SEC = 0.6  # 随机移动按键按下最长时间
AUTOKILL_WALK_MOVE_CHECK_STEP_SEC = 0.05  # 按住移动键期间的分段检查步长（及时响应战斗状态/退出）
AUTOKILL_WALK_INTERRUPT_REST_SEC = 0.2  # 移动被战斗打断后的短暂休息时间（避免操作过于密集）
