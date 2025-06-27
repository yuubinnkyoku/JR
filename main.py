import traceback

import discord
import requests
from discord.ext import commands

from env.config import Config

config = Config()

token = config.token


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.tree.error
async def on_error(interaction, error):
    err = "".join(traceback.format_exception(error))
    embed = discord.Embed(description=f"```py\n{err}\n```"[:4095])
    if interaction.response.is_done():
        await interaction.channel.send("An error has occurred.", embed=embed)
    else:
        await interaction.response.send_message("An error has occurred.", embed=embed)


@bot.event
async def on_ready():
    print("ログインしました")
    # スラッシュコマンドを同期
    await bot.tree.sync()


@bot.tree.command(name="jr_west_delay", description="JR西日本の遅延情報を取得します。")
async def test(interaction: discord.Interaction):
    url = "https://www.train-guide.westjr.co.jp/api/v3/kobesanyo.json"
    # GETリクエストを送信
    response = requests.get(url)
    # レスポンスをJSON形式で取得
    data = response.json()

    trains = data["trains"]

    delay_messages = []
    for train in trains:
        delay = train["delayMinutes"]
        if delay != 0:
            delay_messages.append(
                f"{train['displayType']} {train['dest']['text']}行き {train['typeChange']} {train['no']}: {delay}分遅れ"
            )

    if delay_messages:
        content = "\n".join(delay_messages)
    else:
        content = "現在、遅延情報はありません。"
    await interaction.response.send_message(content)


bot.run(token=token)
