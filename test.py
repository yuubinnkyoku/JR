import json

import requests

url = "https://www.train-guide.westjr.co.jp/api/v3/area_kinki_master.json"
res = requests.get(url)
linedata = res.json()
lines = linedata["lines"]

print("データ構造:", type(lines))
print("路線数:", len(lines))
print("最初の5路線:")
for i, (key, line) in enumerate(lines.items()):
    if i < 5:
        print(f"  {key}: {line['name']}({line['range']})")
    else:
        break
