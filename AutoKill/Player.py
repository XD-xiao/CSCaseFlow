import time
from typing import Dict
from AutoKill.Uitlity import Utility

class Player:
    def __init__(self) -> None:
        self.localControllerPtr = None
        self.pawnPtr = None
        # self.pawnReader removed; Player is now a data holder + control logic
        
        self.health: int = 0
        self.team: int = -1
        self.pos: Dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.angle: Dict[str, float] = {"x": 0.0, "y": 0.0}
        self.isShout: int = -1
        self.weapon: str = ""

        self.Spotted: bool = False
        self.SpottedByMask: list[int] = [0, 0]
