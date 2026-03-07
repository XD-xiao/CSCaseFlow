import threading
import time
import ctypes
import os
import random
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
        
        # 战斗状态标志，用于互斥行走
        self.is_combat = False


    def logLoop(self, mapManager: MapManager):
        print("日志线程已启动...")
        while not self.stop_event.is_set():
            time.sleep(0.5)

            with self.player_lock:
                player_info = f"本地玩家: 血量={self.player.health}, 队伍={self.player.team}, 坐标={self.player.pos}"

            print("-" * 50)
            # print(player_info)


            
            with self.entity_lock:
                current_entities = list(self.entities)
            
            print(f"发现实体数量: {len(current_entities)}")

            for i, ent in enumerate(current_entities):
                print(f"{i}: {ent}")

            print("-" * 50)

    def walk(self):
        print("行走 thread started...")
        
        while not self.stop_event.is_set():
            # 1. 随机时间（5秒内）
            sleep_time = random.uniform(0.1, 2.0)
            time.sleep(sleep_time)
            
            if self.stop_event.is_set():
                break

            # 如果处于战斗状态，暂停行走逻辑
            if self.is_combat:
                time.sleep(0.1)
                continue

            # 2. 随机转动视角或走路，概率默认50%
            if random.random() < 0.5:
                # 随机转动视角
                # 随机转动角度，-60~60之间
                yaw_delta = random.uniform(-100, 100)
                # 稍微给一点点 pitch 变化更真实，或者 0
                pitch_delta = random.uniform(-2, 2)
                
                # 再次检查战斗状态
                if self.is_combat:
                    continue
                    
                # 使用 Utility.move 相对移动
                # print(f"随机视角: yaw={yaw_delta:.1f}")
                Utility.move(yaw_delta, pitch_delta, sens=1.0)
            else:
                # 随机行走方向（WASD）
                # w: 60%, s: 8%, a: 16%, d: 16%
                keys = ['w', 's', 'a', 'd']
                weights = [0.60, 0.08, 0.16, 0.16]
                key = random.choices(keys, weights=weights, k=1)[0]
                duration = random.uniform(0.1, 0.6)
                
                vk_code = Utility.get_vk_code(key)
                # print(f"随机移动: {key} for {duration:.2f}s")
                
                if self.is_combat:
                    continue
                    
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0) # Press
                
                # 分段等待，以便在战斗开始时及时停止
                start_time = time.time()
                interrupted = False
                while time.time() - start_time < duration:
                    if self.is_combat:
                        interrupted = True
                        break
                    time.sleep(0.05)
                
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0) # Release
                
                if interrupted:
                    # 如果被打断，稍微休息一下
                    time.sleep(0.2)

        return None


    def smart_kill(self, mapManager: MapManager):
        print("智能自动击杀已启动 (点射模式)...")
        while not self.stop_event.is_set():
            # 基础循环间隔，让出CPU
            time.sleep(0.005)

            # 获取最新实体列表
            with self.entity_lock:
                current_entities = list(self.entities)

            if not current_entities:
                continue

            # 寻找最佳目标
            target = None
            min_dist = float('inf')
            
            # 获取玩家位置用于计算距离
            with self.player_lock:
                if self.player.health <= 0:
                    continue
                p_pos = self.player.pos
                
            for ent in current_entities:
                if ent.health <= 0:
                    continue
                
                # 必须是可射击的 (MapManager判定)
                if ent.isCanShot:
                    # 计算距离 (平方和即可，不开方也能比较)
                    dist = (ent.pos['x'] - p_pos['x'])**2 + \
                           (ent.pos['y'] - p_pos['y'])**2 + \
                           (ent.pos['z'] - p_pos['z'])**2
                    
                    if dist < min_dist:
                        min_dist = dist
                        target = ent

            # 攻击逻辑
            if target:
                self.is_combat = True
                # 持续更新该目标的数据和角度（因为玩家和敌人都在动）
                # 这一步很重要，确保瞄准的是最新位置
                self.reader.update_entity_data(target, self.player, mapManager)
                
                # 瞄准
                self.reader.setAngle(self.player, target.canShoutAngle)
                
                # 判断准星是否在敌人身上 (内存读取，100%准确)
                # 给予少量重试机会以等待视角同步或游戏判定更新
                is_aiming_at_enemy = False
                for _ in range(5):
                    if self.reader.update_IsShout(self.player):
                        is_aiming_at_enemy = True
                        break
                    time.sleep(0.002)
                
                if is_aiming_at_enemy:
                    mouse.click(Button.left)
                    # 关键：点射延迟，防止枪口上飘 (Recoil Control via Tap Firing)
                    # 0.15秒左右是比较稳的点射间隔
                    time.sleep(0.05)
                else:
                    # 如果瞄准了但没对准（可能是MapManager判定可射击但实际有微小遮挡，或者目标移动极快）
                    # 不开火，防止浪费子弹或暴露
                    pass
            else:
                self.is_combat = False
                # 如果没有可射击目标，稍微多睡一会
                time.sleep(0.02)

    def start(self , mapName: str) -> None:
        print("正在初始化...")
        if not self.mem.initialize():
            print("初始化内存管理器失败。")
            return

        print("作弊已启动。按 'END' 键退出。")
        self.is_running = True


        mapManager = MapManager(mapName)


        # threading.Thread(
        #     target=self.logLoop,
        #     args=(mapManager,),
        #     daemon=True,
        # ).start()


        # 启动智能击杀线程
        threading.Thread(
            target=self.smart_kill,
            args=(mapManager,),
            daemon=True
        ).start()

        threading.Thread(
            target=self.walk,
            daemon=True,
        ).start()

        print("主循环已启动...")
        last_w_press_time = time.time()
        
        while self.is_running:
            if is_key_down(Utility.get_vk_code("end")):
                print("收到 END，正在退出程序...")
                self.is_running = False
                self.stop_event.set()
                try:
                    mapManager.save_data()
                except Exception as e:
                    print(f"保存数据失败: {e}")
                os._exit(0)
            
            # 每隔1秒按一下W键 (防掉线/保持活跃)
            # if time.time() - last_w_press_time > 0.5:
            #     vk_w = Utility.get_vk_code("w")
            #     ctypes.windll.user32.keybd_event(vk_w, 0, 0, 0)  # 按下
            #     time.sleep(0.25)
            #     ctypes.windll.user32.keybd_event(vk_w, 0, 2, 0)  # 抬起
            #     last_w_press_time = time.time()

            if not self.reader.update_player(self.player):
                time.sleep(0.5)
                continue
            
            # 获取新实体列表
            new_entities = self.reader.get_all_entities(self.player,mapManager)
            
            # 如果new_entities为空，则推出循环
            if not new_entities:
                print("实体数组为空,退出射击")
                break

            # 更新实体列表（加锁）
            with self.entity_lock:
                self.entities = new_entities
            
            time.sleep(0.005)
            


        return 0




if __name__ == "__main__":
    app = AutoKill()
    app.start("")
