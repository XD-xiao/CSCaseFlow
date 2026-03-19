import ctypes
import os
import time

from AutoKill.AutoMain import AutoKill
from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain

game_count = 0


def game(cm: ControlMain) -> None:


    cm.chooseTeam()
    Utility.sleep_with_end(2)
    auto_kill = AutoKill()
    auto_kill.start(1)
    Utility.sleep_with_end(20)


if __name__ == "__main__":
    Utility.sleep_with_end(2)

    cm = ControlMain()
    while True:
        Utility.exit_if_end_pressed()
        Utility.sleep_with_end(2)

        game(cm)

        if game_count >= 3:
            Utility.get_vk_code("k")  # 退出对局
            print("该服务器以多次对局,以自动退出程序")
            os._exit(0)
        game_count += 1

