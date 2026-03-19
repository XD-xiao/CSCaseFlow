
import os

from InterfaceControl import ICUtility
from Setting.Setting import (
    CHOOSE_TEAM_OFFSET_X,
    CHOOSE_TEAM_OFFSET_Y,
    CS2_TITLE,
    MAP_IMAGE_DIR,
    MAP_SCREENSHOT_HEIGHT,
    MAP_SCREENSHOT_OFFSET_X,
    MAP_SCREENSHOT_OFFSET_Y,
    MAP_SCREENSHOT_PATH,
    MAP_SCREENSHOT_WIDTH,
    MAP_SIMILARITY_THRESHOLD,
)


class ControlMain:

    def __init__(self):
        self.currentMapName = None

    # 判断地图
    def mapRecognition(self):
        cs2Info = ICUtility.getWindowPosition(CS2_TITLE)
        ICUtility.screenshot_region(
            cs2Info.get("x") + MAP_SCREENSHOT_OFFSET_X,
            cs2Info.get("y") + MAP_SCREENSHOT_OFFSET_Y,
            MAP_SCREENSHOT_WIDTH,
            MAP_SCREENSHOT_HEIGHT,
            MAP_SCREENSHOT_PATH,
        )
        imgName, similarity = ICUtility.find_most_similar_image(
            MAP_IMAGE_DIR,
            MAP_SCREENSHOT_PATH,
            similarity_threshold=MAP_SIMILARITY_THRESHOLD,
        )
        print(f"地图判断：{imgName}")
        self.currentMapName = self._extractMapName(imgName)
        return self.currentMapName

    def _extractMapName(self, imgName):
        if not imgName:
            return None

        fileName = os.path.basename(imgName)
        stem, ext = os.path.splitext(fileName)
        if not stem:
            return None

        left, sep, right = stem.rpartition("-")
        if sep and right.isdigit() and left:
            return left
        return stem


    def chooseTeam(self):
        try:
            cs2Info = ICUtility.getWindowPosition(CS2_TITLE)
            if not cs2Info:
                print(f"未找到窗口: {CS2_TITLE}")
                return

            target_x = cs2Info.get("x") + CHOOSE_TEAM_OFFSET_X
            target_y = cs2Info.get("y") + CHOOSE_TEAM_OFFSET_Y
            
            # 增加对坐标的简单校验，防止无效坐标
            if target_x < 0 or target_y < 0:
                print(f"点击坐标异常: ({target_x}, {target_y})")
                return

            ICUtility.click_at(target_x, target_y)
        except Exception as e:
            print(f"选择队伍失败: {e}")






















