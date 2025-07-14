import json
import traceback
from typing import Optional
import discord
import requests
from discord.ext import commands
from requests.exceptions import RequestException

from env.config import Config

config = Config()
token = config.discord_token

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
        url = f"https://www.train-guide.westjr.co.jp{line_pos}"
        url_st = url.replace(".json", "_st.json")

        res = requests.get(url)
        res_st = requests.get(url_st)
        res.raise_for_status()
        res_st.raise_for_status()

        data = res.json()
        data_st = res_st.json()

        dictst = {
            station["info"]["code"]: station["info"]["name"]
            for station in data_st["stations"]
        }

        delay_messages = []
        for item in data["trains"]:
            if item["delayMinutes"] > 0:
                stn = item["pos"].split("_")
                try:
                    position = dictst[stn[0]] + "辺り"
                except KeyError:
                    position = "どこかよくわかんない"

                tc = item.get("typeChange", "")
                if tc == " ":
                    tc = ""

                display_type = item["displayType"]
                if display_type.endswith("○"):
                    display_type = display_type[:-1] + "速"

                dest_text = (
                    item["dest"]["text"]
                    if isinstance(item["dest"], dict)
                    else item["dest"]
                )
                delay_messages.append(
                    f"{display_type} {dest_text}行き {tc} {item['no']} {item['delayMinutes']}分遅れ {position}"
                )

        if delay_messages:
            content += "\n".join(delay_messages)
        else:
            content += "現在、遅延情報はありません。"

        return content

    except RequestException as err:
        return f"HTTPError: {err}"
    except json.JSONDecodeError as err:
        return f"JSONDecodeError: {err}"


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

        line_pos = selected_line["pos"]
        line_name = selected_line["name"]
        line_range = selected_line["range"]

        delay_info = await get_delay_info(line_pos, line_name, line_range)
        await interaction.followup.send(delay_info)


class LineSelectView(discord.ui.View):
    def __init__(self, lines):
        super().__init__()
        line_items = list(lines.items())
        for i in range(0, len(line_items), 25):
            chunk = dict(line_items[i : i + 25])
            if not chunk:
                break
            self.add_item(LineSelect(chunk))


# グローバルに路線データをキャッシュ
_cached_lines = None


async def get_lines_data():
    """路線データを取得・キャッシュする"""
    global _cached_lines
    if _cached_lines is None:
        url = "https://www.train-guide.westjr.co.jp/api/v3/area_kinki_master.json"
        res = requests.get(url)
        res.raise_for_status()
        linedata = res.json()
        _cached_lines = linedata["lines"]
    return _cached_lines


def split_lines_into_groups(lines: dict) -> tuple[dict, dict]:
    """路線を2つのグループに分割する"""
    line_items = list(lines.items())
    group1 = dict(line_items[:25])
    group2 = dict(line_items[25:])
    return group1, group2


@bot.tree.command(name="jr_west_delay", description="JR西日本の遅延情報を取得します。")
@discord.app_commands.describe(
    group="路線グループを選択してください", line="路線を選択してください"
)
async def jr_west_delay(
    interaction: discord.Interaction, group: str, line: Optional[str] = None
):
    try:
        lines = await get_lines_data()
        group1, group2 = split_lines_into_groups(lines)

        if group == "group1":
            selected_lines = group1
        elif group == "group2":
            selected_lines = group2
        else:
            await interaction.response.send_message("無効なグループが選択されました。")
            return

        if line is None:
            # 路線が選択されていない場合、利用可能な路線を表示
            line_list = "\n".join(
                [
                    f"• {line_data['name']}({line_data['range']})"
                    for line_data in selected_lines.values()
                ]
            )
            await interaction.response.send_message(
                f"以下の路線から選択してください：\n{line_list}"
            )
            return

        if line not in selected_lines:
            await interaction.response.send_message("無効な路線が選択されました。")
            return

        selected_line = selected_lines[line]
        line_pos = selected_line["pos"]
        line_name = selected_line["name"]
        line_range = selected_line["range"]

        delay_info = await get_delay_info(line_pos, line_name, line_range)
        await interaction.response.send_message(delay_info)

    except (RequestException, json.JSONDecodeError) as e:
        await interaction.response.send_message(f"遅延情報の取得に失敗しました: {e}")


# オートコンプリート関数
@jr_west_delay.autocomplete("group")
async def group_autocomplete(interaction: discord.Interaction, current: str):
    choices = [
        discord.app_commands.Choice(name="路線グループ1 (1-25)", value="group1"),
        discord.app_commands.Choice(name="路線グループ2 (26-)", value="group2"),
    ]
    return choices


@jr_west_delay.autocomplete("line")
async def line_autocomplete(interaction: discord.Interaction, current: str):
    try:
        group = interaction.namespace.group
        if not group:
            return []

        lines = await get_lines_data()
        group1, group2 = split_lines_into_groups(lines)

        if group == "group1":
            selected_lines = group1
        elif group == "group2":
            selected_lines = group2
        else:
            return []

        choices = []
        for key, line_data in selected_lines.items():
            name = f"{line_data['name']}({line_data['range']})"
            if current.lower() in name.lower():
                choices.append(discord.app_commands.Choice(name=name, value=key))
                if len(choices) >= 25:  # Discord の制限
                    break

        return choices
    except Exception:
        return []

bot.run(token=token)
