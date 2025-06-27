import json
import urllib.request

try
    url = 'https://www.train-guide.westjr.co.jp/api/v3/kobesanyo.json'
    url_st = url.replace('.json','_st.json')
    res = urllib.request.urlopen(url)
    res_st = urllib.request.urlopen(url_st)
    data = json.loads(res.read().decode('utf-8'))
    data_st = json.loads(res_st.read().decode('utf-8'))

    dictst = {}

    for station in data_st['stations']:
        dictst[station['info']['code']] = station['info']['name']

    for item in data['trains']:
        if item['delayMinutes'] > 0:
            stn = item['pos'].split('_')
            try:
                position = dictst[stn[0]] + '辺り'
            except KeyError:
                position = "どこかよくわかんない"
            tc=item['typeChange']
            if tc == " ":
                tc=''
            print(f"{item['displayType']} {item['dest']['text']}行き {tc} {item['no']} {item['delayMinutes']}分遅れ {position}")

except urllib.error.HTTPError as err:
    print('HTTPError: ', err)
except json.JSONDecodeError as err:
    print('JSONDecodeError: ', err)