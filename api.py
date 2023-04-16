'''
    All API functions required to gather BGS data for Frontier Development's Elite Dangerous
    In Memory Caching is used where possible
'''

import requests
import csv
import json
from datetime import datetime, timedelta, timezone
import time
import sys
from CSNSettings import CSNLog

from requests.models import Response


NREQ = 0  # Count of all api calls made to monitor your own usage. Its nice when you care.
_SYSTEMCACHE = dict()
_ELITEBGSURL = 'https://elitebgs.app/api/ebgs/v5/'
_CANONN = 'https://us-central1-canonn-api-236217.cloudfunctions.net/'
_RAWLASTTICK = None

def _ebgsDateTime(dateTimeString):
    '''
    Converts EliteBGS formated DateTime string to DateTime
    Not exposed as all API calls should have code do all converstions
    '''
    dformat = '%Y-%m-%dT%H:%M:%S'
    #return(datetime.strptime(dateTimeString[:len(dformat) + 2], dformat).replace(tzinfo=timezone.utc)) ## TypeError: can't compare offset-naive and offset-aware datetimes
    return(datetime.strptime(dateTimeString[:len(dformat) + 2], dformat))

def _ebgsDateTimeString(dateTime):
    '''
    Converts DateTime to EliteBGS formated strinf
    Not exposed as all API calls should have code do all converstions
    '''
    dformat = '%Y-%m-%dT%H:%M:%S'
    return(datetime.strftime(dformat))

def getfleetcarrier(fc_id):
    ''' Get FC Info from Canonn API'''
    global NREQ
    try:
        url = f"{_CANONN}postFleetCarriers"
        payload = {'serial':fc_id}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)[0]
    except:
        CSNLog.info(f'Failed to find FC "{fc_id}"')
        print(f'!Failed to find FC "{fc_id}"')
        myload = None
    NREQ +=1
    return myload

def getfaction(faction_name): # elitebgs
    '''
    Retrieve faction system presence from elitebgs  
    '''
    global NREQ
    try:
        url = f"{_ELITEBGSURL}factions"
        payload = {'name':faction_name}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"][0]
        for sys in myload['faction_presence']:
            # empire is overridden by a more detailed node in Bubble, but at least tells you WHY you requested this system in case you are collecting systems for multiple factions
            sys['empire'] = faction_name
            sys['happytext'] = 'Elated' if sys['happiness'] == '$faction_happinessband1;' else 'Happy' if sys['happiness'] == '$faction_happinessband2;' else 'Peeved'
    except:
        CSNLog.info(f'Failed to find faction "{faction_name}"')
        print(f'!Failed to find faction "{faction_name}"')
        myload = None
    NREQ += 1
    return myload

def getfactionsystems(faction_name,page=1): # elitebgs
    '''
    Retrieve system and faction inf values from elitebgs for all systems with faction_name present.
    Only fetchs 10 per API call unlike using factions endpoint which gets all systems in 1 call, but  this method avoids update date/time being out of sync
    '''
    global NREQ
    answer = list()
    url = f"{_ELITEBGSURL}systems"
    payload = {'faction':faction_name, 'factionDetails':'true', 'page' : page}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        myload = content["docs"]
        for sys in myload:
            sys['empire'] = faction_name
            answer.append(sys)
    except:
        CSNLog.info(f'Failed to find systems for faction "{faction_name}"')
        print(f'!Failed to find systems for faction "{faction_name}"')
        myload = None
        content = None
    NREQ += 1
    if content['hasNextPage']: ## More Pages so recurse
        answer += getfactionsystems(faction_name,content['nextPage'])

    return answer

def getsystem(system_name, refresh=False): # elitebgs
    '''
    Retrieve system and faction inf values from elitebgs using cached value if possible. 
    "refresh" will ignore cache and refresh the data. 
    If "system_name" is not a string, assume it is an eddbid int.
    '''
    global NREQ, _SYSTEMCACHE, _RAWLASTTICK
    if not _RAWLASTTICK:
        _RAWLASTTICK = getlasttick(True)
    if refresh or system_name not in _SYSTEMCACHE:
        try:
            url = f"{_ELITEBGSURL}systems"
            #payload = {'name':system_name, 'factionDetails':'true', 'count':1} if type(system_name) == str else {'eddbid':system_name, 'factionDetails':'true', 'count':1}
            payload = {'name':system_name, 'factionDetails':'true'} if type(system_name) == str else {'eddbid':system_name, 'factionDetails':'true'}
            resp = requests.get(url, params=payload)
            myload = json.loads(resp._content)["docs"][0]
            myload['system_name'] = myload['name']
            system_name = myload['system_name']
            # move faction details up to faction node
            for f in myload['factions']:
                f['influence'] = f['faction_details']['faction_presence']['influence']*100
                f['conflicts'] = f['faction_details']['faction_presence']['conflicts']
                f['active_states'] = f['faction_details']['faction_presence']['active_states']
                f['pending_states'] = f['faction_details']['faction_presence']['pending_states']
                f['recovering_states'] = f['faction_details']['faction_presence']['recovering_states']
                if f['influence'] == 0:
                    print(f"!!Zero Faction {f['name']} in {system_name}")
            #if len(myload['factions']) != len(myload['history'][0]['factions']):
            #    print(f"!!Faction Count WRONG in {system_name}")

            myload['factions'].sort(key = lambda x: x['influence'], reverse=True)
        except:
            CSNLog.info(f'Failed to find system "{system_name}"')
            print(f'!Failed to find system "{system_name}"')
            myload = None
        NREQ += 1
        if myload:
            _SYSTEMCACHE[system_name] = myload
        else:
            return None

    _SYSTEMCACHE[system_name]['fresh'] = _RAWLASTTICK < _SYSTEMCACHE[system_name]['updated_at']

    return _SYSTEMCACHE[system_name]

def getnearsystems(system_name, range=20, page=1): # elitebgs
    '''
    Retrieve system and faction inf values from elitebgs for all systems within cube "range" of "system_name".
    Cube distance added for easy decision on simple or expanded expansion.
    '''
    global NREQ
    refsystem = None
    answer = list()
    url = f"{_ELITEBGSURL}systems"
    payload = {'referenceSystem':system_name, 'factionDetails':'true', 'referenceDistance':range, 'page' : page}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        myload = content["docs"]
        for sys in myload:
            if not refsystem:
                refsystem = sys
            answer.append(sys)
    except:
        print(f'!Failed to find system "{system_name}"')
        myload = None
        content = None
    NREQ += 1
    if content['hasNextPage']: ## More Pages so recurse
        answer += getnearsystems(system_name,range,content['nextPage'])

    for sys in answer: ## Will be wrong except for page 1, which will fix all the following pages
        sys['cubedist'] = max(
            [abs(sys['x']-refsystem['x']), abs(sys['y']-refsystem['y']), abs(sys['z']-refsystem['z'])])

    return answer

def getstations(system_name): # elitebgs
    global NREQ
    url = f"{_ELITEBGSURL}stations"
    payload = {'system':system_name}
    resp = requests.get(url, params=payload)
    myload = json.loads(resp._content)["docs"]
    NREQ += 1
    return myload

def getlasttick(raw=False): # elitebgs
    '''
    Returns data & time of last tick from elitebgs as a datetime
    A True "raw" will return the original string value
    '''
    global NREQ
    url = f'{_ELITEBGSURL}ticks'
    payload = {}
    r = requests.get(url, params=payload)
    try:
        myload = json.loads(r._content)[0]
        NREQ += 1
    except:
        print('!!Last Tick Failed : '+r.reason)
        exit()
    if raw:
        return myload["updated_at"]
    else:
        return _ebgsDateTime(myload["updated_at"])

def eddbNatives(system_name):
    '''
    Given a system_name (string)
    Returns all factions registered with that system as their home system. Not 100% sure this is reliable, but it is the ONLY source of this data
    Documentation https://elitebgs.app/api/eddb
    '''
    global NREQ
    CSNLog.info('EDDB NativesRequested !')
    url = 'https://eddbapi.elitebgs.app/api/v4/factions'
    payload = {'homesystemname': system_name}
    r = requests.get(url, params=payload)
    myload = json.loads(r._content)["docs"]
    NREQ += 1

    ans = list()
    for f in myload:
        ans.append(f['name'])
    return ans

def eddbAllStations(sysnameid):
    '''
    Given a system name (string) or system eddbID (int)
    Returns all stations within that system
    Documentation https://elitebgs.app/api/eddb
    NB Body Information is only an ID which does not seem to match any available body id source
    '''
    global NREQ
    CSNLog.info('EDDB AllStations Requested !')
    url = 'https://eddbapi.elitebgs.app/api/v4/stations'
    payload = {'eddbid': sysnameid} if type(sysnameid) == int else {'systemname': sysnameid}

    r = requests.get(url, params=payload)
    try:
        myload = json.loads(r._content)["docs"]#[0]
    except:
        print(f'!System Not found : {sysnameid}')
        return(None)

    NREQ += 1
    return(myload)

def CSNPatrol():
    '''
    Read the CSNPatrol google sheet without any google api requirement
    '''
    #TODO Try publishing and reading as JSON ?
    answer = list()
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTmSy_Lb3ponEAuQzYmDcQIQfnFOPxq3p7S-abYZXlAx_9Ew2iO98Na4_4xvKJPcf1EpEse9TOclB4d/pub?gid=1280901060&single=true&output=tsv"  # Set your BGS override link(tsv)
    with requests.get(url, stream=True) as r:
        reader = csv.reader(r.content.decode('utf-8').splitlines(), delimiter='\t')
        next(reader)
        for row in reader:
            system, x, y, z, TINF, TFAC, Description,icon = row
            instructions = Description.format(TFAC, TINF)
            if system:
                answer.append({'system':system,'icon':icon,'x':x,'y':y,'z':z,'message':instructions})
    return(answer)

def apicount():
    return NREQ

def retreated_factions(system_name, count=300): # elitebgs NO DONT USE
    '''
    Return a list of all Factions that have ever retreated from system.
    Abandoned as a count of 300 was deemed excessive and should be done incrementally with timeMin and timeMax
    '''
    global NREQ 
    try:
        url = f"{_ELITEBGSURL}systems"
        payload = {'name':system_name, 'count':count}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"][0]
        myload['system_name'] = myload['name']
    except:
        print(f'!Failed to find system "{system_name}"')
        myload = None

    factions = list()
    retreated = list()
    myload['history'].sort(key = lambda x: x['updated_at'])
    for h in myload['history']:
        for f in h['factions']:
            if f['name'] not in factions:
                #print(f">{f['name']} on {h['updated_at']}")
                factions.append(f['name']) # Faction Arrived
        for f in factions:
            #f = next((x for x in self.factions if x['id'] == idorname),None)
            if not next((x for x in h['factions'] if x['name']==f),None):
                #print(f"<{f} on {h['updated_at']}")
                retreated.append(f) # Faction Retreated
                factions.remove(f)


    NREQ += 1

    return retreated

def retreated_systems(faction, count=300): # elitebgs NO DONT USE
    '''
    Abandoned as a count of 300 was deemed excessive and should be done incrementally with timeMin and timeMax
    '''
    global NREQ 
    systems = list()
    retreated = list()

    try:
        url = f"{_ELITEBGSURL}factions"
        payload = {'name':faction, 'count':count}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"][0]
        myload['system_name'] = myload['name']
        myload['history'].sort(key = lambda x: x['updated_at'])
        for h in myload['history']:
            for s in h['systems']:
                if s['name'] not in systems:
                    print(f">{s['name']} on {h['updated_at']}")
                    systems.append(s['name']) # Faction Arrived
                    if s['name'] in retreated:
                        retreated.remove(s['name'])
            for s in systems:
                if not next((x for x in h['systems'] if x['name']==s),None):
                    print(f"<{s} on {h['updated_at']}")
                    retreated.append(s) # Faction Retreated
                    systems.remove(s)
    except:
        print(f'!Failed to find faction "{faction}"')

    NREQ += 1

    return retreated

def factionsovertime(system_name, days=30, earliest = datetime(2017,10,8) ): # elitebgs #Garud says 1st record is 8th Oct 1997
    '''
    Return a list of all factions that have ever been in the system
    Can be compared to current factions to identify historic retreats
    Really sorry this takes so long, but ebgs is the ONLY source of this data
    and a full scan through system history is the ONLY way to get the data out of ebgs
    '''
    global NREQ 

    factions = list()
    maxTime = datetime.now()
    minTime = None 
    earliest = datetime(2017,10,8) #Garud says 1st record is 8th Oct 1997
    url = f"{_ELITEBGSURL}systems"

    sys.stdout.write(f"Historic Info for {system_name} ")
    while minTime != earliest:
        minTime = max(earliest,maxTime+timedelta(days=-days))

        ## There is no TRY Block as it might make the cache invalid and cause a total rebuild
        payload = {'name':system_name, 'timeMin':int(1000*time.mktime(minTime.timetuple())), 'timeMax':int(1000*time.mktime(maxTime.timetuple()))}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"]
        if len(myload): # Was getting nothing for a specific Detention Center
            myload = myload[0]
            sys.stdout.write(':' if myload['history'] else '.')
            sys.stdout.flush()
            NREQ += 1

            if myload['history']:
                for h in myload['history']:
                    for f in h['factions']:
                        if f['name'] not in factions:
                            factions.append(f['name']) # Faction Arrived
                            print(f"{f['name']} - {myload['updated_at']}")
            maxTime = minTime
        else:
            break
    print('')
    return factions

def dcohsummary():
    ''' 
    Summarise DCOH Watchlist to list of system names and threat name
    '''
    answer = list()
    url = f"https://dcoh.watch/api/v1/overwatch/systems"
    payload = {'ngsw-bypass':True}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        thargsystems = content["systems"]
        for sys in thargsystems:
            #print(sys["name"],sys["thargoidLevel"]["name"],100*sys["progressPercent"] if sys["progressPercent"] else 0)
            answer.append({"sys_name":sys["name"],"threat":sys["thargoidLevel"]["name"],"level":sys["thargoidLevel"]["level"],"progress":100*sys["progressPercent"] if sys["progressPercent"] else 0})
    except:
        print("!!DCOH Error")

    print('DCOH Complete')
    return answer

if __name__ == '__main__':
    # Test Harness
    print('Test Harness for...')
    #print(factionsovertime('Jaoi'))
    #print(retreated_factions('Cnephtha'))
    print(dcohsummary())

    print('Nothing')
    print(f'Done with {NREQ} requests')
