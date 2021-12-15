import os
import subprocess
import time
import logging
import numpy as np
import mss
import mouse

from logger import Logger
from config import Config
from screen import Screen
from template_finder import TemplateFinder

LauncherExeName = "Diablo II Resurrected Launcher.exe"
BnetExeName = "Battle.net.exe"
GameExeName = "D2R.exe"
BNET_PLAY = "BNET_PLAY"
BLZ_LOGO = "BLZ_LOGO"
D2_LOGO_HS = "D2_LOGO_HS"
HeroImgPrefix = r"config\hero_img"


class GameRestart:
    def __init__(self, screen: Screen, config: Config):
        self._screen, self._config = screen, config
        self._template_finder = TemplateFinder(self._screen, [r"config\hero_img", r"assets\restart"])
        self._sct = mss.mss()

    def is_config_valid(self) -> bool:
        if not self._config.general["launcher_path"] or not self._config.general["hero_name"]:
            Logger.debug(
                f"no launcher_path or hero_name: {self._config.general['launcher_path']}, self._config.general['hero_name']")
            return False
        if not os.path.exists(self._config.general["launcher_path"]):
            Logger.debug(self._config.general["launcher_path"] + " not exists")
            return False
        hero_img_path = os.path.join(HeroImgPrefix, self._config.general["hero_name"] + ".png")
        if not os.path.exists(hero_img_path):
            Logger.debug(hero_img_path + " not exists")
            return False
        Logger.info("game restart: found valid config")
        return True

    def open_launcher(self):
        Logger.debug(f"open launcher: {self._config.general['launcher_path']}")
        subprocess.Popen(self._config.general['launcher_path'])

    def grab_ss(self):
        return np.array(self._sct.grab(self._sct.monitors[self._config.general['monitor']]))

    def click_bnet_play(self, timeout=60):
        start = time.time()
        Logger.debug("wait for bnet play button")
        while 1:
            if time.time() - start > timeout:
                return False
            match = self._template_finder.search(BNET_PLAY, self.grab_ss(), normalize_monitor=True, use_grayscale=True)
            if not match.valid:  # not match bnet play button
                time.sleep(1)
                continue

            mouse.move(match.position[0], match.position[1], True)
            time.sleep(0.1)
            mouse.click()
            Logger.debug("click bnet play button")
            return True

    def wait_for_game(self, timeout=60):
        pos = self._screen.convert_screen_to_monitor(
            (self._config.ui_pos["screen_width"] / 2, self._config.ui_pos["screen_height"] / 2))
        mouse.move(pos[0], pos[1])

        Logger.debug("wait for blz logo")
        while 1:
            match = self._template_finder.search(BLZ_LOGO, self._screen.grab(), use_grayscale=True)
            mouse.click()
            if not match.valid:  # not match blz logo
                time.sleep(1)
                continue
            Logger.debug("match blz log, connect to bnet, the next screen will be hero select")
            break

        # click again to guarantee bnet connection
        time.sleep(1)
        mouse.click()

        time.sleep(5)  # wait 5 seconds for bnet connection, ignore queue situation...
        match = self._template_finder.search_and_wait(D2_LOGO_HS, time_out=timeout, use_grayscale=True)
        return match.valid

    def select_hero(self, is_online=False):
        relative_pos = (1100, 30) if is_online else (1200, 30)  # online tab, offline tab position
        abs_pos = self._screen.convert_screen_to_monitor(relative_pos)
        mouse.move(abs_pos[0], abs_pos[1])
        time.sleep(0.1)
        mouse.click()
        time.sleep(1)

        hero_key = self._config.general["hero_name"].upper()

        match = self._template_finder.search_and_wait(hero_key, time_out=60, use_grayscale=True)
        if not match.valid:
            Logger.debug(f"game restart: not match hero key: {hero_key}")
            return False
        abs_pos = self._screen.convert_screen_to_monitor(match.position)
        mouse.move(abs_pos[0], abs_pos[1])
        time.sleep(0.1)
        mouse.click()
        Logger.debug(f"game restart: hero {self._config.general['hero_name']} selected")
        return True

    def restart_game(self, is_online=False, retry=10) -> bool:
        Logger.info("game restart: try to kill and restart game")
        for i in range(retry):
            Logger.debug(f"game restart: retry {i}")
            self.kill_process()
            self.open_launcher()
            if not self.click_bnet_play():
                Logger.info("game restart: timeout to find bnet button, continue restart game...")
                continue
            time.sleep(10)  # wait for game client
            if not self.wait_for_game():
                Logger.info("game restart: timeout to enter hero select screen, continue restart game...")
                continue
            Logger.info("game restart: success enter hero select screen")
            if self.select_hero(is_online):
                return True
        else:
            Logger.error(
                f"game restart: tried {retry} times yet still failed to find your hero. Please press enter to exit botty...")
            input()
            exit(1)

    @staticmethod
    def kill_process():
        Logger.debug("kill all game processes")
        os.system(f'taskkill /f /im "{LauncherExeName}"')
        os.system(f'taskkill /f /im "{BnetExeName}"')
        os.system(f'taskkill /f /im "{GameExeName}"')


if __name__ == "__main__":
    conf = Config(print_warnings=True)
    if conf.general["logg_lvl"] == "info":
        Logger.init(logging.INFO)
    elif conf.general["logg_lvl"] == "debug":
        Logger.init(logging.DEBUG)
    else:
        print(f"ERROR: Unkown logg_lvl {conf.general['logg_lvl']}. Must be one of [info, debug]")
    scr = Screen(conf.general["monitor"])

    GameRestart(scr, conf).restart_game(is_online=False)
