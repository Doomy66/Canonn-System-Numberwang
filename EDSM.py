import os
import datetime
import json
import requests
import gzip
from DataClasses import Presence, System, Bubble


def GetSystemsFromEDDB(Faction: str) -> list[System]:
    EDSMPOPULATED = "https://www.edsm.net/dump/systemsPopulated.json.gz"
    edsmcache = os.environ.get('APPDATA')+"\BGS\EDSMPopulated.json"
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
            resp = requests.get(EDSMPOPULATED).content
            resp = json.loads(gzip.decompress(resp))
            print('EDSM Save Raw...')
            with gzip.open(edsmcache, "w") as f:
                f.write(json.dumps(resp).encode('utf-8'))
    except:
        print(f"EDSM Offline !")

    # Load the raw EDSM Data
    print('EDSM Loading...')
    with gzip.open(edsmcache, "r") as f:
        raw = json.loads(f.read().decode('utf-8'))

    print('EDSM Converting to DataClass...')
    systemlist: list(System) = []
    for rs in raw:
        s = System(rs['id'], rs['id64'], rs['name'],
                   rs['coords']['x'], rs['coords']['y'], rs['coords']['z'], rs['allegiance'], rs['government'], rs[
                       'state'], rs['economy'], rs['security'], rs['population'], rs['controllingFaction']['name']
                   )
        if 'factions' in rs.keys():
            for rf in rs['factions']:
                if rf['influence'] > 0:
                    f = Presence(rf['id'], rf['name'], allegiance=rf['allegiance'], government=rf['government'],
                                 influence=round(100*rf['influence'], 2), state=rf['state'], happiness=rf['happiness'], isPlayer=rf['isPlayer'], isNative=s.name in rf['name'])
                    s.addfaction(f)

        systemlist.append(s)

    # Reduce List to Empire and Systems withon 30ly
    if Faction:
        empire = list(
            filter(lambda x: x.isfactionpresent(Faction), systemlist))
        systemlist = list(filter(lambda x: min(
            map(lambda e: e.cube_distance(x, e), empire)) < 30, systemlist))
    print(f'EDSM Converted to include {len(systemlist)} systems')

    return systemlist


if __name__ == '__main__':
    # get Active and Pending States into Faction Presemce !!
    FullBubble = Bubble(GetSystemsFromEDDB('Canonn'))
    myFactionName = 'Canonn'
    mySystemName = 'Khun'
    mySystem: System = FullBubble.getsystem(mySystemName)

    print('System :', mySystem.name)
    mylist = FullBubble.cube_systems(mySystem, range=30,
                                     exclude_presense=myFactionName)
    print(
        f"Targets Via Bubble [{len(mylist)}] {', '.join(x.name for x in mylist)}")

    mylist = FullBubble.faction_presence(myFactionName)
    print(
        f"Faction Presence via Bubble for {myFactionName} [{len(mylist)}] : {', '.join(x.name for x in mylist)}")

    print(f"Faction Native Status in Varati")
    for f in FullBubble.getsystem('Varati').factions:
        print(f" {f.name} - {f.isNative}")
