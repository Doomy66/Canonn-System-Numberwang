# Canonn Research - Fleet Carrier Location
import requests
import json

_CANONN = 'https://us-central1-canonn-api-236217.cloudfunctions.net/query/'


def getfleetcarrier(fc_id):
    """ Get FC Info from Canonn API """
    try:
        # url = f"{_CANONN}postFleetCarriers"
        # payload = {'serial': fc_id}
        url = f"{_CANONN}fleetCarrier/{fc_id}"
        resp = requests.get(url)
        myload = json.loads(resp._content)[0]
    except:
        # CSNLog.info(f'Failed to find FC "{fc_id}"')
        print(f'!Failed to find FC "{fc_id}"')
        myload = None
    return myload


if __name__ == '__main__':
    print(getfleetcarrier('TNY-09Z'))
