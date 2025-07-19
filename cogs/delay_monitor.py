import discord
from discord.ext import commands, tasks
import asyncio
from logging import getLogger
import sys
import os
from datetime import datetime

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from API.TokyoMetro import get_train_status
from env.config import Config

# ロガーの設定
logger = getLogger(__name__)

class DelayMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        self.previous_delays = {}  # 前回の遅延情報を保存
        
    async def cog_load(self):
        """Cogが読み込まれた際に監視タスクを開始"""
        logger.info("遅延監視タスクを開始します")
        self.delay_monitor_task.start()
    
    def cog_unload(self):
        """Cogがアンロードされた際に監視タスクを停止"""
        logger.info("遅延監視タスクを停止します")
        self.delay_monitor_task.cancel()
    
    @tasks.loop(minutes=1)
    async def delay_monitor_task(self):
        """1分ごとに遅延情報をチェック"""
        try:
            logger.info("遅延情報をチェック中...")
            status_info = get_train_status()
            
            if not status_info:
                logger.warning("遅延情報の取得に失敗しました")
                return
            
            # 遅延がある路線を抽出
            current_delays = {}
            for info in status_info:
                railway = info.get("railway", "")
                status = info.get("status", "")
                
                # 遅延情報があるかチェック（正常運行でない場合）
                if status and "正常" not in status and "平常" not in status:
                    current_delays[railway] = {
                        "status": status,
                        "time_of_origin": info.get("time_of_origin"),
                        "railway": railway
                    }
            
            # 新しい遅延があるかチェック
            new_delays = {}
            for railway, delay_info in current_delays.items():
                if railway not in self.previous_delays:
                    new_delays[railway] = delay_info
                elif self.previous_delays[railway]["status"] != delay_info["status"]:
                    new_delays[railway] = delay_info
            
            # 解消された遅延をチェック
            resolved_delays = {}
            for railway in self.previous_delays:
                if railway not in current_delays:
                    resolved_delays[railway] = self.previous_delays[railway]
            
            # 遅延情報を各サーバーに送信
            if new_delays or resolved_delays:
                await self.send_delay_notifications(new_delays, resolved_delays)
            
            # 前回の遅延情報を更新
            self.previous_delays = current_delays
            
        except Exception as e:
            logger.error(f"遅延監視タスクでエラーが発生しました: {e}")
    
    async def send_delay_notifications(self, new_delays: dict, resolved_delays: dict):
        """遅延情報を各サーバーに送信"""
        delay_channels = self.config.get_all_delay_channels()
        
        for guild_id, channel_id in delay_channels.items():
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"チャンネルが見つかりません: {channel_id} (サーバー: {guild_id})")
                    continue
                
                embeds = []
                
                # 新しい遅延情報
                for railway, delay_info in new_delays.items():
                    embed = discord.Embed(
                        title="🚨 遅延情報",
                        description=f"**{self.format_railway_name(railway)}**",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(
                        name="運行状況",
                        value=delay_info["status"],
                        inline=False
                    )
                    if delay_info.get("time_of_origin"):
                        embed.add_field(
                            name="発生時刻",
                            value=delay_info["time_of_origin"],
                            inline=True
                        )
                    embeds.append(embed)
                
                # 解消された遅延情報
                for railway, delay_info in resolved_delays.items():
                    embed = discord.Embed(
                        title="✅ 運行正常化",
                        description=f"**{self.format_railway_name(railway)}**",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(
                        name="状況",
                        value="運行が正常化されました",
                        inline=False
                    )
                    embeds.append(embed)
                
                # Embedを送信
                for embed in embeds:
                    await channel.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"チャンネル {channel_id} への送信でエラーが発生しました: {e}")
    
    def format_railway_name(self, railway: str) -> str:
        """路線名をフォーマット"""
        # odpt:Railway:TokyoMetro.Ginza -> 銀座線
        if "TokyoMetro." in railway:
            line_name = railway.split("TokyoMetro.")[-1]
            line_mapping = {
                "Ginza": "銀座線",
                "Marunouchi": "丸ノ内線",
                "Hibiya": "日比谷線",
                "Tozai": "東西線",
                "Chiyoda": "千代田線",
                "Yurakucho": "有楽町線",
                "Hanzomon": "半蔵門線",
                "Namboku": "南北線",
                "Fukutoshin": "副都心線"
            }
            return line_mapping.get(line_name, line_name + "線")
        return railway
    
    @delay_monitor_task.before_loop
    async def before_delay_monitor(self):
        """ボットの準備ができるまで待機"""
        await self.bot.wait_until_ready()
        logger.info("ボットの準備が完了しました。遅延監視を開始します。")
    
    @commands.command(name="set_delay_channel")
    @commands.has_permissions(administrator=True)
    async def set_delay_channel(self, ctx, channel: discord.TextChannel = None):
        """遅延情報を送信するチャンネルを設定"""
        if channel is None:
            channel = ctx.channel
        
        try:
            # config.iniファイルを更新
            config_path = os.path.join(os.path.dirname(__file__), '..', 'env', 'config.ini')
            
            # 現在の設定を読み込み
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path, 'UTF-8')
            
            # MONITORINGセクションが存在しない場合は作成
            if 'MONITORING' not in config:
                config.add_section('MONITORING')
            
            # サーバーIDとチャンネルIDを設定
            config['MONITORING'][str(ctx.guild.id)] = str(channel.id)
            
            # ファイルに書き込み
            with open(config_path, 'w', encoding='UTF-8') as configfile:
                config.write(configfile)
            
            embed = discord.Embed(
                title="✅ 設定完了",
                description=f"遅延情報の送信先を {channel.mention} に設定しました",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            # 設定を再読み込み
            self.config = Config()
            
        except Exception as e:
            logger.error(f"チャンネル設定でエラーが発生しました: {e}")
            embed = discord.Embed(
                title="❌ エラー",
                description="設定の保存に失敗しました",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="delay_status")
    async def delay_status(self, ctx):
        """現在の遅延情報を表示"""
        try:
            status_info = get_train_status()
            
            if not status_info:
                embed = discord.Embed(
                    title="❌ エラー",
                    description="遅延情報の取得に失敗しました",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            delays = []
            normal_operations = []
            
            for info in status_info:
                railway = info.get("railway", "")
                status = info.get("status", "")
                
                if status and "正常" not in status and "平常" not in status:
                    delays.append({
                        "railway": self.format_railway_name(railway),
                        "status": status
                    })
                else:
                    normal_operations.append(self.format_railway_name(railway))
            
            if delays:
                embed = discord.Embed(
                    title="🚨 現在の遅延情報",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                for delay in delays:
                    embed.add_field(
                        name=delay["railway"],
                        value=delay["status"],
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="✅ 運行状況",
                    description="現在、遅延は発生していません",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"遅延状況確認でエラーが発生しました: {e}")
            embed = discord.Embed(
                title="❌ エラー",
                description="遅延情報の取得に失敗しました",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DelayMonitor(bot))
