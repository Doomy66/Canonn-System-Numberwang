import pickle

_EDDBHOME = {}
_EDDPLAYER = {}


def HomeSystem(factionname: str) -> str:
    """ Returns the Home System (lower) on factionname"""
    global _EDDBHOME
    if not _EDDBHOME:
        LoadEDDBFactions()
    return _EDDBHOME[factionname.lower()] if factionname.lower() in _EDDBHOME.keys() else '<Unkown>'


def isPlayer(factionname: str) -> bool:
    """ Returns the Home System (lower) on factionname"""
    global _EDDPLAYER
    if not _EDDPLAYER:
        LoadEDDBFactions()
    return _EDDPLAYER[factionname.lower()] if factionname.lower() in _EDDPLAYER.keys() else False


def LoadEDDBFactions(location: str = 'EDDBFactions.pickle') -> None:
    """ Loads Pickle, default to same folder loaction"""
    global _EDDBHOME, _EDDPLAYER
    eddbf: list = []
    print("EDDB Loading Faction Archive...")
    try:
        with open(location, 'rb') as io:
            eddbf = pickle.load(io)
    except:
        pass

    for f in eddbf:
        if 'home_system' in f.keys():
            _EDDBHOME[f['name'].lower()] = f['home_system'].lower()
        if 'is_player_faction' in f.keys():
            _EDDPLAYER[f['name'].lower()] = f['is_player_faction']

    if not _EDDBHOME:
        print('EDDBFactions.pickle not loaded')
        _EDDBHOME = {'None': 'EDDBFactions.pickle not loaded'}
