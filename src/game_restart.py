import os
import subprocess
import time
import logging
import cv2
import numpy as np
import mss
import mouse

from logger import Logger
from config import Config
from screen import Screen

LauncherExeName = "Diablo II Resurrected Launcher.exe"
BnetExeName = "Battle.net.exe"
GameExeName = "D2R.exe"
BnetPlayTemplate = r"assets\restart\bnet_play.png"
BlzLogoTemplate = r"assets\restart\blz_logo.png"


def kill_process():
    Logger.debug("kill all game processes")
    os.system(f'taskkill /f /im "{LauncherExeName}"')
    os.system(f'taskkill /f /im "{BnetExeName}"')
    os.system(f'taskkill /f /im "{GameExeName}"')


def open_launcher(launcher_path):
    Logger.debug(f"open launcher: {launcher_path}")
    subprocess.Popen(launcher_path)


def match_template(sct, monitor_idx, template, threshold=0.8):
    img = np.array(sct.grab(sct.monitors[monitor_idx]))
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    return np.where(res >= threshold)


def click_bnet_play(sct, monitor_idx, timeout: float = 60) -> bool:
    template = cv2.imread(BnetPlayTemplate, 0)
    w, h = template.shape[::-1]
    start = time.time()

    while 1:
        if time.time() - start > timeout:
            return False
        loc = match_template(sct, monitor_idx, template)
        if len(loc[0]) == 0:  # not match bnet play button
            time.sleep(1)
            Logger.debug("not match bnet play button, continue...")
            continue
        for pt in zip(*loc[::-1]):
            mouse.move(pt[0] + w / 2, pt[1] + h / 2, True)
            mouse.click()
            time.sleep(0.1)
            Logger.debug("click bnet play button")
            return True


def wait_for_game(sct, screen: Screen, monitor_idx, timeout: float = 60) -> bool:
    pos = screen.convert_screen_to_monitor((1280 / 2, 720 / 2))
    mouse.move(pos[0], pos[1])

    while 1:
        template = cv2.imread(BlzLogoTemplate, 0)
        loc = match_template(sct, monitor_idx, template)
        mouse.click()
        if len(loc[0]) == 0:  # not match blz logo
            Logger.debug("not match blz logo, continue...")
            time.sleep(1)
            continue
        Logger.debug("match blz log, connect to bnet, the next screen will be hero select")
        break

    # click again to guarantee bnet connection
    time.sleep(1)
    mouse.click()

    start = time.time()
    time.sleep(5)  # wait 10 seconds for bnet connection, ignore queue situation...
    while 1:
        interval = time.time() - start
        if (interval > 5) and (interval > timeout):
            return False
        template = cv2.imread(r"assets\templates\d2_logo_hs.png", 0)
        loc = match_template(sct, monitor_idx, template)
        if len(loc[0]) == 0:
            Logger.debug(r"not match assets\templates\d2_logo_hs.png, continue...")
            time.sleep(1)
            continue
        Logger.debug(r"match assets\templates\d2_logo_hs.png")
        return True


def restart_game(screen: Screen, monitor_idx: int, launcher_path: str):
    while 1:
        Logger.info("try to restart game")
        kill_process()
        open_launcher(launcher_path)
        sct = mss.mss()
        if not click_bnet_play(sct, monitor_idx):
            Logger.info("restart game: timeout to find bnet button, continue restart game...")
            continue
        time.sleep(10)  # wait for game client
        if not wait_for_game(sct, screen, monitor_idx):
            Logger.info("restart game: timeout to enter hero select screen, continue restart game...")
            continue
        Logger.info("restart game: success enter hero select screen")
        break


if __name__ == "__main__":
    config = Config(print_warnings=True)
    if config.general["logg_lvl"] == "info":
        Logger.init(logging.INFO)
    elif config.general["logg_lvl"] == "debug":
        Logger.init(logging.DEBUG)
    else:
        print(f"ERROR: Unkown logg_lvl {config.general['logg_lvl']}. Must be one of [info, debug]")
    path = config.general["launcher_path"]
    scr = Screen(config.general["monitor"])

    restart_game(scr, config.general["monitor"], path)
