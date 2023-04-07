from Bubble import update_progress
import os
import datetime
import json
from typing import AnyStr
import urllib.request
import tempfile
import pickle
import api

## import requests
from CSNSettings import ignorepf

class EDDBFrame():

    def __init__(self):
        ## EDDBPOPULATED = 'https://eddb.io/archive/v6/systems_populated.json'
        ## EDDBFACTIONS = 'https://eddb.io/archive/v6/factions.json'
        ## EDDBSTAIONS = 'https://eddb.io/archive/v6/stations.json'
        #self._eddb_cache = tempfile.gettempdir()+'\EDDBCache_1.pickle'
        self._data_dir = 'data'
        self._eddb_cache = os.path.join(self._data_dir, 'EDDBCache_1.pickle')
        self._ebgs_systemhist_cache = os.path.join(self._data_dir, 'EBGS_SysHist.pickle')
        self.systemhist = list()
        self.systems = list()
        self.factions = list()
        self.stations = list()

        """
        EDDB Closed Down
            ## Get EDDB Data either from local cache or download a dump
            if (not os.path.exists(self._eddb_cache)) or (datetime.datetime.today() - datetime.datetime.fromtimestamp(os.path.getmtime(self._eddb_cache))).seconds > 3*60*60:
                ## Download Nightly Dumps from EDDB if older than 3 hours
                print('Downloading from EDDB Dump...')
                if False: # Started to fail with SSL Issues
                    req = urllib.request.Request(EDDBPOPULATED)
                    with urllib.request.urlopen(req) as response:
                        self.systems = json.loads(response.read().decode('utf8'))

                    req = urllib.request.Request(EDDBFACTIONS)
                    with urllib.request.urlopen(req) as response:
                        self.factions = json.loads(response.read().decode('utf8'))

                    req = urllib.request.Request(EDDBSTAIONS)
                    with urllib.request.urlopen(req) as response:
                        self.stations = json.loads(response.read().decode('utf8'))
                else:
                    req = requests.get(EDDBPOPULATED)
                    self.systems = req.json()
        
                    req = requests.get(EDDBFACTIONS)
                    self.factions = req.json()

                    req = requests.get(EDDBSTAIONS)
                    self.stations = req.json()
                self.savecache()
                self.retreatsload()
            else:
                #print(datetime.datetime.today(),datetime.datetime.fromtimestamp(os.path.getmtime(self._eddb_cache)),(datetime.datetime.today() - datetime.datetime.fromtimestamp(os.path.getmtime(self._eddb_cache))).seconds)
                #print('Using Local Cached EDDB Dump...')
                with open(self._eddb_cache, 'rb') as io:
                    self.systems = pickle.load(io)
                    self.factions = pickle.load(io)
                    self.stations = pickle.load(io)
                self.retreatsload(False)
        """

        if (os.path.exists(self._eddb_cache)):
            with open(self._eddb_cache, 'rb') as io:
                self.systems = pickle.load(io)
                self.factions = pickle.load(io)
                self.stations = pickle.load(io)
            self.retreatsload(False)

        return 

    """
    def savecache(self):
        print('Saving EDDB Dump Cache...')
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._eddb_cache, 'wb') as io:
            pickle.dump(self.systems,io)
            pickle.dump(self.factions,io)
            pickle.dump(self.stations,io)
        
        # Apply all known factions to the known cache
        for s in self.systemhist:
            x=self.system(s['name'])
        return
    """

    def retreatsload(self,refresh=True): ## Refresh not possible due to EDDB Closed
        self.systemhist = list()
        if os.path.exists(self._ebgs_systemhist_cache):
            with open(self._ebgs_systemhist_cache, 'rb') as io:
                self.systemhist = pickle.load(io)
        ## if refresh:
        ##    self.retreatsrefresh()
        return

    def retreatssave(self):
        '''
        Called inside any function whenever the retreats data changes
        '''
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._ebgs_systemhist_cache, 'wb') as io:
            pickle.dump(self.systemhist,io)
        return

    ## Refresh not possible due to EDDB Closed
    """
    def retreatsrefresh(self):
        '''
        Update any cached retreat data with latest data from eddb
        '''
        saves = 0
        for i,hist in enumerate(self.systemhist):
            update_progress(i/len(self.systemhist),'Retreat Refresh')
            sys = next((x for x in self.systems if x['name'] == hist['name']), None)
            if sys:
                for f in sys['minor_faction_presences']:
                    if self.faction(f['minor_faction_id'])['name'] not in hist['factions']:
                        saves += 1
                        hist['factions'].append(self.faction(f['minor_faction_id'])['name'])
        if saves:
            print(f'{saves} Expansions Detected')
            self.retreatssave()
        update_progress(1)
        
        return
    """

    def retreats(self,system_name):
        ''' 
        Not actualy retreats, but a list of factions that have EVER been in system
        Retreats can then be inferred
        '''
        cached = next((x for x in self.systemhist if x['name'] == system_name),None)
        if not cached:
            answer = api.factionsovertime(system_name)
            self.systemhist.append({'name':system_name, 'factions':answer})
            self.retreatssave()
        else:
            answer = cached['factions']
        return answer


    def system(self,idorname,live=True):
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
        elif not 'pf' in sys.keys() or (live and 'ebgs' not in sys.keys()):
            #Denormalise for lazyness
            sys['pf'] = list()
            for mf in sys['minor_faction_presences']:
                f = self.faction(mf['minor_faction_id'])
                if f:
                    mf['name'] = f['name']
                    mf['detail'] = f
                    if f['is_player_faction']:
                        sys['pf'].append(f['name'])

            ## Get live ebgs data when the dump is just not good enough
            if live and 'ebgs' not in sys.keys():
                if ebgs := api.getsystem(sys['name']): # Some systems are missing or named differently
                    sys['ebgs'] = ebgs
                    for f in sys['minor_faction_presences']:
                        newinf = next((x for x in ebgs['factions'] if x['name']==f['name']),{'influence':0})
                        if newinf: # Faction may have retreated
                            newinf = newinf['influence']
                            f['influence'] = newinf
                        else:
                            print('Bug')

            sys['numberoffactions'] = len(sys['minor_faction_presences'])

            # NB Edgecase systems like Detention Centers count as populated, but have no minor factions
            sys['minor_faction_presences'].sort(key = lambda x: x['influence'] if x['influence'] else 0, reverse=True)
            sys['influence'] = sys['minor_faction_presences'][0]['influence'] if sys['minor_faction_presences'] else 0

            # Additional data from other sources
            sys['historic'] = self.retreats(sys['name'])




        return sys

    def faction(self,idorname):
        '''
        Returns basic faction details give a faction name or ID
        '''
        ## Player Factions that are unsupported, so can be considered NPC Factions
        
        if type(idorname)==type(1):
            f = next((x for x in self.factions if x['id'] == idorname),None)
        else:
            f = next((x for x in self.factions if x['name'] == idorname),None)

        if not f:
            print(f'! Faction Not Found : {idorname}')
        elif f['is_player_faction'] and f['name'] in ignorepf:
            f['is_player_faction'] = False

        return f
        

    def systemscontroled(self,factionname, live=False):
        '''
        Returns all Systems controled by the faction
        '''
        #print(f'.Faction Controlled {factionname}')
        ans = list()
        for s in self.systems:
            if s['controlling_minor_faction'] == factionname:
                ans.append(self.system(s['name'])) # Denormalised
        return ans

    def systemspresent(self,factionname,live=False):
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
    

def cubedist(s1, s2):
    '''
    Cube Distance between 2 systems - The maximum delta
    '''
    return(max(abs(s1['x']-s2['x']) , abs(s1['y']-s2['y']) , abs(s1['z']-s2['z'])))

if __name__ == '__main__':
    ## Unit Test Harness
    g = EDDBFrame()
    khun = g.system('Khun')
    varati = g.system('Varati')
    failed = g.system('I Dont Exist')
    canonn = g.faction('Canonn')
    failed = g.faction('I Dont Exist')
    Sawadbhakui = g.system('Sawadbhakui')
    canonnowned = g.systemscontroled('Canonn')
    canonnspace = g.systemspresent('Canonn')
    aboutvarati = g.cubearea('Varati',30)
    aboutvarati = g.cubearea('Varati',30)
    homesys = g.system(18454)
    stations = g.getstations('Col 285 Sector TZ-O c6-27')

    print('')