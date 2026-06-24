from time import sleep, time
from psutil import process_iter, Process

from win32gui import GetForegroundWindow
from win32process import GetWindowThreadProcessId
from win32api import GetLastInputInfo, GetTickCount

program = "Code.exe"
interval = 1
idle_threshold = 30

cool_cat = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⡴⣆⠀⠀⠀⠀⠀⣠⡀⠀⠀⠀⠀⠀⣼⣿⡗⠀⠀⠀⠀
⠀⠀⠀⣠⠟⠀⠘⠷⠶⠶⠶⠾⠉⢳⡄⠀⠀⠀⠀⣧⣿⠀⠀⠀⠀⠀
⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣤⣤⣤⣤⣿⢿⣄⠀⠀⠀⠀
⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣧⠀⠀⠀⠀⠀⠙⣷⡴⠶⣦
⠀⠀⢱⡀⠀⠉⠉⠀⠀⠀⠀⠛⠃⠀⢠⡟⠀⠀⠀⢀⣀⣤⠿⠞⠛⠋
⣠⠾⠋⠙⣶⣤⣤⣤⣤⣤⣀⣠⣤⣾⣿⠴⠶⠚⠋⠉⠁⠀⠀⠀⠀⠀
⠛⠒⠛⠉⠉⠀⠀⠀⣴⠟⢃⡴⠛⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠛⠛⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""


def is_focused() -> bool:
    try:
        hwnd = GetForegroundWindow()
        _, fg_pid = GetWindowThreadProcessId(hwnd)
        return Process(fg_pid).name() == program
    
    except Exception:
        return False


def input_idle_secs() -> float:
    return (GetTickCount() - GetLastInputInfo()) / 1000


def format_time(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02}:{(s % 3600) // 60:02}:{s % 60:02}"


print(cool_cat)

active_seconds = 0.0
last_check = time()

try:
    while True:
        if not any(p.info["name"] == program for p in process_iter(["name"])):
            break

        now = time()
        focused = is_focused()
        secs_idle = input_idle_secs()

        if not focused:
            status = "paused"

        elif secs_idle >= idle_threshold:
            status = f"idle ({format_time(secs_idle)})"

        else:
            active_seconds += now - last_check
            status = "active"

        last_check = now

        print("\033[2J\033[3J\033[H", end="")
        print(cool_cat)

        print("────────────────────────────")

        print(f"status: {status}")
        print(f"time:   {format_time(active_seconds)}")

        sleep(interval)

except KeyboardInterrupt:
    pass

print("\nyou have ended!")
print(f"final focused time: {format_time(active_seconds)}")