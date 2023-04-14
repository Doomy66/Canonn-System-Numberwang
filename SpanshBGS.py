from Bubble import update_progress
import os
import datetime
import json
from typing import AnyStr
import pickle
import api
import requests
from CSNSettings import ignorepf
import requests
import gzip
import json

def sysdist(s1, s2):
    '''
    Actual Distance between 2 systems
    '''
    return((s1['coords']['x']-s2['coords']['x'])**2 + (s1['coords']['y']-s2['coords']['y'])**2 + (s1['coords']['z']-s2['coords']['z'])**2) ** 0.5

def cubedist(s1, s2):
    '''
    Cube Distance between 2 systems - The maximum delta
    '''
    return(max(abs(s1['coords']['x']-s2['coords']['x']) , abs(s1['coords']['y']-s2['coords']['y']) , abs(s1['coords']['z']-s2['coords']['z'])))

class SpanshBGS():

    def __init__(self):
        SPANSHPOPULATED = "https://downloads.spansh.co.uk/galaxy_populated.json.gz"

        self._data_dir = 'data'
        self._spanshcache = os.path.join(self._data_dir, 'SpanshCache_1.pickle')
        self._ebgs_systemhist_cache = os.path.join(self._data_dir, 'EBGS_SysHist.pickle')
        self._eddb_factions = 'EDDBFactions.pickle' ## Archive from end of EDDB - In ROOT not in Data
        self.systemhist = list()
        self.factions = list()  ## Saved from EDDB

        # Get Modified Dates to check if it needs downloading again
        if os.path.exists(self._spanshcache):
            cachedate = datetime.datetime.fromtimestamp(os.path.getmtime(self._spanshcache))
        resp = requests.head(SPANSHPOPULATED)
        lastmoddt = datetime.datetime.strptime(resp.headers._store['last-modified'][1],'%a, %d %b %Y %H:%M:%S %Z')
        ## print(cachedate,lastmoddt,lastmoddt > cachedate)

        ## Get Cache Data either from local cache or download a dump
        if (not os.path.exists(self._spanshcache)) or lastmoddt > cachedate:
            print('Downloading Dump for Cache...')
            ## Download Nightly Dump if older local cache
            resp = requests.get(SPANSHPOPULATED)
            #content = resp.content
            self.systems = json.loads(gzip.decompress(resp.content).decode('utf-8'))
            print('Cleaning Dump for Cache...')
            for sys in self.systems: ## Strip Useless Data
                x = sys.pop('bodies',None)
                if 'factions' not in sys.keys():            ## Thargoid Controled
                    sys['factions'] = list()
                for station in sys['stations']:
                    if station['controllingFaction'] == 'FleetCarrier' or station['type']=='Mega ship':
                        sys['stations'].remove(station)     ## Kill non-staions
                    else:
                        x = station.pop('market','')        ## Kill data
                        x = station.pop('outfitting','')    ## Kill data
                        x = station.pop('shipyard','')      ## Kill data
                        x = station.pop('services','')      ## Kill data

            with open(self._eddb_factions, 'rb') as io:
                self.factions = pickle.load(io)

            self.savecache()
            self.retreatsload()
            # Clear Memory
            #content = None
            resp = None
            self.systems = None
           
        
        print('Using Local Cached Dump...')
        with open(self._spanshcache, 'rb') as io:
            self.systems = pickle.load(io)
            self.factions = pickle.load(io)
        self.retreatsload(False) 
        return

    def savecache(self):
        print('Saving Dump Cache...')

        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._spanshcache, 'wb') as io:
            pickle.dump(self.systems,io)
            pickle.dump(self.factions,io)
        
        # Apply all known factions to the known cache
        for s in self.systemhist:
            x=self.system(s['name'])
        return

    def retreatsload(self,refresh=True):
        self.systemhist = list()
        if os.path.exists(self._ebgs_systemhist_cache):
            with open(self._ebgs_systemhist_cache, 'rb') as io:
                self.systemhist = pickle.load(io)
        if refresh:
            self.retreatsrefresh()
        return

    def retreatssave(self):
        '''
        Called inside any function whenever the retreats data changes
        '''
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._ebgs_systemhist_cache, 'wb') as io:
            pickle.dump(self.systemhist,io)
        return

    def retreatsrefresh(self):
        '''
        Update any cached retreat data with latest data from eddb
        '''
        saves = 0
        for i,hist in enumerate(self.systemhist):
            update_progress(i/len(self.systemhist),'Retreat Refresh')
            sys = next((x for x in self.systems if x['name'] == hist['name']), None)
            if sys and 'factions' in sys.keys():
                for f in sys['factions']:
                    if f['name'] not in hist['factions']:
                        saves += 1
                        hist['factions'].append(f['name'])
        if saves:
            print(f'{saves} Expansions Detected')
            self.retreatssave()
        update_progress(1)
        
        return

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

    def system(self,idorname,live=False):
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
            for mf in sys['factions']:
                f = self.faction(mf['name'])
                if f:
                    mf['detail'] = f
                    if f['is_player_faction']:
                        sys['pf'].append(f['name'])

            ## Get live ebgs data when the dump is just not good enough
            if live and 'ebgs' not in sys.keys():
                if ebgs := api.getsystem(sys['name']): # Some systems are missing or named differently
                    sys['ebgs'] = ebgs
                    for f in sys['factions']:
                        newinf = next((x for x in ebgs['factions'] if x['name']==f['name']),{'influence':0})
                        if newinf: # Faction may have retreated
                            newinf = newinf['influence']
                            f['influence'] = newinf
                        else:
                            print('Bug')

            sys['numberoffactions'] = len(sys['factions'])

            # NB Edgecase systems like Detention Centers count as populated, but have no minor factions
            sys['factions'].sort(key = lambda x: x['influence'] if x['influence'] else 0, reverse=True)
            sys['influence'] = sys['factions'][0]['influence'] if sys['factions'] else 0

            # Additional data from other sources
            sys['historic'] = self.retreats(sys['name'])

        if sys and 'coords' in sys.keys() and 'x' not in sys.keys():
            sys['x'] = sys['coords']['x']
            sys['y'] = sys['coords']['y']
            sys['z'] = sys['coords']['z']

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
            if 'controllingFaction' in s.keys() and s['controllingFaction']['name'] == factionname:
                ans.append(self.system(s['name'],live=live)) # Denormalised
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
                if 'factions' in sys.keys():
                    for f in sys['factions']:
                        if f['name'] == faction['name']:
                            ans.append(self.system(sys['name'],live=live)) # Denormalised
            faction['faction_presence'] = ans # cache the result
        return faction['faction_presence']

    def cubearea(self,sysname,range,live=False):
        '''
         All Populated Systems within the cube around sysname
        '''
        #print(f'.Cube around {sysname}')
        sys = self.system(sysname,live=live)
        ans = list()
        if range==30: #expansion request
            if 'xcube' in sys.keys(): #cached
                ans = sys['xcube']
        
        if not ans:
            for s in filter(lambda x: cubedist(x,sys)<=range,self.systems):
                ans.append(self.system(s['name'],live=False)) # Denormalised

        if range==30 and 'xcube' not in sys.keys(): # save cache
            sys['xcube'] = ans
        return ans

    def activestates(self,sysname,conflicts=False,live=False):
        '''
        Returns active states for all faction in a system, with an option to only report Conflicts
        '''
        ans = list()
        sys = self.system(sysname,live=live)
        for f in sys['factions']:               ## Only 1 State in Spansh
            if (f['state'] in ['Election','War','Civil War'] or not conflicts) and(f['state'] not in ans) and (f['state'] != 'None'):
                ans.append(f['state'])
        return ans

    def natives(self,system):
        '''
        Returns a list of faction names with the system name as their home system
        '''
        ans = list()
        sys = self.system(system)
        for faction in self.factions:
            if faction['home_system'] == sys['name']:
                ans.append(faction['name'])
        return ans

    def getstations(self,sysname,live=False): ## !! Pads etc
        sys = self.system(sysname,live=live)
        ans = list()
        if sys:
            if 'stations' not in sys.keys() or not sys['stations']:
                sys['stations'] = list()
                sys['beststation'] = 'Planetary'
            else:
                ans = sys['stations']                
                sys['beststation'] = 'Orbital' if next((x for x in ans if ('Starport' in x['type'] or 'Asteroid' in x['type'] )), False) else 'Outpost' if next((x for x in ans if x['type']=='Outpost'), False) else 'Planetary'
        return ans

    def retreatafaction(self,sysname):
        ## Simulate the lowest faction retreating
        sys = self.system(sysname)
        sys['minor_faction_presences'].pop()
        return
    


if __name__ == '__main__':
    ## Unit Test Harness
    g = SpanshBGS()  

    """
    e = EDDBFramework.EDDBFrame()
    for f in g.factions:
        sys = next((x for x in e.systems if x['id'] == f['home_system_id']),None)
        f['home_system'] = sys['name'] if sys else '<Unknown>'
    
    with open(g._eddb_factions, 'wb') as io:
        pickle.dump(g.factions,io)
    with open(g._eddb_factions+'.json', 'w') as io:
        io.write(json.dumps(g.factions))
    """


    khun = g.system('Khun',live=True)
    varati = g.system('Varati')
    failed = g.system('I Dont Exist')
    canonn = g.faction('Canonn')
    failed = g.faction('I Dont Exist')
    Sawadbhakui = g.system('Sawadbhakui')
    canonnowned = g.systemscontroled('Canonn')
    canonnspace = g.systemspresent('Canonn')
    aboutvarati20 = g.cubearea('Varati',20)
    aboutvarati30 = g.cubearea('Varati',30)
    stationsT = g.getstations('Col 285 Sector TZ-O c6-27') ## Non - Thargoid Invaded
    stationsV = g.getstations('Col 285 Sector UZ-O c6-23')  ## Planet
    states = g.activestates('Chacobog')

    print('')