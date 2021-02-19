from api import NREQ, _EDDBURL
import requests
import json

_SPANSHURL = 'https://spansh.co.uk/api/'

def getsmarketdetails(eddb_station): #spansh
    global NREQ
    url = f"{_SPANSHURL}station/{eddb_station}"
    try:
        resp = requests.get(url)
        content = json.loads(resp._content)
        myload = content["record"]
    except:
        print(f'!Failed to find stations for station "{eddb_station}"')
        myload = None
    NREQ += 1

    return myload

def getstations(faction_name,page=1): # eddb via elitebgs
    global NREQ
    answer = list()
    url = f"{_EDDBURL}stations"
    payload = {'controllingfactionname':faction_name, 'page' : page}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        myload = content["docs"]
        for station in myload:
            details = getsmarketdetails(station['ed_market_id'])
            station['system_name'] = details['system_name']
            station['market_updated_at'] = details['market_updated_at']
            station['market'] = details['market']
            station['spansh'] = details
            answer.append(station)


    except:
        print(f'!Failed to find stations for faction "{faction_name}"')
        myload = None
        content = None
    NREQ += 1
    if content['pages'] > int(content['page']) : ## More Pages so recurse
        answer += getstations(faction_name,1+int(content['page']))

    return answer

if __name__ == '__main__':
    stations = getstations('Canonn')

    print(f'*** Markets Done {NREQ}')
