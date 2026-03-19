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
偏移文件配置
"""
OFFSETS_DIR_NAME = "Offsets"
OFFSETS_OUTPUT_DIR_NAME = "output"
OFFSETS_OFFSETS_JSON = "offsets.json"
OFFSETS_CLIENT_DLL_JSON = "client_dll.json"
OFFSETS_BUTTONS_JSON = "buttons.json"

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
MAP_SCREENSHOT_OFFSET_X = 13    # 地图截图偏移量X
MAP_SCREENSHOT_OFFSET_Y = 36    # 地图截图偏移量Y
MAP_SCREENSHOT_WIDTH = 276     # 地图截图宽度
MAP_SCREENSHOT_HEIGHT = 276    # 地图截图高度
MAP_SCREENSHOT_PATH = "screenshot.png"
MAP_IMAGE_DIR = "UiPic/map"
MAP_SIMILARITY_THRESHOLD = 0.7  # 地图识别相似度阈值


"""
界面操作配置
"""
CHOOSE_TEAM_OFFSET_X = 700    # 选择队伍偏移量X
CHOOSE_TEAM_OFFSET_Y = 450    # 选择队伍偏移量Y
