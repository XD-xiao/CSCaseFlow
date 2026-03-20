import os
import sys
import base64
import hashlib
import hmac
import json
import urllib.request
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from AutoKill.AutoMain import AutoKill
from AutoKill.Uitlity import Utility
from InterfaceControl.ControlMain import ControlMain
from Setting.Setting import ActivationToken, MAX_MATCH_COUNT, WaitTime


'''
模式选择
1:击杀模式,不使用可视学习功能
2:击杀模式,使用可视学习功能
3:训练模式,不自动击杀
4:训练模式,自动击杀
5.地图调试,调用mapRecognition,打印当前地图名称

'''
def verify() -> bool:
    token = (ActivationToken or "").strip()
    if not token:
        print("令牌为空")
        return False

    parts = token.split(".")
    if len(parts) != 3:
        print("令牌格式无效(非JWT)")
        return False

    header_b64, payload_b64, signature_b64 = parts
    try:
        header_raw = _b64url_decode(header_b64)
        header = json.loads(header_raw.decode("utf-8"))
        if not isinstance(header, dict):
            print("令牌头无效")
            return False
    except Exception:
        print("令牌头解析失败")
        return False

    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
        if not isinstance(payload, dict):
            print("令牌内容无效")
            return False
    except Exception:
        print("令牌解析失败")
        return False

    now_ts = _get_network_time_ts()
    if now_ts is None:
        print("无法获取网络时间")
        return False
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if isinstance(nbf, (int, float)) and now_ts < int(nbf):
        print("令牌未生效")
        return False
    if isinstance(exp, (int, float)) and now_ts >= int(exp):
        print("令牌已失效")
        return False
    if not isinstance(exp, (int, float)):
        print("令牌缺少exp，无法判断有效期")
        return False

    alg = header.get("alg")
    if alg != "HS256":
        print("令牌算法不支持")
        return False

    expected_signature_b64 = _jwt_hs256_signature_b64(
        header_b64=header_b64,
        payload_b64=payload_b64,
        secret="CSCaseFlow",
    )
    if not hmac.compare_digest(signature_b64, expected_signature_b64):
        print("令牌签名无效")
        return False

    return True


def _b64url_decode(data: str) -> bytes:
    padding_len = (-len(data)) % 4
    return base64.urlsafe_b64decode((data + ("=" * padding_len)).encode("utf-8"))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _jwt_hs256_signature_b64(header_b64: str, payload_b64: str, secret: str) -> str:
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url_encode(signature)


def _get_network_time_ts() -> Optional[int]:
    urls = (
        "https://www.baidu.com/",
        "https://www.sina.com.cn/",
        "https://www.qq.com/",
    )
    for url in urls:
        ts = _get_time_ts_from_http_date(url)
        if ts is not None:
            return ts
    return None


def _get_time_ts_from_http_date(url: str) -> Optional[int]:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(
                url,
                method=method,
                headers={"User-Agent": "CSCaseFlow/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                date_value = resp.headers.get("Date")
                if not date_value:
                    continue
                dt = parsedate_to_datetime(date_value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
        except Exception:
            continue
    return None


def game(mode: int) -> None:
    matchCount = 0

    cm = ControlMain()

    Utility.sleep_with_end(5)

    while True:
        Utility.exit_if_end_pressed()
        cm.chooseTeam()
        Utility.sleep_with_end(1)
        auto_kill = AutoKill()
        auto_kill.start(mode)
        print(f"当前对局结束,等待{WaitTime}秒后开始下一次对局")
        Utility.sleep_with_end(WaitTime)
        if matchCount >= MAX_MATCH_COUNT:
            Utility.get_vk_code("k")  # 退出对局
            print("该服务器以多次对局,以自动退出程序")
            os._exit(0)
        matchCount += 1

def mapDebug() -> None:
    cm = ControlMain()
    
    for i in range(5):
        Utility.sleep_with_end(1)
        print(f"倒计时:{5-i}")

    mapName = cm.mapRecognition()
    print(f"当前地图名称：{mapName}")
    os._exit(0)


def _clear_console() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.flush()
        return
    os.system("cls" if os.name == "nt" else "clear")


def select_mode() -> int:
    options = (
        (1, "击杀模式,不使用可视学习功能"),
        (2, "击杀模式,使用可视学习功能"),
        (3, "训练模式,不自动击杀"),
        (4, "训练模式,自动击杀"),
        (5, "地图调试,识别地图名称"),
    )

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        _clear_console()
        print("模式选择:")
        for mode, desc in options:
            print(f"{mode}:{desc}")
        while True:
            raw = input("请输入模式：").strip()
            if raw.isdigit() and int(raw) in {m for m, _ in options}:
                return int(raw)
            print("输入无效，请重新输入")

    try:
        import msvcrt  # type: ignore
    except Exception:
        _clear_console()
        print("模式选择:")
        for mode, desc in options:
            print(f"{mode}:{desc}")
        while True:
            raw = input("请输入模式：").strip()
            if raw.isdigit() and int(raw) in {m for m, _ in options}:
                return int(raw)
            print("输入无效，请重新输入")

    index = 0
    while True:
        _clear_console()
        print("模式选择(↑↓/W-S 选择, Enter确认):")
        for i, (mode, desc) in enumerate(options):
            prefix = "> " if i == index else "  "
            print(f"{prefix}{mode}:{desc}")
        sys.stdout.flush()

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                index = (index - 1) % len(options)
            elif ch2 == "P":
                index = (index + 1) % len(options)
            continue
        if ch == "\x1b" and msvcrt.kbhit():
            ch2 = msvcrt.getwch()
            if ch2 == "[" and msvcrt.kbhit():
                ch3 = msvcrt.getwch()
                if ch3 == "A":
                    index = (index - 1) % len(options)
                    continue
                if ch3 == "B":
                    index = (index + 1) % len(options)
                    continue
        if ch == "\r":
            return options[index][0]
        if ch in ("w", "W", "k", "K"):
            index = (index - 1) % len(options)
            continue
        if ch in ("s", "S", "j", "J"):
            index = (index + 1) % len(options)
            continue
        if ch.isdigit():
            num = int(ch)
            for i, (mode, _) in enumerate(options):
                if mode == num:
                    index = i
                    return num


if __name__ == "__main__":
    if not verify():
        os._exit(1)

    print("令牌验证成功")
    mode = select_mode()

    if mode == 5:
        mapDebug()
    else:
        game(mode)

        

