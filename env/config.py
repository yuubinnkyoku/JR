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
    
    def get_delay_channel_id(self, guild_id: int) -> int | None:
        """指定されたサーバーIDに対応する遅延情報チャンネルIDを取得"""
        try:
            if "MONITORING" in self.config and str(guild_id) in self.config["MONITORING"]:
                return int(self.config["MONITORING"][str(guild_id)])
            return None
        except (ValueError, KeyError):
            return None
    
    def get_all_delay_channels(self) -> dict[int, int]:
        """すべてのサーバーの遅延情報チャンネル設定を取得"""
        channels = {}
        if "MONITORING" in self.config:
            for guild_id, channel_id in self.config["MONITORING"].items():
                try:
                    # コメント行をスキップ
                    if not guild_id.startswith('#'):
                        channels[int(guild_id)] = int(channel_id)
                except ValueError:
                    continue
        return channels