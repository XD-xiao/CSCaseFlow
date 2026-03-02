from InterfaceControl import ICUtility

CS2Title = "Counter-Strike 2"


class ControlMain:

    def __init__(self):
        self.currentMapName = None

    # 判断地图
    def mapRecognition(self):
        cs2Info = ICUtility.getWindowPosition(CS2Title)
        ICUtility.screenshot_region(cs2Info.get("x") + 12, cs2Info.get("y") + 40, 240, 240,
                                    "screenshot.png")
        imgName, similarity = ICUtility.find_most_similar_image("UiPic", "screenshot.png")
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

