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
    # スラッシュコマンドを同期
    await bot.tree.sync()

@bot.tree.command(name="jr_west_delay", description="JR西日本の遅延情報を取得します。")
async def test(interaction: discord.Interaction):
    url="https://www.train-guide.westjr.co.jp/api/v3/area_kinki_master.json"
    res = requests.get(url)
    linedata = res.json()
    lines = linedata['lines']

    linelist=[]
    linename=[]
    linerange=[]
    for line in lines.values():
        linelist.append(line["pos"])
        linename.append(line["name"])
        linerange.append(line["range"])

    all_responses = []
    for i in range(len(linelist)):
        try:
            line=linelist[i]
            content=""
            content += f"**{linename[i]}({linerange[i]})**\n"
            url = f'https://www.train-guide.westjr.co.jp{line}'
            url_st = url.replace('.json','_st.json')
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
                    tc=item.get('typeChange', '')
                    if tc == " ":
                        tc=''
                    if item['displayType'][-1]=="○":
                        item['displayType'] = item['displayType'][:-1]+'速'
                    dest_text = item['dest']['text'] if isinstance(item['dest'], dict) else item['dest']
                    delay_messages.append(f"{item['displayType']} {dest_text}行き {tc} {item['no']} {item['delayMinutes']}分遅れ {position}")

            if delay_messages:
                content += "\n".join(delay_messages)
            else:
                content += "現在、遅延情報はありません。"
            all_responses.append(content)

        except RequestException as err:
            all_responses.append(f'HTTPError: {err}')
        except json.JSONDecodeError as err:
            all_responses.append(f'JSONDecodeError: {err}')
    
    final_response = "\n\n".join(all_responses)
    await interaction.response.send_message(final_response)


bot.run(token=token)
