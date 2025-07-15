import requests
import json
from typing import Optional
from logging import getLogger
import sys
import os

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from env.config import Config
from google.transit import gtfs_realtime_pb2

# ロガーの設定
logger = getLogger(__name__)

# 環境変数からODPTトークンを取得
config = Config()
token = config.odpt_token

def get_train_timetable():
    url= f"https://api.odpt.org/api/v4/odpt:TrainTimetable?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    logger.info(f"Fetching train timetable from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        timetable = []
        for train_info in data:
            train_data = {
                "date": train_info.get("dc:date"),
                "issued": train_info.get("dct:issued"),
                "same_as": train_info.get("owl:sameAs"),
                "railway": train_info.get("odpt:railway"),
                "calendar": train_info.get("odpt:calendar"),
                "operator": train_info.get("odpt:operator"),
                "train_type": train_info.get("odpt:trainType"),
                "train_number": train_info.get("odpt:trainNumber"),                
                "origin_station": train_info.get("odpt:originStation"),
                "direction": train_info.get("odpt:railDirection"),
                "destination_station": train_info.get("odpt:destinationStation"),
                "stops": [],
            }
            
            for stop_info in train_info.get("odpt:trainTimetableObject", []):
                stop_data = {}
                if "odpt:departureStation" in stop_info:
                    stop_data["station"] = stop_info["odpt:departureStation"]
                elif "odpt:arrivalStation" in stop_info:
                    stop_data["station"] = stop_info["odpt:arrivalStation"]

                if "odpt:departureTime" in stop_info:
                    stop_data["departure_time"] = stop_info["odpt:departureTime"]
                
                if "odpt:arrivalTime" in stop_info:
                    stop_data["arrival_time"] = stop_info["odpt:arrivalTime"]

                if stop_data.get("station"):
                    train_data["stops"].append(stop_data)
            
            timetable.append(train_data)
        
        return timetable
    except requests.RequestException as e:
        logger.error(f"Error fetching train timetable: {e}")
        return None

def get_train_status():
    url=f"https://api.odpt.org/api/v4/odpt:TrainInformation?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    logger.info(f"Fetching train status from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        status_info = []
        for info in data:
            status_data = {
                "date": info.get("dc:date"),
                "valid": info.get("dct:valid"),
                "same_as":info.get("owl:sameAs"),
                "railway": info.get("odpt:railway"),
                "operator": info.get("odpt:operator"),
                "time_of_origin": info.get("odpt:timeOfOrigin"),
                "status": info.get("odpt:trainInformationText", {}).get("ja")
            }
            status_info.append(status_data)
        
        return status_info
    except requests.RequestException as e:
        logger.error(f"Error fetching train status: {e}")
        return None

def get_fare_information():
    url=f" https://api.odpt.org/api/v4/odpt:RailwayFare?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    logger.info(f"Fetching fare information from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        fare_data = []
        for fare_info in data:
            info = {
                "from_station": fare_info.get("odpt:fromStation"),
                "to_station": fare_info.get("odpt:toStation"),
                "ic_card_fare": fare_info.get("odpt:icCardFare"),
                "ticket_fare": fare_info.get("odpt:ticketFare"),
                "child_ic_card_fare": fare_info.get("odpt:childIcCardFare"),
                "child_ticket_fare": fare_info.get("odpt:childTicketFare"),
                "operator": fare_info.get("odpt:operator"),
                "date": fare_info.get("dc:date"),
                "issued": fare_info.get("dct:issued"),
                "same_as": fare_info.get("owl:sameAs"),
            }
            fare_data.append(info)
            
        return fare_data
    except requests.RequestException as e:
        logger.error(f"Error fetching fare information: {e}")
        return None

def get_station_information():
    url=f"https://api.odpt.org/api/v4/odpt:Station?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    logger.info(f"Fetching station information from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        stations = []
        for station in data:
            station_info = {
                "id": station.get("@id"),
                "date": station.get("dc:date"),
                "title": station.get("dc:title"),
                "latitude": station.get("geo:lat"),
                "longitude": station.get("geo:long"),
                "same_as": station.get("owl:sameAs"),
                "railway": station.get("odpt:railway"),
                "operator": station.get("odpt:operator"),
                "station_code": station.get("odpt:stationCode"),
                "station_title": station.get("odpt:stationTitle"),
                "passenger_survey": station.get("odpt:passengerSurvey"),
                "station_timetable": station.get("odpt:stationTimetable"),
                "connecting_railway": station.get("odpt:connectingRailway"),
                "connecting_station": station.get("odpt:connectingStation"),
            }
            stations.append(station_info)
        
        return stations
    except requests.RequestException as e:
        logger.error(f"Error fetching station information: {e}")
        return None


station_info = get_station_information()