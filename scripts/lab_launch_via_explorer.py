import os
import subprocess
import sys
import time

import win32api
import win32con
import win32process

CLIENT_DIR = r"C:\Azerothcore\wowclient\WOW_3.3.5a"
EXPLORER = os.path.join(os.environ["SystemRoot"], "explorer.exe")


def launch_via_explorer():
    si = win32process.STARTUPINFO()
    si.lpDesktop = "WinSta0\\Default"
    hproc, hthread, pid, tid = win32process.CreateProcess(
        EXPLORER,
        "explorer.exe " + os.path.join(CLIENT_DIR, "Wow.exe"),
        None,
        None,
        False,
        win32con.CREATE_NEW_CONSOLE,
        None,
        CLIENT_DIR,
        si,
    )
    print("explorer launcher pid", pid)
    return pid


if __name__ == "__main__":
    launch_via_explorer()
