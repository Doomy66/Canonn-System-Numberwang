# Canonn Research - Fleet Carrier Location
from CSNSettings import CSNLog
import requests
import json

_CANONN = 'https://us-central1-canonn-api-236217.cloudfunctions.net/'


def getfleetcarrier(fc_id):
    """ Get FC Info from Canonn API """
    try:
        url = f"{_CANONN}postFleetCarriers"
        payload = {'serial': fc_id}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)[0]
    except:
        CSNLog.info(f'Failed to find FC "{fc_id}"')
        print(f'!Failed to find FC "{fc_id}"')
        myload = None
    return myload
