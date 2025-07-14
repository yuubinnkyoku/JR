import requests
import json
from typing import Optional
from env.config import Config
from google.transit import gtfs_realtime_pb2

config = Config()
token = config.odpt_token

def get_train_timetable():
    url= f"https://api.odpt.org/api/v4/odpt:TrainTimetable?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    print(f"Fetching train timetable from: {url}")
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
        print(f"Error fetching train timetable: {e}")
        return None

def get_train_status():
    url=f"https://api.odpt.org/api/v4/odpt:TrainInformation?odpt:operator=odpt.Operator:TokyoMetro&acl:consumerKey={token}"
    print(f"Fetching train status from: {url}")
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
        print(f"Error fetching train status: {e}")
        return None

def get_train_realtime_information():
    url=f"https://api.odpt.org/api/v4/gtfs/realtime/tokyometro_odpt_train_alert?acl:consumerKey={token}"
    print(f"Fetching train realtime information from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        alerts = []
        for entity in feed.entity:
            if entity.HasField('alert'):
                alert_data = {
                    "cause": entity.alert.cause,
                    "effect": entity.alert.effect,
                    "header_text": entity.alert.header_text.translation[0].text,
                    "description_text": entity.alert.description_text.translation[0].text,
                }
                alerts.append(alert_data)
        return alerts
    except requests.RequestException as e:
        print(f"Error fetching train realtime information: {e}")
        return None

if __name__ == "__main__":
    statuses = get_train_status()
    if statuses:
        print(json.dumps(statuses, indent=2, ensure_ascii=False))
    
    realtime_info = get_train_realtime_information()
    if realtime_info:
        print(json.dumps(realtime_info, indent=2, ensure_ascii=False))