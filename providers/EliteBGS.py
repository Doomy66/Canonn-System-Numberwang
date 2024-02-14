import requests
import json
from datetime import datetime
from CSNSettings import CSNLog, RequestCount
from classes.Bubble import Bubble
from classes.Presense import Presence
from classes.System import System
from classes.State import State
from providers.EDDBFactions import isPlayer


_ELITEBGSURL = 'https://elitebgs.app/api/ebgs/v5/'


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
                myState = State(state['state'].title(), phase='P')
                myPresence.states.append(myState)
            for state in fp['active_states']:
                myState = State(state['state'].title(), phase='A')
                myPresence.states.append(myState)
            for state in fp['recovering_states']:
                myState = State(state['state'].title(), phase='R')
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
        system.factions = list(
            _ for _ in system.factions if _.source == 'EBGS')

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