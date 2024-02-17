import requests
import json
from datetime import datetime
from CSNSettings import CSNLog, RequestCount
from classes.Bubble import Bubble
from classes.Presense import Presence
from classes.System import System
from classes.State import State, Phase
from providers.EDDBFactions import isPlayer
import pickle
import os
from api import factionsovertime
from time import sleep


_ELITEBGSURL = 'https://elitebgs.app/api/ebgs/v5/'
DATADIR = '.\data'


def EliteBGSDateTime(datestring) -> datetime:
    """
    Converts Eligte BGS DateTime string to DateTime
    """
    dformat = '%Y-%m-%dT%H:%M:%S'  # so much grief from this function
    return (datetime.strptime(datestring[:len(dformat) + 2], dformat))


def LiveSystemDetails(system: System, forced: bool = False) -> System:
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
    except:
        CSNLog.info(
            f'Failed to find system "{system.name if system else "None"}"')
        print(
            f'!! Failed to find system "{system.name if system else "None"}"')
        return system

    updated = EliteBGSDateTime(myload['updated_at'])
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
                                  influence=round(100*fp['influence'], 2))
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

        # Remove Fations that have left since previous data
        system.factions = sorted(
            list(
                _ for _ in system.factions if _.source == 'EBGS'), key=lambda x: x.influence, reverse=True)

    # NREQ += 1
    return system


def EliteBGSFactionSystems(faction: str, page: int = 1) -> list:
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
                (sys['system_name'], EliteBGSDateTime(sys['updated_at']), factionhasconflict))
    except:
        CSNLog.info(f'Failed to find systems for faction "{faction}"')
        print(f'!Failed to find systems for faction "{faction}"')
        myload = None
        content = None
    if content.get('hasNextPage', None):  # More Pages so recurse
        answer += EliteBGSFactionSystems(faction, content['nextPage'])

    return answer


def RefreshFaction(bubble: Bubble, faction: str) -> None:
    """ Gets EBGS data for any systems with stale data or a conflict"""
    print(f"EBGS Refreshing systems for {faction}..")
    systems = EliteBGSFactionSystems(faction=faction)
    for sys_name, updated, inconflict in systems:
        system: System = bubble.getsystem(sys_name)
        if system.updated < updated or inconflict:
            print(f"    {sys_name:30} : {updated:%c} - {system.updated:%c}")
            system = LiveSystemDetails(system, inconflict)
        else:
            system.updated = updated


def HistoryCovert():
    systemhistory = dict()
    oldfile = os.path.join(DATADIR, 'EBGS_SysHist.pickle')
    if os.path.exists(oldfile):
        with open(oldfile, 'rb') as io:
            raw = pickle.load(io)
            for x in raw:
                systemhistory[x['name']] = {y for y in x['factions']}

    os.makedirs(DATADIR, exist_ok=True)
    with open(os.path.join(DATADIR, 'EBGS_SysHist2.pickle'), 'wb') as io:
        pickle.dump(systemhistory, io)
    return


def HistoryLoad(bubble) -> None:
    bubble.systemhistory = dict()
    if os.path.exists(os.path.join(DATADIR, 'EBGS_SysHist2.pickle')):
        with open(os.path.join(DATADIR, 'EBGS_SysHist2.pickle'), 'rb') as io:
            bubble.systemhistory = pickle.load(io)
    print(
        f"Loading System History {len(bubble.systemhistory)}/{len(bubble.systems)}...")
    system: System
    anychanges: bool = False
    for system in bubble.systems:
        # if system.name == 'Varati':
        #     bubble.systemhistory[system.name] = {}  # TEST
        if not bubble.systemhistory.get(system.name, None):
            bubble.systemhistory[system.name] = set(
                factionsovertime(system.name))
            anychanges = True
            sleep(5)  # Be nice to EBGS
        else:
            faction: Presence
            for faction in system.factions:
                if faction.name not in bubble.systemhistory[system.name]:
                    print(
                        f" New Expansion Detected {system.name}, {faction.name}")
                    bubble.systemhistory[system.name].add(faction.name)
                    anychanges = True
    if anychanges:
        HistorySave(bubble)


def HistorySave(bubble):
    os.makedirs(DATADIR, exist_ok=True)
    with open(os.path.join(DATADIR, 'EBGS_SysHist2.pickle'), 'wb') as io:
        pickle.dump(bubble.systemhistory, io)
