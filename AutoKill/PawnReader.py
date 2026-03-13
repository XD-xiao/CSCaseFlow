import time
from typing import List, Optional, Dict
import math
import threading

from AutoKill.MapManager import MapManager
from AutoKill.MemoryManager import MemoryManager
from AutoKill.Entity import Entity
from AutoKill.Player import Player
from AutoKill.Uitlity import Utility




ENTITY_COUNT = 64
ENTITY_ENTRY_SIZE = 112


class PawnReader:
    def __init__(self, memory_manager: MemoryManager) -> None:
        self.mm = memory_manager

    def update_player(self, player: Player) -> bool:
        """
        使用从内存读取的数据更新本地玩家对象。
        """
        if not self.mm.client_base:
            return False

        try:
            # 获取本地玩家 Pawn 地址
            player_pawn_addr = self.mm.read_longlong(self.mm.client_base + self.mm.dwLocalPlayerPawn)
            if not player_pawn_addr:
                return False

            player.pawnPtr = player_pawn_addr
            
            # 读取玩家数据
            player.health = self.mm.read_int(player_pawn_addr + self.mm.m_iHealth)
            player.team = self.mm.read_int(player_pawn_addr + self.mm.m_iTeamNum)
            player.pos = self.mm.read_vec3(player_pawn_addr + self.mm.m_vOldOrigin)
            
            # 视角角度（通常存储在 Client State / LocalPlayerController 中，但此处从 Pawn 读取眼部角度）
            # 注意：控制用的 ViewAngles 通常来自 Client State 中的 dwViewAngles 或类似变量
            # 原始代码从 Pawn 读取 m_angEyeAngles
            player.angle = self.mm.read_vec2(player_pawn_addr + self.mm.m_angEyeAngles)
            
            player.weapon = self.get_weapon_type(player_pawn_addr)
            
            # 检查是否射击
            # 它检查准星 ID 是否大于 0
            player.isShout = self.get_fire_logic_data()

            player.Spotted = bool(self.mm.read_int(player_pawn_addr + self.mm.m_entitySpottedState + self.mm.m_bSpotted))

            spotted_by_mask = self.mm.read_uint32s(
                player_pawn_addr + self.mm.m_entitySpottedState + self.mm.m_bSpottedByMask,
                2,
            )
            mask0, mask1 = spotted_by_mask

            spotted_indices: list[int] = []
            m = mask0
            while m:
                lsb = m & -m
                spotted_indices.append(lsb.bit_length() - 1)
                m ^= lsb

            m = mask1
            while m:
                lsb = m & -m
                spotted_indices.append(lsb.bit_length() - 1 + 32)
                m ^= lsb

            player.SpottedByMask = spotted_indices



            return True
        except Exception as e:
            # print(f"Error updating player: {e}")
            return False
    def update_IsShout(self, player: Player) -> bool:
        player.isShout = self.get_fire_logic_data()
        if player.isShout is not None:
            return True
        return False

    def get_fire_logic_data(self) -> int | None:
        """Retrieve data necessary for firing logic."""
        try:
            player = self.mm.read_longlong(self.mm.client_base + self.mm.dwLocalPlayerPawn)
            entity_id = self.mm.read_int(player + self.mm.m_iIDEntIndex)

            if entity_id > 0:
                entity = self.get_entity(entity_id)
                if entity:
                    return entity
            return None
        except Exception as e:
            if "Could not read memory at" in str(e):
                print("Game was updated, new offsets are required. Please wait for the offsets update.")
            else:
                print(f"Error in fire logic: {e}")
            return None

    def get_entity(self, index: int):
        """Retrieve an entity from the entity list."""
        if not self.mm.ent_list:
            return None
        try:
            # Use cached entity list pointer
            list_offset = 0x8 * (index >> 9)
            ent_entry = self.mm.read_longlong(self.mm.ent_list + list_offset + 0x10)
            entity_offset = ENTITY_ENTRY_SIZE * (index & 0x1FF)
            return self.mm.read_longlong(ent_entry + entity_offset)     #实体的pawnPtr
        except Exception as e:
            print(f"Error reading entity: {e}")
            return None


    def setAngle(
        self,
        player: Player,
        target_angle: Dict[str, float],
        sens: float = 1.0,
        threshold: float = 0.1,
        stop_event: Optional[threading.Event] = None,
        max_duration: float = 0.6,
        max_iterations: int = 500,
    ):
        """
        循环移动视角直到接近目标角度
        target_angle: {"x": pitch(上下), "y": yaw(水平)}
        sens: 灵敏度
        threshold: 停止阈值（角度差小于此值就停止）
        """
        start_time = time.time()
        iterations = 0

        while True:
            if stop_event is not None and stop_event.is_set():
                break
            if max_duration > 0 and (time.time() - start_time) >= max_duration:
                break
            if max_iterations > 0 and iterations >= max_iterations:
                break
            if not getattr(player, "pawnPtr", None):
                break
            iterations += 1

            # 当前角度
            angle = self.mm.read_vec2(
                player.pawnPtr + self.mm.m_angEyeAngles
            )

            # 计算差值
            dy = target_angle["y"] - angle["y"]  # 水平差值
            dx = target_angle["x"] - angle["x"]  # 垂直差值

            # 角度归一化（避免 180/-180 跳变）
            if dy > 180:
                dy -= 360
            elif dy < -180:
                dy += 360

            # 如果差值足够小，退出循环
            if abs(dx) < threshold and abs(dy) < threshold:
                break

            # 转换为鼠标输入（可调比例，避免过冲）
            mx = int(dy * -45.72 * 0.2 * sens)  # 水平
            my = int(dx * 45.71 * 0.2 * sens)  # 垂直

            # 最小移动限制（避免被截断为0导致卡死）
            if mx == 0 and abs(dy) > threshold:
                mx = 1 if dy > 0 else -1
            if my == 0 and abs(dx) > threshold:
                my = 1 if dx > 0 else -1

            # 执行一次鼠标移动
            Utility.move_once(mx, my)
            time.sleep(0.005)

    def update_entity_data(self, entity: Entity, player: Player,mapManager:MapManager) -> bool:
        """
        更新单个实体的数据。
        根据用户请求调整：
        """
        try:
            if not entity.pawnPtr:
                return False

            # 首先读取 GameSceneNode，因为多个字段需要它
            game_scene = self.mm.read_longlong(entity.pawnPtr + self.mm.m_pGameSceneNode)
            if not game_scene:
                entity.isCanShot = False
                return False


            entity.invincible = bool(self.mm.read_int(( entity.pawnPtr + self.mm.m_bHasMovedSinceSpawn)))

            # 如果无敌，跳过后续处理以节省资源
            if not entity.invincible:
                entity.isCanShot = False
                return True


            raw_name = self.mm.read_string(entity.localControllerPtr + self.mm.m_iszPlayerName)
            entity.name = Utility.transliterate(raw_name)
            
            entity.health = self.mm.read_int(entity.pawnPtr + self.mm.m_iHealth)
            entity.team = self.mm.read_int(entity.pawnPtr + self.mm.m_iTeamNum)
            
            # 使用 game_scene 计算骨骼位置
            bone_id = 6 if (entity.health >= 92 ) else 4
            entity.pos = self.bone_pos(bone_id, game_scene ,entity.pawnPtr)
                
            # 验证骨骼位置
            if entity.pos['x'] == 0 and entity.pos['y'] == 0 and entity.pos['z'] == 0:
                # 如果骨骼位置失败，回退到原点
                entity.pos = self.mm.read_vec3(entity.pawnPtr + self.mm.m_vOldOrigin)
            else:
                entity.pos['z'] = entity.pos.get('z', 0) - 64

            entity.angle = self.mm.read_vec2(entity.pawnPtr + self.mm.m_angEyeAngles)
            
            # 计算预测位置
            # x + cos(yaw) * 6, y + sin(yaw) * 6
            # 这稍微预测了他们将在哪里？
            yaw_rad = math.radians(entity.angle['y'])
            entity.pos['x'] = entity.pos.get('x', 0) + math.cos(yaw_rad) * 6
            entity.pos['y'] = entity.pos.get('y', 0) + math.sin(yaw_rad) * 6

            # 计算相对于本地玩家的瞄准角度和距离
            entity.canShoutAngle, distance = Utility.aimEnemy(player.pos, entity.pos)

            # 检查可见性/有效性
            # 注意：我们传递计算出的脚部位置。
            # 如果记录器需要头部位置，这可能是错误的。但完全遵循用户片段。
            entity.isCanShot = mapManager.can_shoot(player.pos, entity.pos)

            entity.weapon = self.get_weapon_type(entity.pawnPtr)

            if entity.health <= 0:
                entity.isCanShot = False

            return True
        except Exception as e:
            # print(f"Failed to update entity data: {e}")
            return False


    def get_all_entities(self, player: Player,mapManager:MapManager) -> List[Entity]:
        """
        扫描实体列表并返回有效实体对象的列表。
        """
        entities = []
        if not self.mm.client_base or not self.mm.dwEntityList:
            return entities

        try:
            ent_list_ptr = self.mm.read_longlong(self.mm.client_base + self.mm.dwEntityList)
            if not ent_list_ptr:
                return entities
            
            # 获取本地控制器指针以排除自身
            local_controller_ptr = self.mm.read_longlong(self.mm.client_base + self.mm.dwLocalPlayerController)



            for i in range(1, ENTITY_COUNT + 1):
                try:
                    list_index = (i & 0x7FFF) >> 9
                    entity_index = i & 0x1FF
                    
                    entry_ptr = self.mm.read_longlong(ent_list_ptr + (8 * list_index) + 16)
                    if not entry_ptr:
                        continue

                    controller_ptr = self.mm.read_longlong(entry_ptr + ENTITY_ENTRY_SIZE * entity_index)
                    if not controller_ptr:
                        continue
                        
                    if local_controller_ptr and controller_ptr == local_controller_ptr:
                        continue

                    # 使用 read_int 读取 pawn handle (4 bytes)，避免读取多余字节
                    controller_pawn_ptr = self.mm.read_int(
                        controller_ptr + self.mm.m_hPlayerPawn)
                    
                    if not controller_pawn_ptr:
                        continue

                    list_entry_ptr = self.mm.read_longlong(
                        ent_list_ptr + 8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                    if not list_entry_ptr:
                        continue

                    pawn_ptr = self.mm.read_longlong(
                        list_entry_ptr + ENTITY_ENTRY_SIZE * (controller_pawn_ptr & 0x1FF))
                    if not pawn_ptr:
                        continue

                    # 创建实体对象
                    entity = Entity()
                    entity.pawnPtr = pawn_ptr
                    entity.localControllerPtr = controller_ptr
                    entity.id = i-1  # 实体ID，用于唯一标识实体

                    # 更新实体数据
                    if self.update_entity_data(entity, player,mapManager):
                        entities.append(entity)
                except Exception as e:
                    # print(f"[IterateEntities] Loop error at index {i}: {e}")
                    continue

        except Exception as e:
            # print(f"Error getting entities: {e}")
            pass
            
        return entities

    def bone_pos(self, bone: int, game_scene: int = 0, pawn_ptr: int = 0) -> Dict[str, float]:
        try:
            if game_scene == 0:
                if pawn_ptr == 0:
                    return {"x": 0.0, "y": 0.0, "z": 0.0}
                game_scene = self.mm.read_longlong(pawn_ptr + self.mm.m_pGameSceneNode)

            if not game_scene:
                return {"x": 0.0, "y": 0.0, "z": 0.0}

            # 强制使用该项目验证过的偏移量逻辑
            # m_modelState = 0x160, + 0x80 = 0x1E0
            bone_array_ptr = self.mm.read_longlong(game_scene + 0x1E0)

            if not bone_array_ptr:
                return {"x": 0.0, "y": 0.0, "z": 0.0}

            return self.mm.read_vec3(bone_array_ptr + bone * 32)
        except Exception as e:
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def _get_entity_address(self, index: int) -> int:
        """从索引获取实体地址的辅助函数。"""
        try:
            list_offset = 0x8 * (index >> 9)
            ent_entry = self.mm.read_longlong(self.mm.ent_list + list_offset + 0x10)
            if not ent_entry: return 0
            
            entity_offset = 120 * (index & 0x1FF)
            return self.mm.read_longlong(ent_entry + entity_offset)
        except:
            return 0

    def _read_player_name(self, entity_pawn_addr: int) -> str:
        # 名字通常在 Controller 中，而不是 Pawn。
        # 这需要找到 Pawn 的控制器。
        # 为了简单起见，返回空或如果存在偏移量则实现
        return ""

    def get_weapon_type(self, pawn_addr: int) -> str:
        """
        确定 Pawn 持有的武器类型。
        """
        try:
            if not pawn_addr: return "Rifles"

            weapon_services_ptr = self.mm.read_longlong(pawn_addr + self.mm.m_pWeaponServices)
            if not weapon_services_ptr: return "Rifles"

            weapon_handle = self.mm.read_longlong(weapon_services_ptr + self.mm.m_hActiveWeapon)
            if not weapon_handle: return "Rifles"

            weapon_id = weapon_handle & 0xFFFF
            
            # 从句柄获取武器实体
            weapon_entity_ptr = self._get_entity_address(weapon_id)
            if not weapon_entity_ptr: return "Rifles"

            attribute_manager_ptr = self.mm.read_longlong(weapon_entity_ptr + self.mm.m_AttributeManager)
            if not attribute_manager_ptr: return "Rifles"

            item_ptr = self.mm.read_longlong(attribute_manager_ptr + self.mm.m_Item)
            if not item_ptr: return "Rifles"

            item_id = self.mm.read_int(item_ptr + self.mm.m_iItemDefinitionIndex)

            weapon_map = {
                1: "Pistols", 2: "Pistols", 3: "Pistols", 4: "Pistols", 30: "Pistols", 32: "Pistols", 36: "Pistols",
                61: "Pistols", 63: "Pistols", 64: "Pistols",
                7: "Rifles", 8: "Rifles", 10: "Rifles", 13: "Rifles", 16: "Rifles", 39: "Rifles", 60: "Rifles",
                9: "Snipers", 11: "Snipers", 38: "Snipers", 40: "Snipers",
                17: "SMGs", 19: "SMGs", 23: "SMGs", 24: "SMGs", 26: "SMGs", 33: "SMGs", 34: "SMGs",
                14: "Heavy", 25: "Heavy", 27: "Heavy", 28: "Heavy", 35: "Heavy"
            }
            return weapon_map.get(item_id, "Rifles")
        except Exception as e:
            return "Rifles"
