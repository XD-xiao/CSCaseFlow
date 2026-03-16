
from InterfaceControl import ICUtility


CS2Title = "Counter-Strike 2"
CS2_PROCESS = "cs2.exe"

class ControlMain:

    def __init__(self):
        self.currentMapName = None

    # 判断地图
    def mapRecognition(self):
        cs2Info = ICUtility.getWindowPosition(CS2Title)
        ICUtility.screenshot_region(cs2Info.get("x") + 12, cs2Info.get("y") + 35, 251, 251,
                                    "screenshot.png")
        imgName, similarity = ICUtility.find_most_similar_image("UiPic/map", "screenshot.png", similarity_threshold=0.8)
        print(f"地图判断：{imgName}")
        if imgName == "Dust2-Map.png":
            self.currentMapName = "Dust2"
        elif imgName == "Mirage-Map.png":
            self.currentMapName = "Mirage"
        elif imgName == "Inferno-Map.png":
            self.currentMapName = "Inferno"
        elif imgName == "Vertigo-Map1.png" or imgName == "Vertigo-Map2.png":
            self.currentMapName = "Vertigo"
        else:
            self.currentMapName = None
        return self.currentMapName

    # 主页判断
    def homeRecognition(self):
        cs2Info = ICUtility.getWindowPosition(CS2Title)
        ICUtility.screenshot_region(cs2Info.get("x") + 1033, cs2Info.get("y") + 700, 200, 40,
                                    "screenshot.png")
        imgName, similarity = ICUtility.find_most_similar_image("UiPic/home", "screenshot.png", similarity_threshold=0.8)
        print(f"主页判断：{imgName}")
        if imgName is None:
            return None
        if imgName == "Home.png":
            return "主页"
        elif imgName == "match1.png":
            return "未匹配"
        elif imgName == "match2.png":
            return "匹配中"
        else:
            return "未知"


    def chooseTeam(self):
        try:
            cs2Info = ICUtility.getWindowPosition(CS2Title)
            if not cs2Info:
                print(f"未找到窗口: {CS2Title}")
                return

            target_x = cs2Info.get("x") + 700
            target_y = cs2Info.get("y") + 400
            
            # 增加对坐标的简单校验，防止无效坐标
            if target_x < 0 or target_y < 0:
                print(f"点击坐标异常: ({target_x}, {target_y})")
                return

            ICUtility.click_at(target_x, target_y)
        except Exception as e:
            print(f"选择队伍失败: {e}")






















