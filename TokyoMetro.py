import requests
import json
from typing import Optional
from env.config import Config

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
                "train_number": train_info.get("odpt:trainNumber"),
                "train_type": train_info.get("odpt:trainType"),
                "railway": train_info.get("odpt:railway"),
                "origin_station": train_info.get("odpt:originStation"),
                "destination_station": train_info.get("odpt:destinationStation"),
                "direction": train_info.get("odpt:railDirection"),
                "stops": []
            }
            
            for stop_info in train_info.get("odpt:trainTimetableObject", []):
                stop_data = {}
                if "odpt:departureTime" in stop_info:
                    stop_data["time"] = stop_info["odpt:departureTime"]
                    stop_data["station"] = stop_info["odpt:departureStation"]
                elif "odpt:arrivalTime" in stop_info:
                    stop_data["time"] = stop_info["odpt:arrivalTime"]
                    stop_data["station"] = stop_info["odpt:arrivalStation"]
                
                if stop_data:
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

if __name__ == "__main__":
    statuses = get_train_status()
    if statuses:
        print(json.dumps(statuses, indent=2, ensure_ascii=False))