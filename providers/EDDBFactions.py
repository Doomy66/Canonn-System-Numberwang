import pickle
from dataclasses import dataclass


@dataclass
class fdetails:
    """ Faction Details from the deceased EDDB data. EDDB is the best (only) known source of homesystem for player and special unique Factions """
    homesystem: str = '<Unknown>'
    isPlayer: bool = False


# GLOBAL
EDDBFACTIONS = {}


def HomeSystem(factionname: str) -> str:
    """ Returns the Home System (lowercase) on factionname"""
    global EDDBFACTIONS
    if not EDDBFACTIONS:
        LoadEDDBFactions()
    return EDDBFACTIONS.get(factionname.lower(), fdetails()).homesystem


def isPlayer(factionname: str) -> bool:
    """ Returns True if the factionname is a Player Created Faction """
    global EDDBFACTIONS
    if not EDDBFACTIONS:
        LoadEDDBFactions()
    answer = EDDBFACTIONS.get(factionname.lower(), fdetails()).isPlayer
    return answer


def LoadEDDBFactions(location: str = 'resources\EDDBFactions.pickle') -> None:
    """ Loads Pickle, default to same folder loaction"""
    global EDDBFACTIONS
    eddbf: list = []
    print("EDDB Loading Faction Archive...")
    try:
        with open(location, 'rb') as io:
            eddbf = pickle.load(io)
    except:
        pass

    for f in eddbf:
        EDDBFACTIONS[f['name'].lower()] = fdetails(
            f.get('home_system'.lower(), '<Unknown>'), f.get('is_player_faction', False))

    if not eddbf:
        print('EDDBFactions.pickle not loaded')
        EDDBFACTIONS = {'None': fdetails()}
