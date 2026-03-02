import threading
import time
import ctypes
import re
from typing import Dict
from pynput.mouse import Controller, Button

from AutoKill.MapManager import MapManager
from AutoKill.MemoryManager import MemoryManager
from AutoKill.PawnReader import PawnReader
from AutoKill.Player import Player
from AutoKill.Uitlity import Utility


mouse = Controller()
input_file = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"
output_file = "attacks.txt"

pattern = re.compile(
    r'(?P<time>\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'"(?P<attacker>.+?)<\d+><.*?><(?P<attacker_team>\w+)>" '
    r'\[(?P<ax>-?\d+) (?P<ay>-?\d+) (?P<az>-?\d+)\] '
    r'attacked '
    r'"(?P<victim>.+?)<\d+><.*?><(?P<victim_team>\w+)>" '
    r'\[(?P<vx>-?\d+) (?P<vy>-?\d+) (?P<vz>-?\d+)\]'
)


def is_key_down(key_code):
    return ctypes.windll.user32.GetAsyncKeyState(key_code) & 0x8000

def make_spawn_pos(x: str, y: str, z: str) -> Dict[str, float]:
    """把坐标转为 dict[str, float]"""
    return {"x": float(x), "y": float(y), "z": float(z)}

class Training:
    def __init__(self) -> None:
        # 1. 初始化内存管理器（内部加载偏移量）
        utility = Utility()
        buttons_data, offsets, client_data = utility.fetch_offsets()
        if offsets is None or client_data is None or buttons_data is None:
            print("错误：无法加载偏移量数据。")
            self.mem = MemoryManager({}, {}, {})
        else:
            self.mem = MemoryManager(offsets, client_data, buttons_data)

        # 2. 初始化逻辑层
        self.reader = PawnReader(self.mem)
        self.player = Player()
        self.entities = []

        self.is_running = False
        self.stop_event = threading.Event()
        self.data_ready = threading.Event()
        self.entity_lock = threading.Lock()
        self.player_lock = threading.Lock()
        self.map_lock = threading.Lock()

    def read_log_file(self, mapManager: MapManager):
        print("日志读取线程已启动...")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                f.seek(0, 2)  # 跳到文件末尾
                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue

                    match = pattern.search(line)
                    if match:
                        attacker = match.group("attacker")
                        attacker_pos = make_spawn_pos(match.group("ax"), match.group("ay"), match.group("az"))
                        victim = match.group("victim")
                        victim_pos = make_spawn_pos(match.group("vx"), match.group("vy"), match.group("vz"))

                        record = (
                            f"时间: {match.group('time')} | 攻击者: {attacker} 坐标: {attacker_pos} "
                            f"| 被攻击者: {victim} 坐标: {victim_pos}"
                        )
                        print(record)
                        
                        # 加锁保护地图写入
                        with self.map_lock:
                            mapManager.add_walkable_path(attacker_pos, victim_pos)
        except FileNotFoundError:
            print(f"错误: 找不到日志文件 {input_file}")
        except Exception as e:
            print(f"读取日志文件时发生错误: {e}")

    def oneTraining(self, mapManager: MapManager):
        print("数据录入线程已启动...")
        while not self.stop_event.is_set():
            time.sleep(0.01)

            with self.player_lock:
                # 复制位置数据以确保线程安全
                player_pos = self.player.pos.copy() if isinstance(self.player.pos, dict) else self.player.pos
                player_info = f"本地玩家: 坐标={self.player.pos}"

            print("-" * 50)
            print(player_info)
            
            # 加锁保护地图写入
            try:
                with self.map_lock:
                    mapManager.add_walkable(player_pos)
            except Exception as e:
                print(f"Error adding player to map: {e}")

            with self.entity_lock:
                current_entities = list(self.entities)

            print(f"发现实体数量: {len(current_entities)}")
            for i, ent in enumerate(current_entities):
                # 加锁保护地图写入
                try:
                    with self.map_lock:
                        mapManager.add_walkable(ent.pos)
                except Exception as e:
                    print(f"Error adding entity to map: {e}")

                if ent.isCanShot:
                    print("")
                    print("")
                    print(f"********name:{ent.name}, health:{ent.health}, team:{ent.team}********")
                    print("")
                    print("")
                    self.reader.setAngle(self.player, ent.canShoutAngle)
                    mouse.click(Button.left)




    def start(self , mapName: str) -> None:
        print("正在初始化...")
        if not self.mem.initialize():
            print("初始化内存管理器失败。")
            return

        print("作弊已启动。按 'END' 键退出。")
        self.is_running = True

        mapManager = MapManager(mapName)

        # 启动日志读取线程
        threading.Thread(
            target=self.read_log_file,
            args=(mapManager,),
            daemon=True
        ).start()

        # 启动数据录入线程
        threading.Thread(
            target=self.oneTraining,
            args=(mapManager,),
            daemon=True
        ).start()

        print("主循环已启动...")
        while self.is_running:
            if is_key_down(Utility.get_vk_code("end")):
                self.is_running = False
                self.stop_event.set()
                break

            if not self.reader.update_player(self.player):
                time.sleep(0.5)
                continue

            # 获取新实体列表
            new_entities = self.reader.get_all_entities(self.player,mapManager)

            # 更新实体列表（加锁）
            with self.entity_lock:
                self.entities = new_entities

            time.sleep(0.00001)
        
        # 保存地图数据
        mapManager.save_data()


if __name__ == "__main__":
    app = Training()
    app.start("")
