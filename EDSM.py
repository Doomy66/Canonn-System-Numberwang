import os
import datetime
import json
import requests
import gzip
from DataClassesBase import Presence, System, Bubble, State
import CSNSettings


def GetSystemsFromEDSM(Faction: str, range=40) -> list[System]:
    """ Reads latest daily download of populated systems from EDSM and creates a list of System Objects \n
        If a Faction is supplied, the list is cut down to that Faction and others withing range ly Cube
    """
    edsmcache = os.environ.get('APPDATA')+"\CSN_EDSMPopulated.json"

    def RefreshCache(edsmcache):
        """ Checks Dates of Cache and API Data and downloads if required """
        EDSMPOPULATED = "https://www.edsm.net/dump/systemsPopulated.json.gz"
        cachedate: datetime.datetime = datetime.datetime.strptime(
            '2000-01-01', '%Y-%m-%d')

        # Get Modified Dates to check if it needs downloading again
        if os.path.exists(edsmcache):
            cachedate = datetime.datetime.fromtimestamp(
                os.path.getmtime(edsmcache))

        try:
            resp = requests.head(EDSMPOPULATED)
            lastmoddt = datetime.datetime.strptime(
                resp.headers._store['last-modified'][1], '%a, %d %b %Y %H:%M:%S %Z')

            # Needs to download fresh data
            if lastmoddt > cachedate:
                print('EDSM Downloading...')
                CSNSettings.CSNLog.info('EDSM Downloading...')

                resp = requests.get(EDSMPOPULATED).content
                resp = json.loads(gzip.decompress(resp))
                print('EDSM Save Raw...')
                with gzip.open(edsmcache, "w") as f:
                    f.write(json.dumps(resp).encode('utf-8'))
        except:
            print(f"EDSM Offline !")

    def LoadCache(edsmcache) -> list:
        print('EDSM Loading...')
        with gzip.open(edsmcache, "r") as f:
            raw = json.loads(f.read().decode('utf-8'))
        return raw

    RefreshCache(edsmcache)
    raw = LoadCache(edsmcache)

    print('EDSM Converting to DataClass...')
    CSNSettings.CSNLog.info('EDSM Converting to DataClass...')

    systemlist: list(System) = []
    for rs in raw:
        s = System('EDSM', rs['id'], rs['id64'], rs['name'],
                   rs['coords']['x'], rs['coords']['y'], rs['coords']['z'], rs['allegiance'], rs['government'], rs[
                       'state'], rs['economy'], rs['security'], rs['population'], rs['controllingFaction']['name']
                   )
        # Add Faction Presences
        if 'factions' in rs.keys():
            for rf in rs['factions']:
                if rf['influence'] > 0:
                    f = Presence(rf['id'], rf['name'], allegiance=rf['allegiance'], government=rf['government'],
                                 influence=round(100*rf['influence'], 2), happiness=rf['happiness'], isPlayer=rf['isPlayer'])
                    # Add States of Faction. NB States have very little information in EDSM
                    if 'activeStates' in rf.keys():
                        for rstate in rf['activeStates']:
                            f.states.append(State(rstate['state'], True))
                    if 'pendingStates' in rf.keys():
                        for rstate in rf['pendingStates']:
                            f.states.append(State(rstate['state'], False))
                    s.addfaction(f)

        systemlist.append(s)

    # Reduce List to Empire and Systems within range (40 covers simple invasions, use 60 for extended)
    if Faction:
        empire = list(
            filter(lambda x: x.isfactionpresent(Faction), systemlist))
        systemlist = list(filter(lambda x: min(
            map(lambda e: e.cube_distance(x, e), empire)) <= range, systemlist))
    print(f'EDSM Converted to include {len(systemlist)} systems')

    return systemlist


if __name__ == '__main__':
    # Some Tests and Examples
    myFactionName = os.environ.get('myfaction')
    myBubble = Bubble(GetSystemsFromEDSM(myFactionName))

    mySystemName = 'Khun'
    mySystem: System = myBubble.getsystem(mySystemName)
    print('System :', mySystem.name)

    systems = myBubble.cube_systems(mySystem, exclude_presense=myFactionName)
    print(
        f"Targets for {mySystemName} Via Bubble [{len(systems)}] {', '.join(x.name for x in systems)}")

    systems = myBubble.faction_presence(myFactionName)
    print(
        f"Faction Presence via Bubble for {myFactionName} [{len(systems)}] : {', '.join(x.name for x in systems)}")

    print(f"Faction Native Status in Varati")
    for f in myBubble.getsystem('Varati').factions:
        print(f" {f.name} - {f.isNative}")
