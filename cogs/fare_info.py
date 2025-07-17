import discord
from discord import ap    def get_station_id_from_name(self, station_name: str) -> str:
        """駅名から駅IDを取得（運賃API用のIDに変換）"""
        station_ids = []
        for station in self.stations:
            if (station.get("station_title") and 
                station.get("station_title").get("ja") == station_name):
                # same_asから運賃API用のIDを取得
                same_as = station.get("same_as")
                if same_as:
                    station_ids.append(same_as)
            elif station.get("title") == station_name:
                same_as = station.get("same_as")
                if same_as:
                    station_ids.append(same_as)
        
        # 複数の路線に同じ駅名がある場合は、最初のIDを返す
        return station_ids[0] if station_ids else ""
    
    def get_all_station_ids_from_name(self, station_name: str) -> list:
        """駅名から全ての駅IDを取得（複数路線対応）"""
        station_ids = []
        for station in self.stations:
            if (station.get("station_title") and 
                station.get("station_title").get("ja") == station_name):
                same_as = station.get("same_as")
                if same_as:
                    station_ids.append(same_as)
            elif station.get("title") == station_name:
                same_as = station.get("same_as")
                if same_as:
                    station_ids.append(same_as)
        return station_idsdiscord.ext import commands
from API.TokyoMetro import get_fare_information, get_station_information
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

class FareInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stations = []
        self.station_names = []
        self._load_stations()

    def _load_stations(self):
        """駅情報を取得し、駅名のリストを作成"""
        try:
            station_info = get_station_information()
            if station_info:
                self.stations = station_info
                # 駅名を抽出（日本語名を優先）
                for station in station_info:
                    if station.get("station_title") and station.get("station_title").get("ja"):
                        self.station_names.append(station["station_title"]["ja"])
                    elif station.get("title"):
                        self.station_names.append(station["title"])
                
                # 重複を除去し、ソート
                self.station_names = sorted(list(set(self.station_names)))
                logger.info(f"読み込んだ駅数: {len(self.station_names)}")
            else:
                logger.error("駅情報を取得できませんでした")
        except Exception as e:
            logger.error(f"駅情報読み込み中にエラーが発生しました: {e}")

    def get_station_id_from_name(self, station_name: str) -> str:
        """駅名から駅IDを取得（運賃API用のIDに変換）"""
        for station in self.stations:
            if (station.get("station_title") and 
                station.get("station_title").get("ja") == station_name):
                # same_asから運賃API用のIDを取得
                same_as = station.get("owl:sameAs")
                if same_as:
                    return same_as
                return station.get("id", "")
            elif station.get("title") == station_name:
                same_as = station.get("owl:sameAs")
                if same_as:
                    return same_as
                return station.get("id", "")
        return ""

    async def station_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """駅名のオートコンプリート"""
        # 現在の入力に基づいて駅名を絞り込み
        if current:
            matches = [station for station in self.station_names if current.lower() in station.lower()]
        else:
            matches = self.station_names[:25]  # 最大25個まで表示
        
        return [
            app_commands.Choice(name=station, value=station)
            for station in matches[:25]  # Discordの制限により25個まで
        ]

    @app_commands.command(name="fare", description="東京メトロの駅間の運賃を検索します。")
    @app_commands.describe(from_station="出発駅", to_station="到着駅")
    @app_commands.autocomplete(from_station=station_autocomplete, to_station=station_autocomplete)
    async def fare(self, interaction: discord.Interaction, from_station: str, to_station: str):
        """指定された2駅間の運賃情報を表示します。"""
        await interaction.response.send_message(f"`{from_station}`駅から`{to_station}`駅までの運賃を検索しています...", ephemeral=True)
        
        try:
            # 駅名から全ての駅IDを取得
            from_station_ids = self.get_all_station_ids_from_name(from_station)
            to_station_ids = self.get_all_station_ids_from_name(to_station)
            
            if not from_station_ids or not to_station_ids:
                await interaction.followup.send("指定された駅名が見つかりませんでした。駅名を正しく選択してください。")
                return

            all_fares = get_fare_information()
            if not all_fares:
                await interaction.followup.send("運賃情報を取得できませんでした。")
                return

            # 全ての組み合わせで運賃情報を検索
            found_fare = None
            for from_id in from_station_ids:
                for to_id in to_station_ids:
                    for fare in all_fares:
                        if ((fare["from_station"] == from_id and fare["to_station"] == to_id) or
                            (fare["from_station"] == to_id and fare["to_station"] == from_id)):
                            found_fare = fare
                            break
                    if found_fare:
                        break
                if found_fare:
                    break
            
            if found_fare:
                embed = discord.Embed(
                    title=f"{from_station}駅 ⇔ {to_station}駅 の運賃",
                    color=discord.Color.blue()
                )
                embed.add_field(name="ICカード運賃", value=f"{found_fare['ic_card_fare']}円", inline=True)
                embed.add_field(name="切符運賃", value=f"{found_fare['ticket_fare']}円", inline=True)
                embed.add_field(name="こどもICカード運賃", value=f"{found_fare['child_ic_card_fare']}円", inline=True)
                embed.add_field(name="こども切符運賃", value=f"{found_fare['child_ticket_fare']}円", inline=True)
                embed.set_footer(text="情報提供: 東京メトロオープンデータ")
                
                await interaction.followup.send(embed=embed)
            else:
                # 同じ路線かどうかを確認
                from_station_info = None
                to_station_info = None
                
                for station in self.stations:
                    if station.get("same_as") in from_station_ids:
                        from_station_info = station
                    if station.get("same_as") in to_station_ids:
                        to_station_info = station
                
                # 同じ路線の駅があるかチェック
                same_railway = False
                if from_station_info and to_station_info:
                    for from_station_data in self.stations:
                        if from_station_data.get("same_as") in from_station_ids:
                            for to_station_data in self.stations:
                                if (to_station_data.get("same_as") in to_station_ids and
                                    from_station_data.get("railway") == to_station_data.get("railway")):
                                    same_railway = True
                                    railway_name = from_station_data.get("railway", "").replace("odpt.Railway:TokyoMetro.", "")
                                    break
                            if same_railway:
                                break
                
                if same_railway:
                    await interaction.followup.send(
                        f"`{from_station}`駅と`{to_station}`駅は同じ{railway_name}線内の駅です。\n"
                        f"同じ路線内の運賃情報は東京メトロオープンデータAPIでは提供されていません。\n"
                        f"詳細な運賃については東京メトロ公式サイトをご確認ください。"
                    )
                else:
                    await interaction.followup.send(f"`{from_station}`駅から`{to_station}`駅への運賃情報が見つかりませんでした。")

        except Exception as e:
            logger.error(f"運賃検索中にエラーが発生しました: {e}")
            await interaction.followup.send("運賃の検索中にエラーが発生しました。")

async def setup(bot):
    await bot.add_cog(FareInfo(bot))
