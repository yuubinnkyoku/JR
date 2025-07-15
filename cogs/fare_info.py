import discord
from discord import app_commands
from discord.ext import commands
from cogs.TokyoMetro import get_fare_information
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

class FareInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fare", description="東京メトロの駅間の運賃を検索します。")
    @app_commands.describe(from_station="出発駅", to_station="到着駅")
    async def fare(self, interaction: discord.Interaction, from_station: str, to_station: str):
        """指定された2駅間の運賃情報を表示します。"""
        await interaction.response.send_message(f"`{from_station}`駅から`{to_station}`駅までの運賃を検索しています...", ephemeral=True)
        
        try:
            all_fares = get_fare_information()
            if not all_fares:
                await interaction.followup.send("運賃情報を取得できませんでした。")
                return

            found_fare = None
            for fare in all_fares:
                # from_station と to_station の両方が駅名に含まれているかチェック
                # APIからの駅名は "odpt.Station:TokyoMetro.Marunouchi.Tokyo" のような形式
                if from_station in fare["from_station"] and to_station in fare["to_station"]:
                    found_fare = fare
                    break
                # 逆方向も検索
                if to_station in fare["from_station"] and from_station in fare["to_station"]:
                    found_fare = fare
                    break
            
            if found_fare:
                from_station_name = found_fare["from_station"].split('.')[-1]
                to_station_name = found_fare["to_station"].split('.')[-1]

                embed = discord.Embed(
                    title=f"{from_station_name}駅 ⇔ {to_station_name}駅 の運賃",
                    color=discord.Color.blue()
                )
                embed.add_field(name="ICカード運賃", value=f"{found_fare['ic_card_fare']}円", inline=True)
                embed.add_field(name="切符運賃", value=f"{found_fare['ticket_fare']}円", inline=True)
                embed.add_field(name="こどもICカード運賃", value=f"{found_fare['child_ic_card_fare']}円", inline=True)
                embed.add_field(name="こども切符運賃", value=f"{found_fare['child_ticket_fare']}円", inline=True)
                embed.set_footer(text="情報提供: 東京メトロオープンデータ")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"`{from_station}`駅から`{to_station}`駅への運賃情報が見つかりませんでした。駅名が正しいか確認してください。")

        except Exception as e:
            logger.error(f"運賃検索中にエラーが発生しました: {e}")
            await interaction.followup.send("運賃の検索中にエラーが発生しました。")

async def setup(bot):
    await bot.add_cog(FareInfo(bot))
