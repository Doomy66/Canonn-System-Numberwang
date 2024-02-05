import pickle

_EDDBFACTIONS = {}


def HomeSystem(factionname: str) -> str:
    global _EDDBFACTIONS
    """ Returns the Home System (lower) on factionname"""

    def LoadEDDBFactions(location: str = 'EDDBFactions.pickle') -> None:
        """ Loads Pickle, default to same folder loaction"""
        global _EDDBFACTIONS
        eddbf: list = []
        print("EDDB Loading Faction Archive...")
        try:
            with open(location, 'rb') as io:
                eddbf = pickle.load(io)
        except:
            pass

        for f in eddbf:
            if 'home_system' in f.keys():
                _EDDBFACTIONS[f['name'].lower()] = f['home_system'].lower()

        if not _EDDBFACTIONS:
            print('EDDBFactions.pickle not loaded')
            _EDDBFACTIONS = {'None': 'EDDBFactions.pickle not loaded'}

    if not _EDDBFACTIONS:
        LoadEDDBFactions()

    return _EDDBFACTIONS[factionname.lower()] if factionname.lower() in _EDDBFACTIONS.keys() else '<Unkown>'
