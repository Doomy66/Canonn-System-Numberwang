# Defence Council of Humanity provides Thargoid Activity
import requests
import json
from CSNSettings import CSNLog


def dcohsummary():
    ''' 
    Summarise DCOH Watchlist to list of system names and threat name
    '''
    answer = list()
    url = f"https://dcoh.watch/api/v1/overwatch/systems"
    payload = {'ngsw-bypass': True}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        thargsystems = content["systems"]
        for sys in thargsystems:
            # print(sys["name"],sys["thargoidLevel"]["name"],100*sys["progressPercent"] if sys["progressPercent"] else 0)
            answer.append({"sys_name": sys["name"], "threat": sys["thargoidLevel"]["name"], "level": sys["thargoidLevel"]
                          ["level"], "progress": 100*sys["progressPercent"] if sys["progressPercent"] else 0})
    except:
        print("!!DCOH Error")
        CSNLog('DCOH Error')
        return answer

    CSNLog('DCOH Complete')
    return answer
