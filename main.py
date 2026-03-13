import time

from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain
from AutoKill.AutoMain import AutoKill

if __name__ == "__main__":

    time.sleep(3)

    cm = ControlMain()

    count = 0

    while True:
        mapName = cm.mapRecognition()
        autoKill = AutoKill()

        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")

        time.sleep(5)
        cm.chooseTeam()
        time.sleep(4)

        if count >=7:
            Utility.get_vk_code('k')    # 退出对局
        else:
            count = count + 1

        Utility.get_vk_code('j')

        autoKill.start(mapName)

        time.sleep(12)
        cm.chooseTeam()
        time.sleep(3)



