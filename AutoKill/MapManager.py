import json
import os
import math
import winsound
import time
from typing import Dict, Tuple, Set, List

class MapManager:
    def __init__(self, mapName: str):
        self.mapName = mapName
        self.grid_size = 64
        self.data: Set[Tuple[int, int, int]] = set()
        
        # 设置路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.map_data_dir = os.path.join(project_root, "mapData")
        self.file_path = os.path.join(self.map_data_dir, f"{mapName}.json")
        
        # 确保目录存在
        if not os.path.exists(self.map_data_dir):
            try:
                os.makedirs(self.map_data_dir)
            except Exception as e:
                print(f"创建地图目录失败: {e}")
        
        # 加载数据
        self._load_data()
        
        # 自动保存计时
        self.last_save_time = time.time()
        self.save_interval = 10  # 秒

    def _load_data(self):
        """从JSON文件加载数据，如果不存在则创建空数据"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                    # 将列表转换为集合，元素转为元组以便哈希
                    self.data = set(tuple(p) for p in data_list)
                print(f"地图数据已加载: {len(self.data)} 个坐标点")
            except Exception as e:
                print(f"加载地图数据失败: {e}")
                self.data = set()
        else:
            print("未找到地图文件，将创建新地图")
            self.data = set()
            self.save_data()

    def save_data(self):
        """将数据保存到JSON文件 (手动调用)"""
        try:
            print(f"正在保存地图数据... ({len(self.data)} 个点)")
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # 集合转列表以便JSON序列化
                json.dump(list(self.data), f)
            print("地图数据保存成功")
        except Exception as e:
            print(f"保存地图数据失败: {e}")

    def _to_grid(self, pos: Dict[str, float]) -> Tuple[int, int, int]:
        """将世界坐标转换为网格坐标"""
        return (
            int(pos['x'] // self.grid_size),
            int(pos['y'] // self.grid_size),
            int(pos['z'] // self.grid_size)
        )

    def add_walkable(self, pos: Dict[str, float]):
        """
        添加坐标数据
        如果坐标是新的，则添加并播放提示音
        注意：不再自动保存，需手动调用 save_data()
        """
        grid_pos = self._to_grid(pos)
        
        if grid_pos not in self.data:
            self.data.add(grid_pos)
            
            # 播放提示音
            try:
                winsound.Beep(800, 500)
            except:
                pass
            
            # 自动保存检查
            if time.time() - self.last_save_time > self.save_interval:
                self.save_data()
                self.last_save_time = time.time()


    def add_walkable_path(self, start_pos: Dict[str, float], end_pos: Dict[str, float]):
        """
        添加两点及其连线路径上的所有坐标到数据集
        """
        p1 = self._to_grid(start_pos)
        p2 = self._to_grid(end_pos)
        
        # 获取路径上所有点
        points = self._bresenham_3d(p1[0], p1[1], p1[2], p2[0], p2[1], p2[2])
        
        # 将路径点以及起终点合并去重
        points_to_add = set(points)
        points_to_add.add(p1)
        points_to_add.add(p2)
        
        has_new = False
        for p in points_to_add:
            if p not in self.data:
                self.data.add(p)
                has_new = True
                
        if has_new:
            # 播放提示音
            try:
                winsound.Beep(800, 500)
            except:
                pass
            
            # 自动保存检查
            if time.time() - self.last_save_time > self.save_interval:
                self.save_data()
                self.last_save_time = time.time()

    def can_shoot(self, start_pos: Dict[str, float], end_pos: Dict[str, float]) -> bool:
        """
        判断两点之间是否可射击（路径上的点是否都在数据集中）
        """
        p1 = self._to_grid(start_pos)
        p2 = self._to_grid(end_pos)
        
        # 1. 检查起点和终点是否存在
        if p1 not in self.data or p2 not in self.data:
            return False
            
        # 2. 检查路径上的所有点
        return self._check_path(p1, p2)

    def _check_path(self, p1: Tuple[int, int, int], p2: Tuple[int, int, int]) -> bool:
        """使用3D Bresenham算法检查路径上的点是否存在"""
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        
        points = self._bresenham_3d(x1, y1, z1, x2, y2, z2)
        
        for p in points:
            if p not in self.data:
                return False
        return True

    def _bresenham_3d(self, x1, y1, z1, x2, y2, z2) -> List[Tuple[int, int, int]]:
        """生成两点之间的所有网格坐标点"""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)
        
        xs = 1 if x2 > x1 else -1
        ys = 1 if y2 > y1 else -1
        zs = 1 if z2 > z1 else -1

        # 确定主轴并进行步进
        if dx >= dy and dx >= dz:
            p1 = 2 * dy - dx
            p2 = 2 * dz - dx
            while x1 != x2:
                x1 += xs
                if p1 >= 0:
                    y1 += ys
                    p1 -= 2 * dx
                if p2 >= 0:
                    z1 += zs
                    p2 -= 2 * dx
                p1 += 2 * dy
                p2 += 2 * dz
                points.append((x1, y1, z1))
        elif dy >= dx and dy >= dz:
            p1 = 2 * dx - dy
            p2 = 2 * dz - dy
            while y1 != y2:
                y1 += ys
                if p1 >= 0:
                    x1 += xs
                    p1 -= 2 * dy
                if p2 >= 0:
                    z1 += zs
                    p2 -= 2 * dy
                p1 += 2 * dx
                p2 += 2 * dz
                points.append((x1, y1, z1))
        else:
            p1 = 2 * dy - dz
            p2 = 2 * dx - dz
            while z1 != z2:
                z1 += zs
                if p1 >= 0:
                    y1 += ys
                    p1 -= 2 * dz
                if p2 >= 0:
                    x1 += xs
                    p2 -= 2 * dz
                p1 += 2 * dy
                p2 += 2 * dx
                points.append((x1, y1, z1))
                
        return points
