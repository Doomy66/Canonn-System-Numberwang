# Defensive Data (or Dirty Deeds) Department
# Routines to assess enemey strengths and weaknesses
from EDDBFramework import EDDBFrame, cubedist as sysdist

friend = "Canonn"
foe = "Marquis du Ma'a" # Just as an example. They are close to us with a decent sized empire, so good for testing

eddb = EDDBFrame()

friendSystems = eddb.systemspresent(friend)
foeSystems = eddb.systemspresent(foe)

for sys in foeSystems:
    friendSystems.sort(key = lambda x: sysdist(sys,x))
    sys['closestfriend'] = next((x for x in friendSystems if x['name'] not in [y['name'] for y in foeSystems]),None) #ignoring systems we share
    sys['frienddist'] = round(sysdist(sys,sys['closestfriend']),1)
    sys['influence'] = round(sys['influence'],1)



# Reports
print('### [DEFENSIVE] High Influnce Within Expansion Range - Prevent These Expanding')
foeSystems.sort(key = lambda x: x['frienddist'])
for sys in foeSystems:
    if sys['influence'] > 65 and sys['frienddist'] <=30:
        eddb.getstations(sys['name'])
        print(f"{sys['name']} ({sys['influence']}%) - {sys['beststation']}".ljust(45)+f"{sys['closestfriend']['name']} ({sys['frienddist']}ly)")
print('')
    

print('### [OFFENSIVE] False Flag Attacks of other Player Groups')
for sys in foeSystems:
    if sys['controlling_minor_faction'] != foe and sys['minor_faction_presences'][0]['detail']['is_player_faction']:
        eddb.getstations(sys['name'])
        foestats = next((x for x in sys['minor_faction_presences'] if x['name'] == foe))
        print(f"{sys['name']} ({round(sys['influence']-foestats['influence'],1)}%) - {sys['beststation']}".ljust(45)+f"{sys['controlling_minor_faction']}")
print('')

print('### [OFFENSIVE] False Flag Attacks BY other Player Groups')
for sys in foeSystems:
    if sys['controlling_minor_faction'] == foe :
        eddb.getstations(sys['name'])
        for foestats in sys['minor_faction_presences'][1:]:
            if foestats['detail']['is_player_faction']:
                print(f"{sys['name']} ({round(sys['influence']-foestats['influence'],1)}%) - {sys['beststation']}".ljust(45)+f"{foestats['name']}")
print('')

print ('*Done*')
