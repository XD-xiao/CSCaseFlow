import time

from InterfaceControl.ControlMain import ControlMain
from AutoKill.AutoMain import AutoKill

if __name__ == "__main__":

    time.sleep(3)

    cm = ControlMain()

    while True:
        mapName = cm.mapRecognition()
        autoKill = AutoKill()

        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")
        print(f"===============  当前地图：{mapName}  ===============")

        time.sleep(5)


        autoKill.start(mapName)

        time.sleep(12)
        # cm.chooseTeam()
        time.sleep(3)



