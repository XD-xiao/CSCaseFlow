import time
from typing import Iterator, Optional, Dict


SKELETON_BONES = {
    6: [5],
    5: [4],
    4: [3, 8, 11],
    3: [0],
    8: [9],
    9: [10],
    11: [12],
    12: [13],
    0: [22, 25],
    22: [23],
    23: [24],
    25: [26],
    26: [27],
}
ALL_BONE_IDS = set(SKELETON_BONES.keys())
for _bones in SKELETON_BONES.values():
    ALL_BONE_IDS.update(_bones)
MAX_BONE_ID = max(ALL_BONE_IDS) if ALL_BONE_IDS else 0

class Entity:

    def __init__(self) -> None:
        self.localControllerPtr = None
        self.pawnPtr = None

        self.id: int = 0  # 实体ID，用于唯一标识实体

        self.pos2d: Optional[Dict[str, float]] = None  # 实体在屏幕上的二维坐标（世界坐标投影到屏幕），用于绘图
        self.distance: float = 0.0  # 实体与玩家的距离
        self.head_pos2d: Optional[Dict[str, float]] = None  # 实体头部在屏幕上的二维坐标，用于绘图（如血条、名字）

        # 缓存的数据
        self.name: str = ""
        self.health: int = 0  # 当前生命值
        self.team: int = -1  # 队伍编号（例如T/CT）
        self.pos: Dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}  # 实体的三维世界坐标位置
        self.angle: Dict[str, float] = {"x": 0.0, "y": 0.0}
        self.isCanShot: bool = False
        self.canShoutAngle: Dict[str, float] = {"x": 0.0, "y": 0.0}

        self.spotted: int = 0
        self.weapon: str = ""

        self.invincible : bool = False  #判断是否在无敌时间,True不在,False正在无敌,无法射击


        return


