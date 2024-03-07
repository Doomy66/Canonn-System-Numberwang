from cachetools import cached
import requests
import json
from CSNSettings import CSNLog, RequestCount
from classes.Presense import Presence
from classes.System import System
from classes.State import State, Phase
from providers.EDDBFactions import isPlayer
from datetime import datetime, timedelta
import time
import pickle
import os


_ELITEBGSURL = 'https://elitebgs.app/api/ebgs/v5/'
DATADIR = '.\data'


def EBGSDateTime(datestring: str) -> datetime:
    """
    Converts Eligte BGS DateTime string to DateTime
    """
    dformat = '%Y-%m-%dT%H:%M:%S'  # so much grief from this function
    return (datetime.strptime(datestring[:len(dformat) + 2], dformat))


def EBGSCache_Save(cache) -> None:
    """ Saves systems as most recent version of EBGS data """
    with open(os.path.join(DATADIR, 'EBGS_Cache.pickle'), 'wb') as io:
        pickle.dump(cache, io)


def EBGSCache_Load() -> dict[System]:
    """ Load most recent versions systems according to EBGS - Pickle can be deleted with minimal impact """
    answer = dict()
    if os.path.exists(os.path.join(DATADIR, 'EBGS_Cache.pickle')):
        with open(os.path.join(DATADIR, 'EBGS_Cache.pickle'), 'rb') as io:
            answer = pickle.load(io)
    return answer


def EBGSLiveSystem(system: System, forced: bool = False, cached=None) -> System:
    """
    Retrieve system and faction inf values from elitebgs using cached value if possible. 
    "refresh" will ignore cache and refresh the data. 
    If "system_name" is not a string, assume it is an eddbid int.
    """
    try:
        url = f"{_ELITEBGSURL}systems"
        payload = {'name': system.name, 'factionDetails': 'true'}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"][0]
        RequestCount()
        # CSNLog.info(f"EBGS Live Data for {system.name}")
    except:
        CSNLog.info(
            f'Failed to find system "{system.name if system else "None"}"')
        print(
            f'!! Failed to find system "{system.name if system else "None"}"')
        return system

    updated = EBGSDateTime(myload['updated_at'])
    # Ensure EBGS data isnt stale
    if updated > system.updated or forced:
        system.source = 'EBGS'
        system.updated = updated
        system.id = myload['eddb_id']
        system.controllingFaction = myload['controlling_minor_faction_cased']
        # # Dump for debugging
        # with open(f'data\\Test{system.name}.json', 'w') as io:  # Dump to file
        #     json.dump(myload, io, indent=4)

        for f in myload['factions']:
            fd = f['faction_details']  # Details are in a lower dict
            fp = fd['faction_presence']
            myPresence = Presence(name=f['name'], id=fd['eddb_id'],
                                  allegiance=fd['allegiance'].title(), government=fd['government'].title(),
                                  influence=100*fp['influence'])
            myPresence.isPlayer = isPlayer(myPresence.name)

            for state in fp['pending_states']:
                myState = State(state['state'].title(), phase=Phase.PENDING)
                myPresence.states.append(myState)
            for state in fp['active_states']:
                myState = State(state['state'].title(), phase=Phase.ACTIVE)
                myPresence.states.append(myState)
            for state in fp['recovering_states']:
                myState = State(state['state'].title(), phase=Phase.RECOVERING)
                myPresence.states.append(myState)

            if myPresence.influence > 0:
                system.addfaction(myPresence)

        for conflict in myload.get('conflicts', []):
            f1 = conflict['faction1']
            f2 = conflict['faction2']
            for faction in system.factions:
                if faction.name == f1['name']:
                    state: State
                    for state in faction.states:
                        if state.isConflict:
                            state.opponent = f2['name']
                            state.atstake = f1['stake']
                            state.dayswon = f1['days_won']
                            state.dayslost = f2['days_won']
                            state.gain = f2['stake']
                if faction.name == f2['name']:
                    state: State
                    for state in faction.states:
                        if state.isConflict:
                            state.opponent = f1['name']
                            state.atstake = f2['stake']
                            state.dayswon = f2['days_won']
                            state.dayslost = f1['days_won']
                            state.gain = f1['stake']

        # Remove Factions that have left since EDSM data
        system.factions = sorted(
            list(
                _ for _ in system.factions if _.source == 'EBGS'), key=lambda x: x.influence, reverse=True)
    return system


def EBGSFactionSystems(faction: str, page: int = 1) -> list:
    """
    Retrieve list of systems with faction present.
    """
    answer = list()
    url = f"{_ELITEBGSURL}factions"
    payload = {'name': faction, 'minimal': 'false',
               'systemDetails': 'false', 'page': page}
    try:
        resp = requests.get(url, params=payload)
        content = json.loads(resp._content)
        myload = content["docs"][0]['faction_presence']
        RequestCount()
        for sys in myload:
            factionhasconflict = sys.get('conflicts', None)
            answer.append(
                (sys['system_name'], EBGSDateTime(sys['updated_at']), factionhasconflict))
    except:
        CSNLog.info(f'Failed to find systems for faction "{faction}"')
        print(f'!Failed to find systems for faction "{faction}"')
        myload = None
        content = None
    if content.get('hasNextPage', None):  # More Pages so recurse
        answer += EBGSFactionSystems(faction, content['nextPage'])

    return answer


def RefreshFaction(mySystems: list[System], myFaction: str) -> list[System]:
    """ Gets EBGS data for any systems with stale data or a conflict"""
    print(f"EBGS Refreshing systems for {myFaction}..")
    CSNLog.info(f"EBGS Refreshing systems for {myFaction}")
    # ebgs_system_summary = EBGSFactionSystems(faction=myFaction)
    ebgs_system_summary = {}
    for name, updated, inconflict in EBGSFactionSystems(faction=myFaction):
        ebgs_system_summary[name.lower()] = (updated, inconflict)
    cache: dict[System] = EBGSCache_Load()
    answer = []

    for system in mySystems:
        updated, inconflict = ebgs_system_summary.get(
            system.name.lower(), (None, None))
        if updated:
            if system.updated < updated or inconflict:
                if cache.get(system.name) and cache[system.name].updated == updated:
                    # CSNLog.info(f"EBGS Cache {sys_name:30} : {updated:%c}")
                    system = cache[system.name]
                    print(
                        f" EBGS Cached  {system.name:30} : {updated:%c}")
                else:
                    CSNLog.info(
                        f"EBGS Request {system.name:30} : {updated:%c}")
                    print(f" EBGS Request {system.name:30} : {updated:%c}")
                    system = EBGSLiveSystem(system, inconflict)
                    cache[system.name] = system
            else:
                system.updated = updated
        answer.append(system)

    EBGSCache_Save(cache)
    return answer


def EBGSPreviousVisitors(system_name, days=30, earliest=datetime(2017, 10, 8)):
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
    earliest = datetime(2017, 10, 8)  # Garud says 1st record is 8th Oct 2017
    url = f"{_ELITEBGSURL}systems"

    print(f"Historic Info for {system_name} ")
    while minTime != earliest:
        minTime = max(earliest, maxTime+timedelta(days=-days))

        # There is no TRY Block as it might make the cache invalid and cause a total rebuild
        payload = {'name': system_name, 'timeMin': int(
            1000*time.mktime(minTime.timetuple())), 'timeMax': int(1000*time.mktime(maxTime.timetuple()))}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"]
        RequestCount()
        if len(myload):  # Was getting nothing for a specific Detention Center
            myload = myload[0]
            if myload['history']:
                for h in myload['history']:
                    for f in h['factions']:
                        if f['name'] not in factions:
                            factions.append(f['name'])  # Faction Arrived
                            print(f"{f['name']} - {myload['updated_at']}")
            maxTime = minTime
        else:
            break
    print('')
    return factions
