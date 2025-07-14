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

if __name__ == "__main__":
    timetables = get_train_timetable()
    if timetables:
        # 最初の5件だけ表示
        print(json.dumps(timetables[:5], indent=2, ensure_ascii=False))