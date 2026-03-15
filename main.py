import ctypes
import os
import time

from AutoKill.AutoMain import AutoKill
from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain


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
    count = 0

    while True:
        exit_if_end_pressed()

        map_name = cm.mapRecognition()
        auto_kill = AutoKill()

        banner = f"===============  当前地图：{map_name}  ==============="
        for _ in range(4):
            print(banner)

        sleep_with_end(5)
        cm.chooseTeam()
        sleep_with_end(4)

        if count >= 2:
            Utility.get_vk_code("k")  # 退出对局
            return None
        count += 1

        Utility.get_vk_code("j")
        auto_kill.start(map_name)

        sleep_with_end(12)
        cm.chooseTeam()
        sleep_with_end(3)


if __name__ == "__main__":
    sleep_with_end(3)

    cm = ControlMain()
    while True:
        exit_if_end_pressed()

        # cm.intoGame()

        game(cm)

