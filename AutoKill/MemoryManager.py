import pymem
import pymem.process
import struct

from AutoKill.Uitlity import Utility
from Setting.Setting import CS2_PROCESS_NAME


class MemoryManager:
    def __init__(self) -> None:
        """使用偏移量和客户端数据初始化 MemoryManager。"""

        self.pm = None
        self.client_base = None
        self.ent_list = None  # 实体列表指针缓存
        # 偏移量属性
        self.dwEntityList = None
        self.dwLocalPlayerPawn = None
        self.dwLocalPlayerController = None
        self.dwViewAngles = None
        self.m_angEyeAngles = None
        self.m_iHealth = None
        self.m_iTeamNum = None
        self.m_iIDEntIndex = None
        self.m_iszPlayerName = None
        self.m_vOldOrigin = None
        self.m_pGameSceneNode = None
        self.m_hPlayerPawn = None
        self.m_bHasMovedSinceSpawn = None
        self.m_entitySpottedState = None
        self.m_bSpotted = None
        self.m_bSpottedByMask = None


    def initialize(self) -> bool:
        """
        通过附加到进程并设置必要的数据来初始化内存访问。
        如果成功返回 True，否则返回 False。
        """
        # 检查 pymem 是否已初始化且已获取客户端模块
        if not self.initialize_pymem() or not self.get_client_module():
            return False
        # 缓存实体列表指针
        self.load_offsets()
        if self.dwEntityList is None:  # 确保偏移量已成功加载
            return False
        self.ent_list = self.read_longlong(self.client_base + self.dwEntityList)
        if self.ent_list == 0:
            print("读取实体列表指针失败。偏移量可能已过期或游戏尚未准备好。")
            return False
        return True

    def initialize_pymem(self) -> bool:
        """将 pymem 附加到游戏进程。"""
        try:
            self.pm = pymem.Pymem(CS2_PROCESS_NAME)
            print(f"成功附加到 {CS2_PROCESS_NAME} 进程。")
            return True
        except pymem.exception.ProcessNotFound:
            print(f"未找到 {CS2_PROCESS_NAME} 进程。请确保游戏正在运行。")
            return False
        except Exception as e:
            print(f"附加到 {CS2_PROCESS_NAME} 时发生意外错误: {e}")
            return False

    def get_client_module(self) -> bool:
        """获取 client.dll 模块基地址。"""
        try:
            # 尝试获取 client.dll 模块
            client_module = pymem.process.module_from_name(self.pm.process_handle, "client.dll")
            self.client_base = client_module.lpBaseOfDll
            print("已找到 client.dll 模块并获取基地址。")
            return True
        except pymem.exception.ModuleNotFoundError:
            # 如果未找到模块，记录错误
            print("未找到 client.dll。请确保它已加载。")
            return False
        except Exception as e:
            # 记录可能发生的任何其他异常
            print(f"获取 client.dll 模块时发生意外错误: {e}")
            return False

    def load_offsets(self) -> None:
        """从 Utility.extract_offsets 加载内存偏移量。"""
        extracted = Utility.extract_offsets()
        if extracted:
            self.dwEntityList = extracted["dwEntityList"]
            self.dwLocalPlayerPawn = extracted["dwLocalPlayerPawn"]
            self.dwLocalPlayerController = extracted["dwLocalPlayerController"]
            self.dwViewAngles = extracted["dwViewAngles"]
            self.m_iHealth = extracted["m_iHealth"]
            self.m_iTeamNum = extracted["m_iTeamNum"]
            self.m_iIDEntIndex = extracted["m_iIDEntIndex"]
            self.m_iszPlayerName = extracted["m_iszPlayerName"]
            self.m_vOldOrigin = extracted["m_vOldOrigin"]
            self.m_pGameSceneNode = extracted["m_pGameSceneNode"]
            self.m_angEyeAngles = extracted["m_angEyeAngles"]
            self.m_hPlayerPawn = extracted["m_hPlayerPawn"]
            self.m_bHasMovedSinceSpawn = extracted["m_bHasMovedSinceSpawn"]
            self.m_entitySpottedState = extracted["m_entitySpottedState"]
            self.m_bSpotted = extracted["m_bSpotted"]
            self.m_bSpottedByMask = extracted["m_bSpottedByMask"]

        else:
            print("从提取的数据初始化偏移量失败。")


    def read_vec2(self, address: int) -> dict | None:
        """"""
        try:
            return {
                "x": self.pm.read_float(address),
                "y": self.pm.read_float(address + 4)
            }
        except Exception as e:
            print(f"读取地址 {hex(address)} 处的 vec2 失败: {e}")
            return {"x": 200.0, "y": 200.0}

    def write_vec2(self, address: int = None, vec: dict = None) -> None:
        """
        将 2D 向量（两个浮点数）写入指定地址的内存。
        """
        try:
            self.pm.write_float(address, vec["x"])
            self.pm.write_float(address + 4, vec["y"])
        except Exception as e:
            print(f"写入地址 {hex(address)} 处的 vec2 失败: {e}")
            raise

    def read_vec3(self, address: int) -> dict | None:
        """
        从指定地址的内存中读取 3D 向量（三个浮点数）。
        """
        try:
            return {
                "x": self.pm.read_float(address),
                "y": self.pm.read_float(address + 4),
                "z": self.pm.read_float(address + 8)
            }
        except Exception as e:
            # print(f"读取地址 {hex(address)} 处的 vec3 失败: {e}")
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def read_string(self, address: int, max_length: int = 256) -> str:
        """
        从指定地址的内存中读取以空字符结尾的字符串。
        """
        try:
            data = self.pm.read_bytes(address, max_length)
            string_data = data.split(b'\x00')[0]
            return string_data.decode('utf-8', errors='replace')
        except Exception as e:
            # print(f"读取地址 {hex(address)} 处的字符串失败: {e}")
            return ""

    def read_floats(self, address: int, count: int) -> list[float]:
        """
        从内存中读取 `count` 个浮点数的数组。
        """
        try:
            data = self.pm.read_bytes(address, count * 4)
            return list(struct.unpack(f'{count}f', data))
        except Exception as e:
            # print(f"读取地址 {hex(address)} 处的 {count} 个浮点数失败: {e}")
            return []

    def read_uint32s(self, address: int, count: int) -> list[int]:
        try:
            data = self.pm.read_bytes(address, count * 4)
            return list(struct.unpack(f"<{count}I", data))
        except Exception:
            return [0] * count

    def read_int(self, address: int) -> int:
        """从内存中读取整数。"""
        try:
            return self.pm.read_int(address)
        except Exception as e:
            # print(f"读取地址 {hex(address)} 处的整数失败: {e}")
            return 0

    def read_longlong(self, address: int) -> int:
        """从内存中读取长长整型。"""
        try:
            return self.pm.read_longlong(address)
        except Exception as e:
            # print(f"读取地址 {hex(address)} 处的长长整型失败: {e}")
            return 0

    @property
    def client_dll_base(self) -> int:
        """获取 client.dll 的基地址。"""
        return self.client_base
