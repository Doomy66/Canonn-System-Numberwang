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
        print(f"{sys['name']} ({sys['influence']}%)".ljust(34)+f"{sys['closestfriend']['name']} ({sys['frienddist']}ly)")
print('')
    
print ('')