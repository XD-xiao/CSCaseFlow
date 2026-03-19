import re
import threading
import time
import os
import random
from pynput.mouse import Controller, Button

from AutoKill.MapManager import MapManager
from AutoKill.MemoryManager import MemoryManager
from AutoKill.PawnReader import PawnReader
from AutoKill.Player import Player
from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain

mouse = Controller()
input_file = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"
# input_file = r"D:\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"

pattern = re.compile(
    r'(?P<time>\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'"(?P<attacker>.+?)<\d+><.*?><(?P<attacker_team>\w+)>" '
    r'\[(?P<ax>-?\d+) (?P<ay>-?\d+) (?P<az>-?\d+)\] '
    r'attacked '
    r'"(?P<victim>.+?)<\d+><.*?><(?P<victim_team>\w+)>" '
    r'\[(?P<vx>-?\d+) (?P<vy>-?\d+) (?P<vz>-?\d+)\]'
)
map_fail_count = 0

class AutoKill:
    def __init__(self) -> None:
        # 1. 初始化内存管理器（内部加载偏移量）
        self.mem = MemoryManager()
        
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
        
        # 战斗状态标志，用于互斥行走
        self.is_combat = False

    def read_log_file(self, mapManager: MapManager):
        print("日志读取线程已启动...")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                f.seek(0, 2)
                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue

                    match = pattern.search(line)
                    if match:
                        attacker = match.group("attacker")
                        attacker_pos = Utility.make_spawn_pos(match.group("ax"), match.group("ay"), match.group("az"))
                        victim = match.group("victim")
                        victim_pos = Utility.make_spawn_pos(match.group("vx"), match.group("vy"), match.group("vz"))

                        record = (
                            f"时间: {match.group('time')} | 攻击者: {attacker} 坐标: {attacker_pos} "
                            f"| 被攻击者: {victim} 坐标: {victim_pos}"
                        )
                        print(record)

                        with self.map_lock:
                            mapManager.add_walkable_path(attacker_pos, victim_pos)
        except FileNotFoundError:
            print(f"错误: 找不到日志文件 {input_file}")
            self.stop_event.set()
            self.is_running = False
        except Exception as e:
            print(f"读取日志文件时发生错误: {e}")
            with self.map_lock:
                mapManager.save_data()
            self.stop_event.set()
            self.is_running = False



    def logLoop(self, mapManager: MapManager):
        print("信息打印线程已启动...")
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)

                with self.player_lock:
                    player_info = f"本地玩家: 位置:{self.player.pos} | 生命值:{self.player.health}"

                print("-" * 50)
                print(player_info)

                with self.entity_lock:
                    current_entities = list(self.entities)

                print(f"发现实体数量: {len(current_entities)}")

                for i, ent in enumerate(current_entities):
                    if ent.spotted:
                        print(f"{i}: {ent.name} | 敌人被发现 位置:{ent.pos} ")

                print("-" * 50)
        except Exception as e:
            print(f"logLoop 发生错误: {e}")
            self.stop_event.set()
            self.is_running = False

    def spottedLearn(self , mapManager: MapManager):
        print("可视学习线程已启动...")
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)

                with self.player_lock:
                    player_pos = dict(self.player.pos) if self.player.pos else None

                with self.entity_lock:
                    positions = [dict(ent.pos) for ent in self.entities if ent.spotted and ent.pos]

                print(f"可视学习到敌人位置数量: {len(positions)}")

                if player_pos and positions:
                    with self.map_lock:
                        for pos in positions:
                            mapManager.add_walkable_path(pos, player_pos)

        except Exception as e:
            print(f"spottedLearn 发生错误: {e}")
            with self.map_lock:
                mapManager.save_data()
            self.stop_event.set()
            self.is_running = False

    def walkLearn(self , mapManager: MapManager):
        print("行走学习线程已启动...")
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)

                with self.player_lock:
                    player_pos = dict(self.player.pos) if self.player.pos else None

                with self.entity_lock:
                    enemy_positions = [dict(ent.pos) for ent in self.entities if ent.health > 0 and ent.pos]

                if player_pos or enemy_positions:
                    with self.map_lock:
                        if player_pos:
                            mapManager.add_walkable(player_pos)
                        for pos in enemy_positions:
                            mapManager.add_walkable(pos)

        except Exception as e:
            print(f"walkLearn 发生错误: {e}")
            with self.map_lock:
                mapManager.save_data()
            self.stop_event.set()
            self.is_running = False




    def walk(self):
        print("行走线程已启动...")
        
        while not self.stop_event.is_set():
            # 1. 随机时间（5秒内）
            sleep_time = random.uniform(0.1, 2.0)
            Utility.sleep_with_end(sleep_time, stop_event=self.stop_event)

            if Utility.request_stop_if_end_pressed(self.stop_event):
                break

            Utility.tap_key("j", hold=0.02, only_when_game_active=True, stop_event=self.stop_event)
            
            if self.stop_event.is_set():
                break

            # 如果处于战斗状态，暂停行走逻辑
            if self.is_combat:
                Utility.sleep_with_end(0.1, stop_event=self.stop_event)
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
                Utility.move(yaw_delta, pitch_delta, sens=1.0, stop_event=self.stop_event)
            else:
                # 随机行走方向（WASD）
                # w: 60%, s: 8%, a: 16%, d: 16%
                keys = ['w', 's', 'a', 'd']
                weights = [0.60, 0.08, 0.16, 0.16]
                key = random.choices(keys, weights=weights, k=1)[0]
                duration = random.uniform(0.1, 0.6)

                if self.is_combat:
                    continue
                    
                Utility.key_down(key)
                
                # 分段等待，以便在战斗开始时及时停止
                start_time = time.time()
                interrupted = False
                while time.time() - start_time < duration:
                    if self.is_combat:
                        interrupted = True
                        break
                    Utility.sleep_with_end(0.05, stop_event=self.stop_event)
                
                Utility.key_up(key)
                
                if interrupted:
                    # 如果被打断，稍微休息一下
                    Utility.sleep_with_end(0.2, stop_event=self.stop_event)

        return None


    def smart_kill(self, mapManager: MapManager):
        print("智能自动击杀已启动 (点射模式)...")
        while not self.stop_event.is_set():
            # 基础循环间隔，让出CPU
            time.sleep(0.004)
            if Utility.request_stop_if_end_pressed(self.stop_event):
                break

            # 获取最新实体列表
            with self.entity_lock:
                current_entities = list(self.entities)

            if not current_entities:
                continue

            # 寻找目标
            target = None
            
            # 获取玩家位置用于计算距离
            with self.player_lock:
                if self.player.health <= 0:
                    continue
                
            for ent in current_entities:
                if ent.health <= 0:
                    continue
                
                # 必须是可射击的 (MapManager判定)
                if ent.isCanShot:
                    target = ent
                    break

            # 攻击逻辑
            if target:
                self.is_combat = True
                # 持续更新该目标的数据和角度（因为玩家和敌人都在动）
                # 这一步很重要，确保瞄准的是最新位置
                self.reader.update_entity_data(target, self.player, mapManager)
                
                # 瞄准
                self.reader.setAngle(self.player, target.canShoutAngle, stop_event=self.stop_event)
                
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
                    Utility.sleep_with_end(0.08, stop_event=self.stop_event)
                else:
                    # 如果瞄准了但没对准（可能是MapManager判定可射击但实际有微小遮挡，或者目标移动极快）
                    # 不开火，防止浪费子弹或暴露
                    pass
            else:
                self.is_combat = False
                # 如果没有可射击目标，稍微多睡一会
                Utility.sleep_with_end(0.02, stop_event=self.stop_event)


    '''
    模式选择
    1:击杀模式,不使用可视学习功能
    2:击杀模式,使用可视学习功能
    3:训练模式,不自动击杀
    4:训练模式,自动击杀
    
    '''

    def start(self , mode: int = 0) -> None:
        print("正在初始化...")
        if not self.mem.initialize():
            print("初始化内存管理器失败。")
            return None

        print("作弊已启动。按 'END' 键退出。")
        self.is_running = True
        global map_fail_count

        cm = ControlMain()
        mapName = cm.mapRecognition()
        print(f"==============================  当前地图：{mapName}  ==============================")
        if mapName is None:
            print("未识别地图，请检查是否进入对局")
            Utility.sleep_with_end(2, stop_event=self.stop_event)
            if map_fail_count >= 10:
                Utility.tap_key("k", hold=0.02, only_when_game_active=True, stop_event=self.stop_event)
                print("地图无法识别,已退出程序")
                os._exit(0)
            map_fail_count += 1
            return None

        mapManager = MapManager(mapName)

        # 启动信息输出线程 ， 调试使用
        # threading.Thread(
        #     target=self.logLoop,
        #     args=(mapManager,),
        #     daemon=True,
        # ).start()

        # 启动日志读取线程 , 仅限训练模式
        if mode == 3 or mode == 4:
            threading.Thread(
                target=self.read_log_file,
                args=(mapManager,),
                daemon=True
            ).start()

        # 启动可视学习线程
        if mode == 2 or mode == 3 or mode ==4 :
            threading.Thread(
                target=self.spottedLearn,
                args=(mapManager,),
                daemon=True,
            ).start()

        # 启动行走学习线程
        if mode == 3 or mode ==4 :
            threading.Thread(
                target=self.walkLearn,
                args=(mapManager,),
                daemon=True,
            ).start()

        # 启动行走线程
        if mode == 1 or mode == 2:
            threading.Thread(
                target=self.walk,
                daemon=True,
            ).start()


        # 启动击杀线程
        if mode == 1 or mode == 2 or mode == 4:
            threading.Thread(
                target=self.smart_kill,
                args=(mapManager,),
                daemon=True
            ).start()



        print("主循环已启动...")
        try:
            def handle_end() -> None:
                self.is_running = False
                with self.map_lock:
                    mapManager.save_data()

            while self.is_running:
                if Utility.request_stop_if_end_pressed(self.stop_event, on_end=handle_end):
                    break

                if not self.reader.update_player(self.player):
                    time.sleep(0.5)
                    continue

                new_entities = self.reader.get_all_entities(self.player,mapManager)
                
                if not new_entities:
                    print("实体数组为空,退出射击")
                    self.is_running = False
                    self.stop_event.set()
                    with self.map_lock:
                        mapManager.save_data()
                    break

                with self.entity_lock:
                    self.entities = new_entities
                
                time.sleep(0.003)
        except KeyboardInterrupt:
            self.is_running = False
            self.stop_event.set()
            with self.map_lock:
                mapManager.save_data()
        except Exception as e:
            print(f"主循环发生错误: {e}")
            self.is_running = False
            self.stop_event.set()
            with self.map_lock:
                mapManager.save_data()
        finally:
            with self.map_lock:
                mapManager.save_data()

        return None




if __name__ == "__main__":
    app = AutoKill()
    app.start(1)
