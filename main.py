import traceback
import discord
import json
import requests
from requests.exceptions import RequestException
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
    await bot.tree.sync()

async def get_delay_info(line_pos: str, line_name: str, line_range: str) -> str:
    """Fetches and formats delay information for a given train line."""
    try:
        content = f"**{line_name}({line_range})**\n"
        url = f'https://www.train-guide.westjr.co.jp{line_pos}'
        url_st = url.replace('.json', '_st.json')
        
        res = requests.get(url)
        res_st = requests.get(url_st)
        res.raise_for_status()
        res_st.raise_for_status()
        
        data = res.json()
        data_st = res_st.json()

        dictst = {station['info']['code']: station['info']['name'] for station in data_st['stations']}

        delay_messages = []
        for item in data['trains']:
            if item['delayMinutes'] > 0:
                stn = item['pos'].split('_')
                try:
                    position = dictst[stn[0]] + '辺り'
                except KeyError:
                    position = "どこかよくわかんない"
                
                tc = item.get('typeChange', '')
                if tc == " ":
                    tc = ''
                
                display_type = item['displayType']
                if display_type.endswith("○"):
                    display_type = display_type[:-1] + '速'
                
                dest_text = item['dest']['text'] if isinstance(item['dest'], dict) else item['dest']
                delay_messages.append(f"{display_type} {dest_text}行き {tc} {item['no']} {item['delayMinutes']}分遅れ {position}")

        if delay_messages:
            content += "\n".join(delay_messages)
        else:
            content += "現在、遅延情報はありません。"
        
        return content

    except RequestException as err:
        return f'HTTPError: {err}'
    except json.JSONDecodeError as err:
        return f'JSONDecodeError: {err}'

class LineSelect(discord.ui.Select):
    def __init__(self, lines):
        options = [
            discord.SelectOption(label=f"{line['name']}({line['range']})", value=key)
            for key, line in lines.items()
        ]
        super().__init__(placeholder="路線を選択してください", options=options)
        self.lines = lines

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_key = self.values[0]
        selected_line = self.lines[selected_key]
        
        line_pos = selected_line['pos']
        line_name = selected_line['name']
        line_range = selected_line['range']

        delay_info = await get_delay_info(line_pos, line_name, line_range)
        await interaction.followup.send(delay_info)

class LineSelectView(discord.ui.View):
    def __init__(self, lines):
        super().__init__()
        line_items = list(lines.items())
        for i in range(0, len(line_items), 25):
            chunk = dict(line_items[i:i+25])
            if not chunk:
                break
            self.add_item(LineSelect(chunk))

@bot.tree.command(name="jr_west_delay", description="JR西日本の遅延情報を取得します。")
async def jr_west_delay(interaction: discord.Interaction):
    url = "https://www.train-guide.westjr.co.jp/api/v3/area_kinki_master.json"
    try:
        res = requests.get(url)
        res.raise_for_status()
        linedata = res.json()
        lines = linedata['lines']
        
        view = LineSelectView(lines)
        await interaction.response.send_message("確認したい路線を選択してください。", view=view)

    except (RequestException, json.JSONDecodeError) as e:
        await interaction.response.send_message(f"路線の取得に失敗しました: {e}")

bot.run(token=token)
