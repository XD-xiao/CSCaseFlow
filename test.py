import argparse
import ctypes
import os
import re
import time
from dataclasses import dataclass
from enum import Enum

input_file = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"


class ConsoleState(str, Enum):
    LOBBY = "lobby"
    IN_GAME = "in_game"
    MATCHMAKING = "matchmaking"
    MATCHMAKING_CANCELLED = "matchmaking_cancelled"


@dataclass(frozen=True)
class ConsoleStateMatch:
    state: ConsoleState
    state_text: str
    matched_line: str
    matched_at: float


_LOBBY_RE = re.compile(
    r"\bsetpos\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?;setang\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\b"
)
_IN_GAME_MARK = "[Console] SV: Cheat command 'getpos' ignored."
_MM_1_MARK = "[Developer] Matchmaking update: 1"
_MM_0_MARK = "[Developer] Matchmaking update: 0"
_LOBBY_HINTS = ("setpos", "setang")


def _press_key_once(key: str, hold_seconds: float = 0.03) -> None:
    from AutoKill.Uitlity import Utility

    vk_code = Utility.get_vk_code(key)
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    if hold_seconds > 0:
        time.sleep(hold_seconds)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


def _match_console_state(line: str) -> tuple[ConsoleState, str] | None:
    if _MM_1_MARK in line:
        return ConsoleState.MATCHMAKING, "正在匹配"
    if _MM_0_MARK in line:
        return ConsoleState.MATCHMAKING_CANCELLED, "取消匹配"
    if _IN_GAME_MARK in line:
        return ConsoleState.IN_GAME, "对局中"
    if _LOBBY_RE.search(line) is not None:
        return ConsoleState.LOBBY, "大厅"
    return None


def _extract_line_around(text: str, index: int) -> str:
    if index < 0:
        return ""
    left = text.rfind("\n", 0, index)
    right = text.find("\n", index)
    if left == -1:
        left = 0
    else:
        left += 1
    if right == -1:
        right = len(text)
    return text[left:right].strip("\r")


def _scan_tail_for_match(
    file_path: str,
    tail_bytes: int,
    preferred_encoding: str,
) -> tuple[ConsoleState, str, str] | None:
    try:
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        return None

    start_offset = max(0, file_size - max(0, tail_bytes))
    if start_offset % 2 == 1:
        start_offset -= 1

    with open(file_path, "rb") as f:
        if start_offset:
            f.seek(start_offset)
        data = f.read()

    markers = (
        (_MM_1_MARK, ConsoleState.MATCHMAKING, "正在匹配"),
        (_MM_0_MARK, ConsoleState.MATCHMAKING_CANCELLED, "取消匹配"),
        (_IN_GAME_MARK, ConsoleState.IN_GAME, "对局中"),
    )

    candidates: list[tuple[int, str, ConsoleState, str, str]] = []

    encodings_to_try = [preferred_encoding]
    if preferred_encoding != "utf-8":
        encodings_to_try.append("utf-8")
    if preferred_encoding != "utf-16-le":
        encodings_to_try.append("utf-16-le")

    for enc in encodings_to_try:
        for marker, state, state_text in markers:
            try:
                marker_bytes = marker.encode(enc, errors="ignore")
            except LookupError:
                continue
            if not marker_bytes:
                continue
            idx = data.rfind(marker_bytes)
            if idx != -1:
                try:
                    text = data.decode(enc, errors="ignore")
                except LookupError:
                    continue
                marker_idx = text.rfind(marker)
                line = _extract_line_around(text, marker_idx)
                candidates.append((idx, enc, state, state_text, line))

        for hint in _LOBBY_HINTS:
            try:
                hint_bytes = hint.encode(enc, errors="ignore")
            except LookupError:
                continue
            idx = data.rfind(hint_bytes) if hint_bytes else -1
            if idx != -1:
                try:
                    text = data.decode(enc, errors="ignore")
                except LookupError:
                    continue
                marker_idx = max(text.rfind(_LOBBY_HINTS[0]), text.rfind(_LOBBY_HINTS[1]))
                line = _extract_line_around(text, marker_idx)
                matched = _match_console_state(line)
                if matched is not None:
                    state, state_text = matched
                    candidates.append((idx, enc, state, state_text, line))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, _, state, state_text, line = candidates[0]
    return state, state_text, line


def wait_console_state(
    file_path: str = input_file,
    poll_interval_seconds: float = 0.5,
    timeout_seconds: float | None = None,
    press_o_before_read: bool = True,
    initial_read_back_bytes: int = 65536,
    encoding: str = "utf-8",
) -> ConsoleStateMatch | None:
    start_time = time.time()

    def timed_out() -> bool:
        return timeout_seconds is not None and (time.time() - start_time) >= timeout_seconds
    if encoding == "auto":
        preferred_encoding = "utf-8"
    else:
        preferred_encoding = encoding

    while True:
        if timed_out():
            return None

        if press_o_before_read:
            _press_key_once("o")
            time.sleep(0.05)

        found = _scan_tail_for_match(
            file_path=file_path,
            tail_bytes=initial_read_back_bytes,
            preferred_encoding=preferred_encoding,
        )
        if found is not None:
            state, state_text, line = found
            return ConsoleStateMatch(
                state=state,
                state_text=state_text,
                matched_line=line,
                matched_at=time.time(),
            )

        time.sleep(poll_interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", dest="file_path", default=input_file)
    parser.add_argument("--timeout", dest="timeout_seconds", type=float, default=None)
    parser.add_argument("--poll", dest="poll_interval_seconds", type=float, default=0.5)
    parser.add_argument("--no-press-o", dest="no_press_o", action="store_true")
    parser.add_argument("--back-bytes", dest="initial_read_back_bytes", type=int, default=65536)
    parser.add_argument("--encoding", dest="encoding", default="utf-8")
    args = parser.parse_args()

    try:
        result = wait_console_state(
            file_path=args.file_path,
            poll_interval_seconds=args.poll_interval_seconds,
            timeout_seconds=args.timeout_seconds,
            press_o_before_read=not args.no_press_o,
            initial_read_back_bytes=args.initial_read_back_bytes,
            encoding=args.encoding,
        )
    except KeyboardInterrupt:
        return 130

    if result is None:
        print("未匹配到状态")
        return 1

    print(result.state_text)
    print(result.matched_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

