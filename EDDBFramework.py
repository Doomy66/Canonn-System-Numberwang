import os
import datetime
import json
import urllib.request

def sysdist(s1, s2):
    '''
    Actual Distance between 2 systems
    '''
    return((s1['x']-s2['x'])**2 + (s1['y']-s2['y'])**2 + (s1['z']-s2['z'])**2) ** 0.5

def cubedist(s1, s2):
    '''
    Cube Distance between 2 systems - The maximum delta
    '''
    return(max((abs(s1['x']-s2['x'])) , abs((s1['y']-s2['y'])) , abs((s1['z']-s2['z']))))

class EDDBFrame():

    def __init__(self):
        EDDBPOPULATED = 'https://eddb.io/archive/v6/systems_populated.json'
        EDDBFACTIONS = 'https://eddb.io/archive/v6/factions.json'
        eddpopulate_cache = 'Data\EDDBSystemCache.json'
        eddfaction_cache = 'Data\EDDBFactionCache.json'

        ## Get EDDB Data either from local cache or download a dump
        if (not os.path.exists(eddpopulate_cache)) or (datetime.datetime.today() - datetime.datetime.fromtimestamp(os.path.getmtime(eddpopulate_cache))).seconds > 3*60*60:
            ## Download Nightly Dumps from EDDB if older than 3 hours
            print('Downloading from EDDB Dump...')
            req = urllib.request.Request(EDDBPOPULATED)
            with urllib.request.urlopen(req) as response:
                self.systems = json.loads(response.read().decode('utf8'))
            with open(eddpopulate_cache, 'w') as io:
                json.dump(self.systems,io)

            req = urllib.request.Request(EDDBFACTIONS)
            with urllib.request.urlopen(req) as response:
                self.factions = json.loads(response.read().decode('utf8'))
            with open(eddfaction_cache, 'w') as io:
                json.dump(self.factions,io)
        else:
            print('Using Local Cached EDDB Dump...')
            with open(eddpopulate_cache, 'r') as io:
                self.systems = json.load(io)
            with open(eddfaction_cache, 'r') as io:
                self.factions = json.load(io)

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
            for mf in sys['minor_faction_presences']:
                f = self.faction(mf['minor_faction_id'])
                mf['name'] = f['name']
            sys['minor_faction_presences'].sort(key = lambda x: x['influence'] if x['influence'] else 0, reverse=True)
        return sys

    def faction(self,idorname):
        '''
        Returns basic faction details give a faction name or ID
        '''
        if type(idorname)==type(1):
            f = next((x for x in self.factions if x['id'] == idorname),None)
        else:
            f = next((x for x in self.factions if x['name'] == idorname),None)

        if not f:
            print(f'! Faction Not Found : {idorname}')
        return f

    def systemscontroled(self,factionname):
        '''
        Returns all Systems controled by the faction
        '''
        print(f'.Faction Controlled {factionname}')
        ans = list()
        for s in self.systems:
            if s['controlling_minor_faction'] == factionname:
                ans.append(self.system(s['name'])) # Denormalised
        return ans

    def systemspresent(self,factionname):
        '''
        Returns all Systems controled by the faction
        '''
        print(f'.Faction Presence {factionname}')
        fid = self.faction(factionname)['id']
        ans = list()
        for sys in self.systems:
            #print(sys['name'])
            for f in sys['minor_faction_presences']:
                if f['minor_faction_id'] == fid:
                    ans.append(self.system(sys['name'])) # Denormalised

        return ans

    def cubearea(self,sysname,range):
        '''
         All Populated Systems within the cube around sysname
        '''
        print(f'.Cube around {sysname}')
        sys = self.system(sysname)
        ans = list()
        for sys in filter(lambda x: cubedist(x,sys)<=range,self.systems):
            ans.append(self.system(sys['name'])) # Denormalised
        return ans


if __name__ == '__main__':
    ## Test Harness
    g = EDDBFrame()
    varati = g.system('Varati')
    failed = g.system('I Dont Exist')
    canonn = g.faction('Canonn')
    failed = g.faction('I Dont Exist')
    canonnowned = g.systemscontroled('Canonn')
    canonnspace = g.systemspresent('Canonn')
    aboutvarati = g.cubearea('Varati',30)

    print('')