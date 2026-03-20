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
from Setting.Setting import (
    AUTOKILL_AIM_CHECK_RETRY_COUNT,
    AUTOKILL_AIM_CHECK_RETRY_SLEEP_SEC,
    AUTOKILL_ANTI_AFK_HOLD_SEC,
    AUTOKILL_ANTI_AFK_KEY,
    AUTOKILL_ATTACK_LOG_REGEX,
    AUTOKILL_CONSOLE_LOG_PATH,
    AUTOKILL_INFO_LOOP_INTERVAL_SEC,
    AUTOKILL_MAIN_LOOP_SLEEP_SEC,
    AUTOKILL_MAIN_UPDATE_PLAYER_FAIL_SLEEP_SEC,
    AUTOKILL_MAIN_WAIT_MAP_MANAGER_SLEEP_SEC,
    AUTOKILL_MONITOR_MAP_INTERVAL_SEC,
    AUTOKILL_NO_TARGET_SLEEP_SEC,
    AUTOKILL_READ_LOG_IDLE_SLEEP_SEC,
    AUTOKILL_SMART_KILL_LOOP_SLEEP_SEC,
    AUTOKILL_TAP_FIRE_INTERVAL_SEC,
    AUTOKILL_WALK_COMBAT_PAUSE_SEC,
    AUTOKILL_WALK_INTERRUPT_REST_SEC,
    AUTOKILL_WALK_MOVE_CHECK_STEP_SEC,
    AUTOKILL_WALK_MOVE_HOLD_MAX_SEC,
    AUTOKILL_WALK_MOVE_HOLD_MIN_SEC,
    AUTOKILL_WALK_MOVE_KEY_WEIGHTS,
    AUTOKILL_WALK_MOVE_KEYS,
    AUTOKILL_WALK_SLEEP_MAX_SEC,
    AUTOKILL_WALK_SLEEP_MIN_SEC,
    AUTOKILL_WALK_TURN_PITCH_MAX,
    AUTOKILL_WALK_TURN_PITCH_MIN,
    AUTOKILL_WALK_TURN_PROBABILITY,
    AUTOKILL_WALK_TURN_SENS,
    AUTOKILL_WALK_TURN_YAW_MAX,
    AUTOKILL_WALK_TURN_YAW_MIN,
)

mouse = Controller()
input_file = AUTOKILL_CONSOLE_LOG_PATH


pattern = re.compile(AUTOKILL_ATTACK_LOG_REGEX)
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

        self.map_manager = None
        self.map_name = None
        self.temp_map_manager = None
        self.empty_map_manager = MapManager("__empty__", persist=False)

    def _get_map_manager_snapshot(self):
        with self.map_lock:
            return self.map_manager

    def _save_map_manager_if_needed(self, map_manager):
        if map_manager is None:
            return
        if not getattr(map_manager, "persist", True):
            return
        try:
            map_manager.save_data()
        except Exception as e:
            print(f"保存地图数据失败: {e}")

    def _hard_exit(self, reason: str):
        print(reason)
        self.is_running = False
        self.stop_event.set()
        self._save_map_manager_if_needed(self._get_map_manager_snapshot())
        os._exit(0)

    def _set_map_manager(self, new_map_manager, new_map_name, save_old: bool):
        old_map_manager = None
        old_map_name = None
        with self.map_lock:
            old_map_manager = self.map_manager
            old_map_name = self.map_name
            self.map_manager = new_map_manager
            self.map_name = new_map_name

        if save_old:
            self._save_map_manager_if_needed(old_map_manager)

        if new_map_name != old_map_name:
            print(f"==============================  当前地图：{new_map_name}  ==============================")

    def monitor_map(self, mode: int):
        cm = ControlMain()

        while not self.stop_event.is_set():
            try:
                detected = cm.mapRecognition()
            except Exception as e:
                print(f"地图识别失败: {e}")
                detected = None

            if mode == 3 or mode == 4:
                current = None
                with self.map_lock:
                    current = self.map_name
                if detected is None or detected != current:
                    self._hard_exit(f"训练模式地图异常: detected={detected} current={current}，即将退出")

            elif mode == 1:
                if detected:
                    current_mm = self._get_map_manager_snapshot()
                    if not (current_mm and getattr(current_mm, "persist", True) and current_mm.mapName == detected):
                        self._set_map_manager(MapManager(detected, persist=True), detected, save_old=False)
                else:
                    self._set_map_manager(self.empty_map_manager, None, save_old=False)

            else:
                if detected:
                    current_mm = self._get_map_manager_snapshot()
                    if not (current_mm and getattr(current_mm, "persist", True) and current_mm.mapName == detected):
                        self._set_map_manager(MapManager(detected, persist=True), detected, save_old=True)
                else:
                    if self.temp_map_manager is None:
                        self.temp_map_manager = MapManager("temp", persist=False)
                    self._set_map_manager(self.temp_map_manager, None, save_old=True)

            Utility.sleep_with_end(AUTOKILL_MONITOR_MAP_INTERVAL_SEC, stop_event=self.stop_event)

    def read_log_file(self):
        print("日志读取线程已启动...")
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                f.seek(0, 2)
                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        Utility.sleep_with_end(AUTOKILL_READ_LOG_IDLE_SLEEP_SEC, stop_event=self.stop_event)
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

                        map_manager = self._get_map_manager_snapshot()
                        if map_manager:
                            map_manager.add_walkable_path(attacker_pos, victim_pos)
        except FileNotFoundError:
            print(f"错误: 找不到日志文件 {input_file}")
            self.stop_event.set()
            self.is_running = False
        except Exception as e:
            print(f"读取日志文件时发生错误: {e}")
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())
            self.stop_event.set()
            self.is_running = False



    def logLoop(self):
        print("信息打印线程已启动...")
        try:
            while not self.stop_event.is_set():
                Utility.sleep_with_end(AUTOKILL_INFO_LOOP_INTERVAL_SEC, stop_event=self.stop_event)

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

    def spottedLearn(self):
        print("可视学习线程已启动...")
        try:
            while not self.stop_event.is_set():
                Utility.sleep_with_end(AUTOKILL_INFO_LOOP_INTERVAL_SEC, stop_event=self.stop_event)

                with self.player_lock:
                    player_pos = dict(self.player.pos) if self.player.pos else None

                with self.entity_lock:
                    positions = [dict(ent.pos) for ent in self.entities if ent.spotted and ent.pos]

                print(f"可视学习到敌人位置数量: {len(positions)}")

                if player_pos and positions:
                    map_manager = self._get_map_manager_snapshot()
                    if map_manager:
                        for pos in positions:
                            map_manager.add_walkable_path(pos, player_pos)

        except Exception as e:
            print(f"spottedLearn 发生错误: {e}")
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())
            self.stop_event.set()
            self.is_running = False

    def walkLearn(self):
        print("行走学习线程已启动...")
        try:
            while not self.stop_event.is_set():
                Utility.sleep_with_end(AUTOKILL_INFO_LOOP_INTERVAL_SEC, stop_event=self.stop_event)

                with self.player_lock:
                    player_pos = dict(self.player.pos) if self.player.pos else None

                with self.entity_lock:
                    enemy_positions = [dict(ent.pos) for ent in self.entities if ent.health > 0 and ent.pos]

                if player_pos or enemy_positions:
                    map_manager = self._get_map_manager_snapshot()
                    if map_manager:
                        if player_pos:
                            map_manager.add_walkable(player_pos)
                        for pos in enemy_positions:
                            map_manager.add_walkable(pos)

        except Exception as e:
            print(f"walkLearn 发生错误: {e}")
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())
            self.stop_event.set()
            self.is_running = False




    def walk(self):
        print("行走线程已启动...")
        
        while not self.stop_event.is_set():
            # 1. 随机时间（5秒内）
            sleep_time = random.uniform(AUTOKILL_WALK_SLEEP_MIN_SEC, AUTOKILL_WALK_SLEEP_MAX_SEC)
            Utility.sleep_with_end(sleep_time, stop_event=self.stop_event)

            if Utility.request_stop_if_end_pressed(self.stop_event):
                break

            Utility.tap_key(
                AUTOKILL_ANTI_AFK_KEY,
                hold=AUTOKILL_ANTI_AFK_HOLD_SEC,
                only_when_game_active=True,
                stop_event=self.stop_event,
            )
            
            if self.stop_event.is_set():
                break

            # 如果处于战斗状态，暂停行走逻辑
            if self.is_combat:
                Utility.sleep_with_end(AUTOKILL_WALK_COMBAT_PAUSE_SEC, stop_event=self.stop_event)
                continue

            # 2. 随机转动视角或走路，概率默认50%
            if random.random() < AUTOKILL_WALK_TURN_PROBABILITY:
                # 随机转动视角
                # 随机转动角度，-60~60之间
                yaw_delta = random.uniform(AUTOKILL_WALK_TURN_YAW_MIN, AUTOKILL_WALK_TURN_YAW_MAX)
                # 稍微给一点点 pitch 变化更真实，或者 0
                pitch_delta = random.uniform(AUTOKILL_WALK_TURN_PITCH_MIN, AUTOKILL_WALK_TURN_PITCH_MAX)
                
                # 再次检查战斗状态
                if self.is_combat:
                    continue
                    
                # 使用 Utility.move 相对移动
                # print(f"随机视角: yaw={yaw_delta:.1f}")
                Utility.move(yaw_delta, pitch_delta, sens=AUTOKILL_WALK_TURN_SENS, stop_event=self.stop_event)
            else:
                # 随机行走方向（WASD）
                # w: 60%, s: 8%, a: 16%, d: 16%
                key = random.choices(AUTOKILL_WALK_MOVE_KEYS, weights=AUTOKILL_WALK_MOVE_KEY_WEIGHTS, k=1)[0]
                duration = random.uniform(AUTOKILL_WALK_MOVE_HOLD_MIN_SEC, AUTOKILL_WALK_MOVE_HOLD_MAX_SEC)

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
                    Utility.sleep_with_end(AUTOKILL_WALK_MOVE_CHECK_STEP_SEC, stop_event=self.stop_event)
                
                Utility.key_up(key)
                
                if interrupted:
                    # 如果被打断，稍微休息一下
                    Utility.sleep_with_end(AUTOKILL_WALK_INTERRUPT_REST_SEC, stop_event=self.stop_event)

        return None


    def smart_kill(self):
        print("智能自动击杀已启动 (点射模式)...")
        while not self.stop_event.is_set():
            # 基础循环间隔，让出CPU
            Utility.sleep_with_end(AUTOKILL_SMART_KILL_LOOP_SLEEP_SEC, stop_event=self.stop_event)
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
                map_manager = self._get_map_manager_snapshot()
                if not map_manager:
                    continue
                self.reader.update_entity_data(target, self.player, map_manager)
                
                # 瞄准
                self.reader.setAngle(self.player, target.canShoutAngle, stop_event=self.stop_event)
                
                # 判断准星是否在敌人身上 (内存读取，100%准确)
                # 给予少量重试机会以等待视角同步或游戏判定更新
                is_aiming_at_enemy = False
                for _ in range(AUTOKILL_AIM_CHECK_RETRY_COUNT):
                    if self.reader.update_IsShout(self.player):
                        is_aiming_at_enemy = True
                        break
                    Utility.sleep_with_end(AUTOKILL_AIM_CHECK_RETRY_SLEEP_SEC, stop_event=self.stop_event)
                
                if is_aiming_at_enemy:
                    mouse.click(Button.left)
                    # 关键：点射延迟，防止枪口上飘 (Recoil Control via Tap Firing)
                    # 0.15秒左右是比较稳的点射间隔
                    Utility.sleep_with_end(AUTOKILL_TAP_FIRE_INTERVAL_SEC, stop_event=self.stop_event)
                else:
                    # 如果瞄准了但没对准（可能是MapManager判定可射击但实际有微小遮挡，或者目标移动极快）
                    # 不开火，防止浪费子弹或暴露
                    pass
            else:
                self.is_combat = False
                # 如果没有可射击目标，稍微多睡一会
                Utility.sleep_with_end(AUTOKILL_NO_TARGET_SLEEP_SEC, stop_event=self.stop_event)


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
        cm = ControlMain()
        try:
            initial_map_name = cm.mapRecognition()
        except Exception as e:
            print(f"地图识别失败: {e}")
            initial_map_name = None

        if mode == 3 or mode == 4:
            if not initial_map_name:
                print("训练模式未识别地图，退出")
                self.is_running = False
                self.stop_event.set()
                return None
            self._set_map_manager(MapManager(initial_map_name, persist=True), initial_map_name, save_old=False)
        elif mode == 1:
            if initial_map_name:
                self._set_map_manager(MapManager(initial_map_name, persist=True), initial_map_name, save_old=False)
            else:
                self._set_map_manager(self.empty_map_manager, None, save_old=False)
        else:
            if initial_map_name:
                self._set_map_manager(MapManager(initial_map_name, persist=True), initial_map_name, save_old=False)
            else:
                self.temp_map_manager = MapManager("temp", persist=False)
                self._set_map_manager(self.temp_map_manager, None, save_old=False)

        threading.Thread(
            target=self.monitor_map,
            args=(mode,),
            daemon=True,
        ).start()

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
                daemon=True
            ).start()

        # 启动可视学习线程
        if mode == 2 or mode == 3 or mode ==4 :
            threading.Thread(
                target=self.spottedLearn,
                daemon=True,
            ).start()

        # 启动行走学习线程
        if mode == 3 or mode ==4 :
            threading.Thread(
                target=self.walkLearn,
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
                daemon=True
            ).start()



        print("主循环已启动...")
        try:
            def handle_end() -> None:
                self.is_running = False
                self._save_map_manager_if_needed(self._get_map_manager_snapshot())

            while self.is_running:
                if Utility.request_stop_if_end_pressed(self.stop_event, on_end=handle_end):
                    break

                if not self.reader.update_player(self.player):
                    Utility.sleep_with_end(AUTOKILL_MAIN_UPDATE_PLAYER_FAIL_SLEEP_SEC, stop_event=self.stop_event)
                    continue

                map_manager = self._get_map_manager_snapshot()
                if not map_manager:
                    Utility.sleep_with_end(AUTOKILL_MAIN_WAIT_MAP_MANAGER_SLEEP_SEC, stop_event=self.stop_event)
                    continue
                new_entities = self.reader.get_all_entities(self.player, map_manager)
                
                if not new_entities:
                    print("实体数组为空,退出射击")
                    self.is_running = False
                    self.stop_event.set()
                    self._save_map_manager_if_needed(self._get_map_manager_snapshot())
                    break

                with self.entity_lock:
                    self.entities = new_entities
                
                Utility.sleep_with_end(AUTOKILL_MAIN_LOOP_SLEEP_SEC, stop_event=self.stop_event)
        except KeyboardInterrupt:
            self.is_running = False
            self.stop_event.set()
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())
        except Exception as e:
            print(f"主循环发生错误: {e}")
            self.is_running = False
            self.stop_event.set()
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())
        finally:
            self._save_map_manager_if_needed(self._get_map_manager_snapshot())

        return None




if __name__ == "__main__":
    app = AutoKill()
    app.start(1)
