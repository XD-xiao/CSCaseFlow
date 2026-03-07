import time
import cv2

import pygetwindow as gw
import psutil
import os

import pyautogui

from skimage.metrics import structural_similarity as ssim



def screenshot_region(x, y, width, height, save_path):
    """
    截取屏幕指定区域并保存到固定位置。

    :param x: 左上角 X 坐标
    :param y: 左上角 Y 坐标
    :param width: 截图宽度
    :param height: 截图高度
    :param save_path: 保存路径（默认 screenshot.png）
    :return: 保存路径
    """
    # 路径前面加个文件夹
    save_path = os.path.join("screenshots/", save_path)

    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    screenshot.save(save_path)
    return save_path


def find_most_similar_image(folder_path, target_image_path):
    best_score = -1.0
    best_image_name = None
    target_image_path = os.path.join("screenshots/", target_image_path)
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".png"):
            img_path = os.path.join(folder_path, file_name)
            if os.path.isfile(img_path):  # 排除子文件夹
                try:
                    score = compare_images_ssim(target_image_path, img_path)
                    # print(f"比较 {file_name} -> {score}")
                    if score > best_score:
                        best_score = score
                        best_image_name = file_name
                except Exception as e:
                    print(f"跳过 {file_name}，原因：{e}")

    return best_image_name, best_score


def compare_images_ssim(img_path1, img_path2):
    img1 = cv2.imread(img_path1, 0)
    img2 = cv2.imread(img_path2, 0)

    if img1 is None or img2 is None:
        raise FileNotFoundError("其中一张图片无法加载")

    # 缩放到相同大小
    img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    # 计算结构相似度（范围 -1 ~ 1，1 表示完全相同）
    score, _ = ssim(img1, img2, full=True)
    return float(score)


def getWindowPosition(title):
    """
    获取窗口位置
    """
    # 获取所有窗口
    windows = gw.getAllWindows()

    for win in windows:
        if title in win.title:
            # print(f"窗口标题: {win.title}")
            # print(f"位置 (x, y): ({win.left}, {win.top})")
            # print(f"大小 (宽, 高): ({win.width}, {win.height})")
            return {
                "x": win.left,
                "y": win.top,
                "width": win.width,
                "height": win.height
            }
        # else:
        #     print(f"窗口:{win.title}")


def click_at(x, y):
    """
    点击指定坐标
    """
    # 暂时禁用 fail-safe，防止鼠标移动到角落触发异常
    pyautogui.FAILSAFE = False
    try:
        pyautogui.click(x, y)
    except Exception as e:
        print(f"点击失败: {e}")
    finally:
        # 恢复 fail-safe（可选，根据需求决定是否恢复）
        pyautogui.FAILSAFE = True


def is_process_running(name: str) -> bool:
    """判断进程是否在运行"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == name.lower():
            return True
    return False


