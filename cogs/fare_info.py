import discord
from discord import app_commands
from discord.ext import commands
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
        return station_ids

    def find_stations_by_name(self, input_name: str) -> list:
        """入力された駅名から候補駅を検索（部分一致・曖昧検索対応）"""
        matches = []
        input_lower = input_name.lower().replace(" ", "").replace("　", "")
        
        for station in self.stations:
            station_name = ""
            if station.get("station_title") and station.get("station_title").get("ja"):
                station_name = station.get("station_title").get("ja")
            elif station.get("title"):
                station_name = station.get("title")
            
            if station_name:
                station_lower = station_name.lower().replace(" ", "").replace("　", "")
                same_as = station.get("same_as")
                
                # 完全一致
                if station_lower == input_lower:
                    matches.append({
                        "name": station_name,
                        "id": same_as,
                        "priority": 1
                    })
                # 前方一致
                elif station_lower.startswith(input_lower):
                    matches.append({
                        "name": station_name,
                        "id": same_as,
                        "priority": 2
                    })
                # 部分一致
                elif input_lower in station_lower:
                    matches.append({
                        "name": station_name,
                        "id": same_as,
                        "priority": 3
                    })
        
        # 優先度でソートし、重複を除去
        seen_names = set()
        unique_matches = []
        for match in sorted(matches, key=lambda x: (x["priority"], x["name"])):
            if match["name"] not in seen_names:
                seen_names.add(match["name"])
                unique_matches.append(match)
        
        return unique_matches[:10]  # 最大10件まで返す

    @app_commands.command(name="fare", description="東京メトロの駅間の運賃を検索します。")
    @app_commands.describe(from_station="出発駅（駅名を入力してください）", to_station="到着駅（駅名を入力してください）")
    async def fare(self, interaction: discord.Interaction, from_station: str, to_station: str):
        """指定された2駅間の運賃情報を表示します。"""
        await interaction.response.send_message(f"`{from_station}`駅から`{to_station}`駅までの運賃を検索しています...", ephemeral=True)
        
        try:
            # 入力された駅名から候補を検索
            from_candidates = self.find_stations_by_name(from_station)
            to_candidates = self.find_stations_by_name(to_station)
            
            if not from_candidates:
                embed = discord.Embed(
                    title="駅が見つかりません",
                    description=f"`{from_station}`に該当する駅が見つかりませんでした。",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="ヒント",
                    value="• 駅名の一部だけでも検索できます\n• ひらがな、カタカナ、漢字で入力してください\n• 例: `新宿`, `しんじゅく`, `シンジュク`",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            if not to_candidates:
                embed = discord.Embed(
                    title="駅が見つかりません",
                    description=f"`{to_station}`に該当する駅が見つかりませんでした。",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="ヒント",
                    value="• 駅名の一部だけでも検索できます\n• ひらがな、カタカナ、漢字で入力してください\n• 例: `新宿`, `しんじゅく`, `シンジュク`",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 複数候補がある場合は最初の候補を使用し、候補リストも表示
            selected_from = from_candidates[0]
            selected_to = to_candidates[0]
            
            # 候補が複数ある場合の情報表示用
            from_info = f"`{selected_from['name']}`"
            if len(from_candidates) > 1:
                other_from = [c['name'] for c in from_candidates[1:6]]  # 最大5つまで表示
                from_info += f"\n（他の候補: {', '.join(other_from)}{'...' if len(from_candidates) > 6 else ''}）"
            
            to_info = f"`{selected_to['name']}`"
            if len(to_candidates) > 1:
                other_to = [c['name'] for c in to_candidates[1:6]]  # 最大5つまで表示
                to_info += f"\n（他の候補: {', '.join(other_to)}{'...' if len(to_candidates) > 6 else ''}）"

            # 運賃情報を取得
            all_fares = get_fare_information()
            if not all_fares:
                await interaction.followup.send("運賃情報を取得できませんでした。")
                return

            # 選択された駅のIDを使用して運賃情報を検索
            from_station_ids = [selected_from['id']] if selected_from['id'] else []
            to_station_ids = [selected_to['id']] if selected_to['id'] else []
            
            # 他の候補駅のIDも追加
            for candidate in from_candidates[1:]:
                if candidate['id'] and candidate['id'] not in from_station_ids:
                    from_station_ids.append(candidate['id'])
            for candidate in to_candidates[1:]:
                if candidate['id'] and candidate['id'] not in to_station_ids:
                    to_station_ids.append(candidate['id'])

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
                    title=f"{selected_from['name']}駅 ⇔ {selected_to['name']}駅 の運賃",
                    color=discord.Color.blue()
                )
                embed.add_field(name="ICカード運賃", value=f"{found_fare['ic_card_fare']}円", inline=True)
                embed.add_field(name="切符運賃", value=f"{found_fare['ticket_fare']}円", inline=True)
                embed.add_field(name="こどもICカード運賃", value=f"{found_fare['child_ic_card_fare']}円", inline=True)
                embed.add_field(name="こども切符運賃", value=f"{found_fare['child_ticket_fare']}円", inline=True)
                
                # 候補が複数ある場合の情報を表示
                if len(from_candidates) > 1 or len(to_candidates) > 1:
                    candidate_info = ""
                    if len(from_candidates) > 1:
                        candidate_info += f"**出発駅**: {from_info}\n"
                    if len(to_candidates) > 1:
                        candidate_info += f"**到着駅**: {to_info}\n"
                    if candidate_info:
                        embed.add_field(name="検索結果", value=candidate_info, inline=False)
                
                embed.set_footer(text="情報提供: 東京メトロオープンデータ")
                await interaction.followup.send(embed=embed)
            else:
                # 直通運賃がない場合、複数区間の運賃と経路を計算
                from heapq import heappush, heappop
                # 駅IDから駅名へのマップ作成
                name_map = {}
                for station in self.stations:
                    # same_asキーから駅IDを取得
                    sid = station.get("same_as") or station.get("id")
                    name = station.get("station_title", {}).get("ja") or station.get("title")
                    if sid:
                        name_map[sid] = name
                # グラフ構築: {駅ID: [(隣駅ID, costs), ...]}
                graph = {}
                for fare in all_fares:
                    u = fare["from_station"]
                    v = fare["to_station"]
                    costs = {
                        "ic": fare.get("ic_card_fare", 0),
                        "ticket": fare.get("ticket_fare", 0),
                        "child_ic": fare.get("child_ic_card_fare", 0),
                        "child_ticket": fare.get("child_ticket_fare", 0),
                    }
                    graph.setdefault(u, []).append((v, costs))
                    graph.setdefault(v, []).append((u, costs))
                # ダイクストラ: cost_keyの運賃で経路とコストを取得
                def dijkstra(src, dst, cost_key):
                    heap = [(0, src, [src])]
                    visited = set()
                    while heap:
                        cost, node, path = heappop(heap)
                        if node == dst:
                            return cost, path
                        if node in visited:
                            continue
                        visited.add(node)
                        for nb, c in graph.get(node, []):
                            if nb not in visited:
                                heappush(heap, (cost + c[cost_key], nb, path + [nb]))
                    return None, None
                # 最良経路探索(ICカード運賃基準)
                best = None  # (ic_cost, path)
                for src in from_station_ids:
                    for dst in to_station_ids:
                        ic_cost, path = dijkstra(src, dst, "ic")
                        if ic_cost is None:
                            continue
                        if best is None or ic_cost < best[0]:
                            best = (ic_cost, path)
                # 経路が見つかった場合、他運賃も同経路で計算
                if best:
                    ic_cost, path = best
                    # 他運賃の合計
                    ticket = child_ic = child_ticket = 0
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i+1]
                        for nb, c in graph.get(u, []):
                            if nb == v:
                                ticket += c["ticket"]
                                child_ic += c["child_ic"]
                                child_ticket += c["child_ticket"]
                                break
                    # 経路の駅名リスト
                    route_names = [name_map.get(s, s) for s in path]
                    route_str = " → ".join(route_names)
                    embed = discord.Embed(
                        title=f"{selected_from['name']}駅 ⇔ {selected_to['name']}駅 の運賃 (経路表示)",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="経路", value=route_str, inline=False)
                    embed.add_field(name="ICカード運賃", value=f"{ic_cost}円", inline=True)
                    embed.add_field(name="切符運賃", value=f"{ticket}円", inline=True)
                    embed.add_field(name="こどもICカード運賃", value=f"{child_ic}円", inline=True)
                    embed.add_field(name="こども切符運賃", value=f"{child_ticket}円", inline=True)
                    
                    # 候補が複数ある場合の情報を表示
                    if len(from_candidates) > 1 or len(to_candidates) > 1:
                        candidate_info = ""
                        if len(from_candidates) > 1:
                            candidate_info += f"**出発駅**: {from_info}\n"
                        if len(to_candidates) > 1:
                            candidate_info += f"**到着駅**: {to_info}\n"
                        if candidate_info:
                            embed.add_field(name="検索結果", value=candidate_info, inline=False)
                    
                    embed.set_footer(text="最短ICカード運賃の経路を合算しています")
                    await interaction.followup.send(embed=embed)
                    return
                # 経路計算でも見つからない場合は同一路線／未提供メッセージへ
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
                        f"`{selected_from['name']}`駅と`{selected_to['name']}`駅は同じ{railway_name}線内の駅です。\n"
                        f"同じ路線内の運賃情報は東京メトロオープンデータAPIでは提供されていません。\n"
                        f"詳細な運賃については東京メトロ公式サイトをご確認ください。"
                    )
                else:
                    embed = discord.Embed(
                        title="運賃情報が見つかりません",
                        description=f"`{selected_from['name']}`駅から`{selected_to['name']}`駅への運賃情報が見つかりませんでした。",
                        color=discord.Color.orange()
                    )
                    
                    # 候補が複数ある場合の情報を表示
                    if len(from_candidates) > 1 or len(to_candidates) > 1:
                        candidate_info = ""
                        if len(from_candidates) > 1:
                            candidate_info += f"**出発駅の候補**: {', '.join([c['name'] for c in from_candidates[:5]])}\n"
                        if len(to_candidates) > 1:
                            candidate_info += f"**到着駅の候補**: {', '.join([c['name'] for c in to_candidates[:5]])}\n"
                        if candidate_info:
                            embed.add_field(name="他の候補駅", value=candidate_info, inline=False)
                    
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"運賃検索中にエラーが発生しました: {e}")
            embed = discord.Embed(
                title="エラーが発生しました",
                description="運賃の検索中にエラーが発生しました。しばらく時間をおいて再度お試しください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FareInfo(bot))
