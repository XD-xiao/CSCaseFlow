import threading
import time
import ctypes
from pynput.mouse import Controller, Button

from AutoKill.MapManager import MapManager
from AutoKill.MemoryManager import MemoryManager
from AutoKill.PawnReader import PawnReader
from AutoKill.Player import Player
from AutoKill.Uitlity import Utility

mouse = Controller()

def is_key_down(key_code):
    return ctypes.windll.user32.GetAsyncKeyState(key_code) & 0x8000

class AutoKill:
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


    def logLoop(self):
        print("日志线程已启动...")
        while not self.stop_event.is_set():
            time.sleep(1)
            
            with self.player_lock:
                player_info = f"本地玩家: 血量={self.player.health}, 队伍={self.player.team}, 坐标={self.player.pos}"
            
            print("-" * 50)
            print(player_info)
            
            with self.entity_lock:
                current_entities = list(self.entities)
            
            print(f"发现实体数量: {len(current_entities)}")
            for i, ent in enumerate(current_entities):
                # 计算距离
                _, distance = Utility.aimEnemy(self.player.pos, ent.pos)
                print(f"  [{i+1}] 名字: {ent.name:<15} 血量: {ent.health:<3} 队伍: {ent.team} 距离: {distance:.2f} 坐标: {ent.pos}")
            
            print("-" * 50)

    def kill(self, mapManager: MapManager):
        print("日志线程已启动...")
        while not self.stop_event.is_set():
            time.sleep(0.1)

            with self.player_lock:
                player_info = f"本地玩家: 血量={self.player.health}, 队伍={self.player.team}, 坐标={self.player.pos}"

            print("-" * 50)
            print(player_info)

            with self.entity_lock:
                current_entities = list(self.entities)

            print(f"发现实体数量: {len(current_entities)}")
            for i, ent in enumerate(current_entities):
                # 计算距离
                print(
                    f"  [{i + 1}] 名字: {ent.name:<15} 血量: {ent.health:<3} 队伍: {ent.team} canShoot: {ent.isCanShot}")

                # if ent.isCanShot:
                #     self.reader.setAngle(self.player,ent.canShoutAngle)
                count = 0

                while ent.isCanShot and ent.health >= 0:
                    # 判断是否能击中
                    self.reader.update_IsShout(self.player)
                    self.reader.setAngle(self.player, ent.canShoutAngle)
                    if self.player.isShout is not None and self.player.health > 0:

                        mouse.click(Button.left)
                        time.sleep(0.003)
                        mouse.click(Button.left)
                        time.sleep(0.003)
                        count = 0
                    elif count <= 9:
                        # 如果打不到，刷新位置再试
                        # 实体数据
                        count = count + 1
                        print(f"瞄准次数{count}")
                        self.reader.update_entity_data(ent, self.player,mapManager)
                        # 重新瞄准
                        self.reader.update_IsShout(self.player)
                        continue
                    else:
                        break
                    time.sleep(0.001)  # 射击间隔



            print("-" * 50)


    def start(self):
        print("正在初始化...")
        if not self.mem.initialize():
            print("初始化内存管理器失败。")
            return

        print("作弊已启动。按 'END' 键退出。")
        self.is_running = True

        mapManager = MapManager("Dust2")

        threading.Thread(
            target=self.kill,
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
            
            time.sleep(0.01)

        # 保存地图数据
        mapManager.save_data()



if __name__ == "__main__":
    app = AutoKill()
    app.start()
