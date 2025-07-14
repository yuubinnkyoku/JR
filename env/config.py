# env/config.py

import configparser
import os


class Config:
    def __init__(self):
        path = os.path.join(os.path.dirname(__file__), "config.ini")
        self.config = configparser.ConfigParser()
        self.config.read(path, "UTF-8")

    @property
    def discord_token(self) -> str:
        return str(self.config["DISCORD"]["TOKEN"])
    
    @property
    def odpt_token(self) -> str:
        return str(self.config["ODPT"]["TOKEN"])