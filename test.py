import requests

url="https://www.train-guide.westjr.co.jp/api/v3/area_kinki_master.json"
res = requests.get(url)
linedata = res.json()
lines = linedata['lines']

linelist=[]
for line in lines:
    print(f"{line['name']}({line['range']})")
    linelist.append(line['pos'])
