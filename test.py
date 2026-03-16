import os
import time


input_file = r"F:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\console.log"
needle = "[Console] SV: Cheat command 'getpos' ignored."
needle_no = "setpos 0.000000 0.000000 0.000000;setang 0.000000 0.000000 0.000000"


def follow_file(path: str):
    last_inode = None

    while True:
        try:
            st = os.stat(path)
            inode = getattr(st, "st_ino", None)
            file_changed = inode != last_inode
            last_inode = inode

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if not file_changed:
                    f.seek(0, os.SEEK_END)

                while True:
                    line = f.readline()
                    if line:
                        yield line
                        continue

                    try:
                        new_st = os.stat(path)
                        new_inode = getattr(new_st, "st_ino", None)
                        if new_inode != last_inode or new_st.st_size < f.tell():
                            break
                    except FileNotFoundError:
                        break

                    time.sleep(0.1)
        except FileNotFoundError:
            time.sleep(0.5)


def main() -> None:
    for line in follow_file(input_file):
        if needle in line:
            print("yes", flush=True)
        if needle_no in line:
            print("NO", flush=True)


if __name__ == "__main__":
    main()
