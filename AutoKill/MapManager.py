import os
import math
import winsound
import time
import threading
import pickle
from typing import Dict, Tuple, Set, List, Iterator

from Setting.Setting import MAP_AUTO_SAVE_INTERVAL_SEC, MAP_DATA_DIR_NAME, MAP_DATA_FILE_EXT, MAP_GRID_SIZE

class MapManager:
    def __init__(self, mapName: str):
        self.mapName = mapName
        self._data_lock = threading.RLock()
        self.grid_size = MAP_GRID_SIZE
        self.data: Set[Tuple[int, int, int]] = set()
        
        # 设置路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.map_data_dir = os.path.join(project_root, MAP_DATA_DIR_NAME)
        self.file_path = os.path.join(self.map_data_dir, f"{mapName}.{MAP_DATA_FILE_EXT}")
        
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
        self.save_interval = MAP_AUTO_SAVE_INTERVAL_SEC

    def _play_beep(self):
        """异步播放提示音，避免阻塞主线程"""
        def beep():
            try:
                winsound.Beep(800, 500)
            except:
                pass
        threading.Thread(target=beep, daemon=True).start()

    def _load_data(self):
        """从pickle文件加载数据，如果不存在则创建空数据"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "rb") as f:
                    loaded = pickle.load(f)
                    if isinstance(loaded, set):
                        data_set = loaded
                    else:
                        data_set = set(tuple(p) for p in loaded)
                with self._data_lock:
                    self.data = data_set
                    data_count = len(self.data)
                print(f"地图数据已加载: {data_count} 个坐标点")
            except Exception as e:
                print(f"加载地图数据失败: {e}")
                with self._data_lock:
                    self.data = set()
        else:
            print("未找到地图文件，将创建新地图")
            with self._data_lock:
                self.data = set()
            self.save_data()

    def save_data(self):
        """将数据保存到pickle文件 (手动调用)"""
        try:
            with self._data_lock:
                data_snapshot = set(self.data)
            print(f"正在保存地图数据... ({len(data_snapshot)} 个点)")
            tmp_path = f"{self.file_path}.tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump(data_snapshot, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp_path, self.file_path)
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

        added = False
        with self._data_lock:
            if grid_pos not in self.data:
                self.data.add(grid_pos)
                added = True

        if not added:
            return

        self._play_beep()

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
        with self._data_lock:
            for p in points_to_add:
                if p not in self.data:
                    self.data.add(p)
                    has_new = True
                
        if has_new:
            # 播放提示音 (异步)
            self._play_beep()
            
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

        with self._data_lock:
            if p1 not in self.data or p2 not in self.data:
                return False
            return self._check_path(p1, p2)

    def _check_path(self, p1: Tuple[int, int, int], p2: Tuple[int, int, int]) -> bool:
        """使用3D Bresenham算法检查路径上的点是否存在"""
        x1, y1, z1 = p1
        x2, y2, z2 = p2

        for p in self._iter_bresenham_3d(x1, y1, z1, x2, y2, z2):
            if p not in self.data:
                return False
        return True

    def _iter_bresenham_3d(self, x1, y1, z1, x2, y2, z2) -> Iterator[Tuple[int, int, int]]:
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)

        xs = 1 if x2 > x1 else -1
        ys = 1 if y2 > y1 else -1
        zs = 1 if z2 > z1 else -1

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
                yield (x1, y1, z1)
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
                yield (x1, y1, z1)
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
                yield (x1, y1, z1)

    def _bresenham_3d(self, x1, y1, z1, x2, y2, z2) -> List[Tuple[int, int, int]]:
        """生成两点之间的所有网格坐标点"""
        return list(self._iter_bresenham_3d(x1, y1, z1, x2, y2, z2))
