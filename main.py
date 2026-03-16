import ctypes
import os
import time

from AutoKill.AutoMain import AutoKill
from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain

map_fail_count = 0
game_count = 0

def is_key_down(key_code: int) -> bool:
    return ctypes.windll.user32.GetAsyncKeyState(key_code) & 0x8000


def exit_if_end_pressed() -> None:
    if is_key_down(Utility.get_vk_code("end")):
        print("收到 END，正在退出程序...")
        os._exit(0)


def sleep_with_end(seconds: float, step: float = 0.05) -> None:
    end_time = time.time() + seconds
    while True:
        exit_if_end_pressed()
        remaining = end_time - time.time()
        if remaining <= 0:
            return
        time.sleep(min(step, remaining))


def game(cm: ControlMain) -> None:
    global map_fail_count

    cm.chooseTeam()
    sleep_with_end(2)

    map_name = cm.mapRecognition()
    print(f"==============================  当前地图：{map_name}  ==============================")
    if map_name is None:
        print("未识别地图，请检查是否进入对局")
        sleep_with_end(2)
        if map_fail_count >= 10:
            Utility.get_vk_code("k")  # 退出对局
            print("地图无法识别,已退出程序")
            os._exit(0)
        map_fail_count += 1
        return


    map_fail_count = 0
    auto_kill = AutoKill()
    auto_kill.start(map_name , False)
    sleep_with_end(20)


if __name__ == "__main__":
    sleep_with_end(2)

    cm = ControlMain()
    while True:
        exit_if_end_pressed()
        sleep_with_end(2)

        game(cm)

        if game_count >= 3:
            Utility.get_vk_code("k")  # 退出对局
            print("该服务器以多次对局,以自动退出程序")
            os._exit(0)
        game_count += 1

