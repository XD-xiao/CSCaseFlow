import time

from InterfaceControl.ControlMain import ControlMain
from AutoKill.Training import Training

if __name__ == "__main__":

    time.sleep(3)

    cm = ControlMain()
    mapName = cm.mapRecognition()

    print(f"===============  当前地图：{mapName}  ===============")

    i = input("输入'1'确认开始:")

    if i == "1":
        training = Training()
        training.start(mapName)



