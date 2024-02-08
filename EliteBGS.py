import requests
import csv
import json
from datetime import datetime, timedelta, timezone
import time
import sys
from CSNSettings import CSNLog
from DataClassesBase import System, Presence, State
from EDDBFactions import isPlayer

_ELITEBGSURL = 'https://elitebgs.app/api/ebgs/v5/'


def LiveSystemDetails(system: System) -> System:
    '''
    Retrieve system and faction inf values from elitebgs using cached value if possible. 
    "refresh" will ignore cache and refresh the data. 
    If "system_name" is not a string, assume it is an eddbid int.
    '''
    try:
        url = f"{_ELITEBGSURL}systems"
        payload = {'name': system.name, 'factionDetails': 'true'}
        resp = requests.get(url, params=payload)
        myload = json.loads(resp._content)["docs"][0]
    except:
        CSNLog.info(f'Failed to find system "{system.name}"')
        print(f'!Failed to find system "{system.name}"')
        return system

    system.source = 'EBGS'
    system.id = myload['eddb_id']
    system.controllingFaction = myload['controlling_minor_faction_cased']

    for f in myload['factions']:
        fd = f['faction_details']  # Details are in a lower dict
        fp = fd['faction_presence']
        myPresence = Presence(name=f['name'], id=fd['eddb_id'],
                              allegiance=fd['allegiance'].title(), government=fd['government'].title(),
                              influence=round(100*fp['influence'], 2))
        myPresence.isPlayer = isPlayer(myPresence.name)
        for state in fp['pending_states']:
            myState = State(state[state].title(), False)
            myPresence.states.append(myState)
        for state in fp['active_states']:
            myState = State(state['state'].title(), True)
            myPresence.states.append(myState)

        if myPresence.influence > 0:
            system.addfaction(myPresence)

    # Remove Fations that have left since previous data
    system.factions = list(_ for _ in system.factions if _.source == 'EBGS')

    # NREQ += 1
    return system
