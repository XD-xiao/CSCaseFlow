import threading
import time
import ctypes
import os
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
# input_file = r"D:\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"
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



    def logLoop(self, mapManager: MapManager):
        print("日志线程已启动...")
        while not self.stop_event.is_set():
            time.sleep(0.5)

            with self.player_lock:
                player_info = (
                    f"本地玩家: m_bSpotted:{self.player.Spotted}  "
                    f"m_bSpottedByMask:{self.player.SpottedByMask}"
                )

            print("-" * 50)
            print(player_info)

            with self.entity_lock:
                current_entities = list(self.entities)

            # print(f"发现实体数量: {len(current_entities)}")

            for i, ent in enumerate(current_entities):
                print(f"{ent.id}: hp: {ent.health} ")

            print("-" * 50)


    def oneTraining(self, mapManager: MapManager):
        print("数据录入线程已启动...")
        last_print_time = time.time()

        while not self.stop_event.is_set():
            time.sleep(0.01)

            # 1. 获取快照 (减少锁持有时间)
            with self.player_lock:
                if self.player.health <= 0:
                    continue
                # 浅拷贝位置数据
                player_pos = self.player.pos.copy() if isinstance(self.player.pos, dict) else self.player.pos

            with self.entity_lock:
                # 列表浅拷贝
                current_entities = list(self.entities)

            # 2. 批量写入地图 (只获取一次锁)
            try:
                with self.map_lock:
                    # 录入玩家位置
                    mapManager.add_walkable(player_pos)
                    
                    # 录入实体位置
                    for ent in current_entities:
                        if ent.health > 0:
                            mapManager.add_walkable(ent.pos)
            except Exception as e:
                print(f"Error adding data to map: {e}")

            # 3. 日志输出 (降低频率，每5秒一次)
            if time.time() - last_print_time > 5.0:
                print(f"[Training] 正在录入... 玩家位置: {player_pos} | 周围实体数: {len(current_entities)}")
                last_print_time = time.time()


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
                    dist = (ent.pos['x'] - p_pos['x']) ** 2 + \
                           (ent.pos['y'] - p_pos['y']) ** 2 + \
                           (ent.pos['z'] - p_pos['z']) ** 2

                    if dist < min_dist:
                        min_dist = dist
                        target = ent

            # 攻击逻辑
            if target:
                # 持续更新该目标的数据和角度（因为玩家和敌人都在动）
                # 这一步很重要，确保瞄准的是最新位置
                self.reader.update_entity_data(target, self.player, mapManager)

                # 瞄准
                self.reader.setAngle(self.player, target.canShoutAngle, stop_event=self.stop_event)

                # 判断准星是否在敌人身上 (内存读取，100%准确)
                # 给予少量重试机会以等待视角同步或游戏判定更新
                is_aiming_at_enemy = False
                for _ in range(5):
                    if self.stop_event.is_set():
                        break
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

        # 启动日志读取线程
        # threading.Thread(
        #     target=self.read_log_file,
        #     args=(mapManager,),
        #     daemon=True
        # ).start()

        # 启动数据录入线程
        # threading.Thread(
        #     target=self.oneTraining,
        #     args=(mapManager,),
        #     daemon=True
        # ).start()


        # 启动信息输出线程
        threading.Thread(
            target=self.logLoop,
            args=(mapManager,),
            daemon=True
        ).start()

        # 启动智能击杀线程
        # threading.Thread(
        #     target=self.smart_kill,
        #     args=(mapManager,),
        #     daemon=True
        # ).start()

        print("主循环已启动...")
        try:
            while self.is_running and not self.stop_event.is_set():
                if is_key_down(Utility.get_vk_code("end")):
                    print("收到 END，正在退出程序...")
                    self.is_running = False
                    self.stop_event.set()
                    try:
                        mapManager.save_data()
                    except Exception:
                        pass
                    os._exit(0)

                if not self.reader.update_player(self.player):
                    time.sleep(0.5)
                    continue

                new_entities = self.reader.get_all_entities(self.player, mapManager)

                if not new_entities:
                    print("实体数组为空,退出射击")
                    self.is_running = False
                    self.stop_event.set()
                    break

                with self.entity_lock:
                    self.entities = new_entities

                time.sleep(0.01)
        finally:
            self.is_running = False
            self.stop_event.set()
            try:
                mapManager.save_data()
            except Exception:
                pass

        return None


if __name__ == "__main__":
    app = Training()
    app.start("")
