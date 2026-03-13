import os
from typing import Dict, Optional
import math

import requests
import psutil
import sys
import pygetwindow as gw
import orjson
from packaging import version
import ctypes
import time

# --- Windows API 定义 ---
PUL = ctypes.POINTER(ctypes.c_ulong)


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]


class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]


SendInput = ctypes.windll.user32.SendInput

# --- 常量 ---
MOUSEEVENTF_MOVE = 0x0001  # 相对移动


class Utility:
    @staticmethod
    def fetch_offsets():
        """
        从本地文件加载偏移量数据。
        """
        try:
            # 获取当前文件所在目录 (AutoKill)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 获取项目根目录
            project_root = os.path.dirname(current_dir)
            # 构建 Offsets/output 的绝对路径
            base_dir = os.path.join(project_root, "Offsets", "output")
            
            with open(os.path.join(base_dir, "offsets.json"), "rb") as f:
                offset = orjson.loads(f.read())
            with open(os.path.join(base_dir, "client_dll.json"), "rb") as f:
                client = orjson.loads(f.read())
            with open(os.path.join(base_dir, "buttons.json"), "rb") as f:
                buttons = orjson.loads(f.read())
            return offset, client, buttons

        except FileNotFoundError as e:
            print(f"缺少本地文件: {e}")
            return None, None, None
        except orjson.JSONDecodeError as e:
            print(f"解析 JSON 失败: {e}")
            return None, None, None
        except Exception as e:
            print(f"加载偏移量时发生意外错误: {e}")
            return None, None, None

    @staticmethod
    def is_game_active():
        """使用 pygetwindow 检查游戏窗口是否处于活动状态。"""
        windows = gw.getWindowsWithTitle('Counter-Strike 2')
        return any(window.isActive for window in windows)

    @staticmethod
    def is_game_running():
        """使用 psutil 检查游戏进程是否正在运行。"""
        return any(proc.info['name'] == 'cs2.exe' for proc in psutil.process_iter(attrs=['name']))

    @staticmethod
    def extract_offsets() -> dict | None:
        """
        从本地 JSON 文件加载并提取内存偏移量。
        """
        try:
            # 获取当前文件所在目录 (AutoKill)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 获取项目根目录
            project_root = os.path.dirname(current_dir)
            # 构建 Offsets/output 的绝对路径
            base_dir = os.path.join(project_root, "Offsets", "output")

            # 本地文件路径
            offsets_path = os.path.join(base_dir, "offsets.json")
            client_path = os.path.join(base_dir, "client_dll.json")
            buttons_path = os.path.join(base_dir, "buttons.json")

            # 加载 JSON 文件
            with open(offsets_path, "rb") as f:
                offsets = orjson.loads(f.read())
            with open(client_path, "rb") as f:
                client_data = orjson.loads(f.read())
            with open(buttons_path, "rb") as f:
                buttons_data = orjson.loads(f.read())

            # 提取相关字段
            client = offsets.get("client.dll", {})
            buttons = buttons_data.get("client.dll", {})
            classes = client_data.get("client.dll", {}).get("classes", {})

            def get_field(class_name, field_name):
                """递归获取字段值"""
                class_info = classes.get(class_name)
                if not class_info:
                    raise KeyError(f"Class '{class_name}' not found")

                field = class_info.get("fields", {}).get(field_name)
                if field is not None:
                    return field

                parent_class_name = class_info.get("parent")
                if parent_class_name:
                    return get_field(parent_class_name, field_name)

                raise KeyError(f"'{field_name}' not found in '{class_name}' or its parents")

            extracted_offsets = {
                "dwEntityList": client.get("dwEntityList"),
                "dwLocalPlayerPawn": client.get("dwLocalPlayerPawn"),
                "dwLocalPlayerController": client.get("dwLocalPlayerController"),
                "dwViewAngles": client.get("dwViewAngles"),
                "dwViewMatrix": client.get("dwViewMatrix"),
                "dwGameRules": client.get("dwGameRules"),

                "dwForceJump": buttons.get("jump"),
                "m_iHealth": get_field("C_BaseEntity", "m_iHealth"),
                "m_iTeamNum": get_field("C_BaseEntity", "m_iTeamNum"),
                "m_pGameSceneNode": get_field("C_BaseEntity", "m_pGameSceneNode"),
                "m_vOldOrigin": get_field("C_BasePlayerPawn", "m_vOldOrigin"),
                "m_pWeaponServices": get_field("C_BasePlayerPawn", "m_pWeaponServices"),
                "m_iIDEntIndex": get_field("C_CSPlayerPawn", "m_iIDEntIndex"),
                "m_flFlashDuration": get_field("C_CSPlayerPawn", "m_flFlashDuration"),
                "m_pClippingWeapon": get_field("C_CSPlayerPawn", "m_pClippingWeapon"),
                "m_angEyeAngles": get_field("C_CSPlayerPawn", "m_angEyeAngles"),
                "m_hPlayerPawn": get_field("CCSPlayerController", "m_hPlayerPawn"),
                "m_iszPlayerName": get_field("CBasePlayerController", "m_iszPlayerName"),
                "m_hActiveWeapon": get_field("CPlayer_WeaponServices", "m_hActiveWeapon"),
                "m_bDormant": get_field("CGameSceneNode", "m_bDormant"),
                "m_AttributeManager": get_field("C_EconEntity", "m_AttributeManager"),
                "m_Item": get_field("C_AttributeContainer", "m_Item"),
                "m_iItemDefinitionIndex": get_field("C_EconItemView", "m_iItemDefinitionIndex"),
                "m_pBoneArray": 528,  # 手动定义的 offset，通常是固定值

                "m_gamePhase": get_field("C_CSGameRules", "m_gamePhase"),
                "m_iRoundTime": get_field("C_CSGameRules", "m_iRoundTime"),
                "m_bHasMovedSinceSpawn":get_field("C_CSPlayerPawnBase" , "m_bHasMovedSinceSpawn"),

                "m_entitySpottedState": get_field("C_CSPlayerPawn", "m_entitySpottedState"),
                "m_bSpotted": get_field("EntitySpottedState_t", "m_bSpotted"),
                "m_bSpottedByMask":get_field("EntitySpottedState_t", "m_bSpottedByMask"),

            }

            missing_keys = [k for k, v in extracted_offsets.items() if v is None]
            if missing_keys:
                print(f"Offset initialization error: Missing keys: {missing_keys}")
                return None

            return extracted_offsets

        except FileNotFoundError as e:
            print(f"Missing local file: {e}")
            return None
        except orjson.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None
        except KeyError as e:
            print(f"Offset initialization error: Missing key {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    @staticmethod
    def get_vk_code(key: str) -> int:
        """将键字符串转换为对应的虚拟键代码。"""
        key = key.lower()
        vk_codes = {
            # 鼠标按键
            "mouse1": 0x01,  # 鼠标左键
            "mouse2": 0x02,  # 鼠标右键
            "mouse3": 0x04,  # 鼠标中键
            "mouse4": 0x05,  # 鼠标侧键1
            "mouse5": 0x06,  # 鼠标侧键2
            # 常用键盘按键
            "space": 0x20,  # 空格键
            "enter": 0x0D,  # 回车键
            "shift": 0x10,  # Shift键
            "ctrl": 0x11,  # Ctrl键
            "alt": 0x12,  # Alt键
            "tab": 0x09,  # Tab键
            "backspace": 0x08,  # 退格键
            "esc": 0x1B,  # Esc键
            # 字母按键
            "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46,
            "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C,
            "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52,
            "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
            "y": 0x59, "z": 0x5A,
            # 数字按键
            "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
            "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
            # 功能键
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
            "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
            "f11": 0x7A, "f12": 0x7B,
            # 控制键
            "insert": 0x2D, "home": 0x24, "pageup": 0x21, "delete": 0x2E,
            "end": 0x23, "pagedown": 0x22
        }
        return vk_codes.get(key, 0x20)  # 默认为空格键

    @staticmethod
    def aimEnemy(myPos: dict, enemyHeadPos: dict):
        # 计算向量差
        dx = enemyHeadPos["x"] - myPos["x"]
        dy = enemyHeadPos["y"] - myPos["y"]
        dz = enemyHeadPos["z"] - myPos["z"]

        # 总距离（三维欧几里得距离）
        distance_total = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

        # 计算角度
        horizontal_angle = math.degrees(math.atan2(dy, dx))  # yaw: -180 ~ 180
        vertical_angle = math.degrees(math.atan2(-dz, math.hypot(dx, dy)))  # pitch: 90 ~ -90

        angle = {
            "x": round(vertical_angle, 2),  # pitch（垂直角）
            "y": round(horizontal_angle, 2)  # yaw（水平角）
        }

        distance = round(distance_total, 2)

        return angle, distance

    @staticmethod
    def move_once(dx: int, dy: int):
        """底层单次相对移动"""
        mi = MouseInput(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
        input_event = Input(ctypes.c_ulong(0), Input_I(mi))
        SendInput(1, ctypes.byref(input_event), ctypes.sizeof(input_event))

    @staticmethod
    def move(
        yaw: float,
        pitch: float,
        sens: float,
        step: int = 30,
        delay: float = 0.00001,
        stop_event: Optional[object] = None,
    ):
        """
        按角度移动视角（自动换算成鼠标输入，并分步发送）
        yaw: 水平角度 (+右, -左)
        pitch: 垂直角度 (+下, -上)
        sens: CS2 游戏内灵敏度
        step: 每次最大移动像素（防止过大无效）
        delay: 每步之间的延时 (秒)
        """
        # 角度 -> 鼠标 counts
        dx = int(yaw * -45.72)
        dy = int(pitch * 45.71)

        # 分步移动
        steps = max(abs(dx), abs(dy)) // step + 1
        stepx = dx / steps
        stepy = dy / steps

        for _ in range(steps):
            if stop_event is not None and stop_event.is_set():
                break
            Utility.move_once(int(stepx), int(stepy))
            if delay > 0:
                time.sleep(delay)

    @staticmethod
    def transliterate(text: str) -> str:
        """将给定文本中的西里尔字符转换为对应的拉丁字符。"""
        mapping = {
            'А': 'A', 'а': 'a',
            'Б': 'B', 'б': 'b',
            'В': 'V', 'в': 'v',
            'Г': 'G', 'г': 'g',
            'Д': 'D', 'д': 'd',
            'Е': 'E', 'е': 'e',
            'Ё': 'Yo', 'ё': 'yo',
            'Ж': 'Zh', 'ж': 'zh',
            'З': 'Z', 'з': 'z',
            'И': 'I', 'и': 'i',
            'Й': 'I', 'й': 'i',
            'К': 'K', 'к': 'k',
            'Л': 'L', 'л': 'l',
            'М': 'M', 'м': 'm',
            'Н': 'N', 'н': 'n',
            'О': 'O', 'о': 'o',
            'П': 'P', 'п': 'p',
            'Р': 'R', 'р': 'r',
            'С': 'S', 'с': 's',
            'Т': 'T', 'т': 't',
            'У': 'U', 'у': 'u',
            'Ф': 'F', 'ф': 'f',
            'Х': 'Kh', 'х': 'kh',
            'Ц': 'Ts', 'ц': 'ts',
            'Ч': 'Ch', 'ч': 'ch',
            'Ш': 'Sh', 'ш': 'sh',
            'Щ': 'Shch', 'щ': 'shch',
            'Ъ': '', 'ъ': '',
            'Ы': 'Y', 'ы': 'y',
            'Ь': '', 'ь': '',
            'Э': 'E', 'э': 'e',
            'Ю': 'Yu', 'ю': 'yu',
            'Я': 'Ya', 'я': 'ya'
        }
        return "".join(mapping.get(char, char) for char in text)
