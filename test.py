import ctypes
import os
import time


input_file = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"
dust2 = "[Client] loaded spawngroup(  1)  : SV:  [1: de_dust2 | main lump | mapload]"
mirage = " [Client] loaded spawngroup(  1)  : SV:  [1: de_mirage | main lump | mapload]"
pipei = "[Developer] Matchmaking update: 1"


def press_p() -> None:
    vk_code = 0x50
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


class LogTailer:
    def __init__(self, path: str):
        self.path = path
        self._inode = None
        self._file = None
        self._pos = 0

    def _open_if_needed(self) -> bool:
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            self._close()
            return False

        inode = getattr(st, "st_ino", None)
        if self._file is None or inode != self._inode:
            self._close()
            self._file = open(self.path, "r", encoding="utf-8", errors="ignore")
            self._inode = inode
            self._file.seek(0, os.SEEK_END)
            self._pos = self._file.tell()
            return True

        if st.st_size < self._pos:
            self._file.seek(0, os.SEEK_END)
            self._pos = self._file.tell()

        return True

    def _close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            finally:
                self._file = None
        self._inode = None
        self._pos = 0

    def poll_state(self, timeout_s: float = 1.0):
        start = time.time()
        while time.time() - start < timeout_s:
            if not self._open_if_needed():
                time.sleep(0.2)
                continue

            line = self._file.readline()
            if not line:
                self._pos = self._file.tell()
                time.sleep(0.05)
                continue

            if dust2 in line:
                return 1
            if mirage in line:
                return 2
            if pipei in line:
                return 3

        return None
def main() -> None:
    tailer = LogTailer(input_file)
    while True:
        press_p()
        state = tailer.poll_state(timeout_s=1.0)
        if state == 1:
            print("dust2", flush=True)
        elif state == 2:
            print("mirage", flush=True)
        elif state == 3:
            print("匹配",flush=True)

        else:
            print("未知", flush=True)
        time.sleep(1)


if __name__ == "__main__":
    time.sleep(3)
    main()
