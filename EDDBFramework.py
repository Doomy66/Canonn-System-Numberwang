import os
import datetime
import json
from typing import AnyStr
import urllib.request
import tempfile
import pickle


def sysdist(s1, s2):
    '''
    Actual Distance between 2 systems
    '''
    return((s1['x']-s2['x'])**2 + (s1['y']-s2['y'])**2 + (s1['z']-s2['z'])**2) ** 0.5

def cubedist(s1, s2):
    '''
    Cube Distance between 2 systems - The maximum delta
    '''
    return(max(abs(s1['x']-s2['x']) , abs(s1['y']-s2['y']) , abs(s1['z']-s2['z'])))

class EDDBFrame():

    def __init__(self):
        EDDBPOPULATED = 'https://eddb.io/archive/v6/systems_populated.json'
        EDDBFACTIONS = 'https://eddb.io/archive/v6/factions.json'
        EDDBSTAIONS = 'https://eddb.io/archive/v6/stations.json'
        self._eddb_cache = tempfile.gettempdir()+'\EDDBCache_1.pickle'

        ## Get EDDB Data either from local cache or download a dump
        if (not os.path.exists(self._eddb_cache)) or (datetime.datetime.today() - datetime.datetime.fromtimestamp(os.path.getmtime(self._eddb_cache))).seconds > 3*60*60:
            ## Download Nightly Dumps from EDDB if older than 3 hours
            print('Downloading from EDDB Dump...')
            req = urllib.request.Request(EDDBPOPULATED)
            with urllib.request.urlopen(req) as response:
                self.systems = json.loads(response.read().decode('utf8'))

            req = urllib.request.Request(EDDBFACTIONS)
            with urllib.request.urlopen(req) as response:
                self.factions = json.loads(response.read().decode('utf8'))

            req = urllib.request.Request(EDDBSTAIONS)
            with urllib.request.urlopen(req) as response:
                self.stations = json.loads(response.read().decode('utf8'))

            self.savecache()

        else:
            #print('Using Local Cached EDDB Dump...')
            with open(self._eddb_cache, 'rb') as io:
                self.systems = pickle.load(io)
                self.factions = pickle.load(io)
                self.stations = pickle.load(io)
        return

    def savecache(self):
        print('Saving EDDB Dump Cache...')
        with open(self._eddb_cache, 'wb') as io:
            pickle.dump(self.systems,io)
            pickle.dump(self.factions,io)
            pickle.dump(self.stations,io)
        return

    def system(self,idorname):
        ''' 
        Returns System Data given a system name or ID 
        Faction Names and Details are denormalised
        '''
        if type(idorname)==type(1):
            sys = next((x for x in self.systems if x['id'] == idorname),None)
        else:
            sys = next((x for x in self.systems if x['name'] == idorname),None)

        if not sys:
            print(f'! System Not Found : {idorname}')
        else:
            #Denormalise for lazyness
            sys['pf'] = list()
            for mf in sys['minor_faction_presences']:
                f = self.faction(mf['minor_faction_id'])
                if f:
                    mf['name'] = f['name']
                    mf['detail'] = f
                    if f['is_player_faction']:
                        sys['pf'].append(f['name'])

            # NB Edgecase systems like Detention Centers count as populated, but have no minor factions
            sys['minor_faction_presences'].sort(key = lambda x: x['influence'] if x['influence'] else 0, reverse=True)
            sys['influence'] = sys['minor_faction_presences'][0]['influence'] if sys['minor_faction_presences'] else 0
        return sys

    def faction(self,idorname):
        '''
        Returns basic faction details give a faction name or ID
        '''
        ## Player Factions that are unsupported, so can be considered NPC Factions
        ignorepf = ['The Digiel Aggregate','Eternal Sunrise Association','Interstellar Incorporated','Lagrange Interstellar','FDMA Security Service']

        if type(idorname)==type(1):
            f = next((x for x in self.factions if x['id'] == idorname),None)
        else:
            f = next((x for x in self.factions if x['name'] == idorname),None)

        if not f:
            print(f'! Faction Not Found : {idorname}')
        elif f['is_player_faction'] and f['name'] in ignorepf:
            f['is_player_faction'] = False

        return f
        

    def systemscontroled(self,factionname):
        '''
        Returns all Systems controled by the faction
        '''
        #print(f'.Faction Controlled {factionname}')
        ans = list()
        for s in self.systems:
            if s['controlling_minor_faction'] == factionname:
                ans.append(self.system(s['name'])) # Denormalised
        return ans

    def systemspresent(self,factionname):
        '''
        Returns list of systems (Syustem Name only) controled by the faction
        '''
        faction = next((x for x in self.factions if x['name'] == factionname),None)
        if 'faction_presence' not in faction.keys():
            ## not yet cached
            ans = list()
            for sys in self.systems:
                for f in sys['minor_faction_presences']:
                    if f['minor_faction_id'] == faction['id']:
                        ans.append(self.system(sys['name'])) # Denormalised
            faction['faction_presence'] = ans # cache the result
        return faction['faction_presence']

    def cubearea(self,sysname,range):
        '''
         All Populated Systems within the cube around sysname
        '''
        #print(f'.Cube around {sysname}')
        sys = self.system(sysname)
        ans = list()
        if range==30: #expansion request
            if 'xcube' in sys.keys(): #cached
                ans = sys['xcube']
        
        if not ans:
            for s in filter(lambda x: cubedist(x,sys)<=range,self.systems):
                ans.append(self.system(s['name'])) # Denormalised

        if range==30 and 'xcube' not in sys.keys(): # save cache
            sys['xcube'] = ans
        return ans


    def activestates(self,sysname,conflicts=False):
        '''
        Returns active states for all faction in a system, with an option to only report Conflicts
        '''
        ans = list()
        sys = self.system(sysname)
        for f in sys['minor_faction_presences']:
            for state in f['active_states']:
                state['faction'] = f['name']
                if state['name'] in ['Election','War','Civil War'] or not conflicts:
                    ans.append(state)
        return ans

    def natives(self,system):
        '''
        Returns a list of faction names with the system (name or id) as their home system
        '''
        ans = list()
        sys = self.system(system)
        for f in self.factions:
            if f['home_system_id'] == sys['id']:
                ans.append(f['name'])
        return ans

    def getstations(self,sysname):
        sys = self.system(sysname)
        ans = list()
        if sys:
            if 'stations' not in sys.keys():
                for station in filter(lambda x: x['system_id'] == sys['id'],self.stations):
                    ans.append(station)
                sys['stations'] = ans
                sys['beststation'] = 'Orbital' if next((x for x in ans if x['max_landing_pad_size']=='L' and not x['is_planetary'] and x['type_id'] != 24), False) else 'Outpost' if next((x for x in ans if x['max_landing_pad_size']=='M' and not x['is_planetary']), False) else 'Planetary'
                # max_landing_pad_size, is_planetary
            else:
                ans = sys['stations']
        return ans

    def retreatafaction(self,sysname):
        ## Simulate the lowest faction retreating
        sys = self.system(sysname)
        sys['minor_faction_presences'].pop()
        return
    
    def hasretreated(self,sysname,faction):
        knownretreats = list()
        knownretreats.append(["Cnephtha","The Digiel Aggregate"])
        knownretreats.append(["Cephei Sector YZ-Y b4","Jaoi Flag"])
        #Cephei Sector YZ-Y b4 , Jaoi Flag

        #answer = list(filter(lambda x : x[0]==sysname and x[1]==faction,knownretreats))
        answer = [sysname,faction] in knownretreats
        if answer:
            print(f"!{faction} has previously retreated from {sysname}")
            return True
        else:
            return False


if __name__ == '__main__':
    ## Unit Test Harness
    g = EDDBFrame()
    varati = g.system('Varati')
    failed = g.system('I Dont Exist')
    canonn = g.faction('Canonn')
    failed = g.faction('I Dont Exist')
    canonnowned = g.systemscontroled('Canonn')
    canonnspace = g.systemspresent('Canonn')
    aboutvarati = g.cubearea('Varati',30)
    aboutvarati = g.cubearea('Varati',30)
    homesys = g.system(18454)
    stations = g.getstations('Col 285 Sector TZ-O c6-27')

    print('')