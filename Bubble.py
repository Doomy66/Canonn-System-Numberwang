import os
import sys
import json
import gzip
from os import name, system

import CSNSettings
from datetime import datetime
import api

journalfolder = os.environ.get('USERPROFILE') + f'\\Saved Games\\Frontier Developments\\Elite Dangerous'
harddrive = os.environ.get('USERPROFILE') + f'\\Downloads\\'

def filetimestamp(file):
    try:
        return datetime.utcfromtimestamp(os.path.getmtime(file))
    except:
        return None

def dist(x1, x2, y1, y2, z1=0, z2=0):
    """Distance between 2 points in 2 or 3d"""
    return ((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2) ** 0.5

def EliteBGSDateTime(s):
    '''
    Converts Eligte BGS DateTime string to DateTime
    '''
    dformat = '%Y-%m-%dT%H:%M:%S'  # so much grief from this function
    return(datetime.strptime(s[:len(dformat) + 2], dformat))

def whereami():
    try:
        with open(journalfolder+'\\NavRoute.json', 'r') as io:
            return json.load(io)['Route'][-1]['StarSystem']
    except:
        return

def update_progress(progress,status=''):
    # update_progress() : Displays or updates a console progress bar
    ## Accepts a float between 0 and 1. Any int will be converted to a float.
    ## A value under 0 represents a 'halt'.
    ## A value at 1 or bigger represents 100%
    barLength = 30 # Modify this to change the length of the progress bar
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float".ljust(40)+"\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...+".ljust(40)+"\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...".ljust(40)+"\r\n"
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), round(progress*100,1), status.ljust(40))
    sys.stdout.write(text)
    sys.stdout.flush()

class Bubble():
    factionnames = CSNSettings.factionnames

    localdrive = 'data\\'
    SPANSHFULL = f'{harddrive}galaxy.json.gz'
    SPANSH7DAY = f'{harddrive}galaxy_7days.json.gz'
    SPANSH1MON = f'{harddrive}galaxy_1month.json.gz'
    DTFILE = f'{localdrive}deep_thought.json'
   
    def __init__(self):
        # systems with faction presence, full uptodate detail
        self.lastick = api.getlasttick()

        self.localspace = self.refreshcache()

        # all nearby systems, has only stale or structural data
        if os.path.exists(self.DTFILE):
            with open(self.DTFILE,'r') as istream:
                self.systems = json.load(istream)
                lastUpdated = filetimestamp(self.DTFILE)
        else:
            self.systems = list()
            self.saveDeepThought()
            lastUpdated = None
        
        if filetimestamp(self.SPANSHFULL) != None and (lastUpdated == None or lastUpdated < filetimestamp(self.SPANSHFULL)):
            self.ReadSpanch(self.SPANSHFULL)
            self.saveDeepThought()
        elif filetimestamp(self.SPANSH7DAY) != None and (lastUpdated == None or lastUpdated < filetimestamp(self.SPANSH7DAY)):
            self.ReadSpanch(self.SPANSH7DAY)
            self.saveDeepThought()
        elif filetimestamp(self.SPANSH1MON) != None and (lastUpdated == None or lastUpdated < filetimestamp(self.SPANSH1MON)):
            self.ReadSpanch(self.SPANSH1MON)
            self.saveDeepThought()

    def saveDeepThought(self):
        print('Saving...')
        with open(self.DTFILE, 'w') as outfile:
            json.dump(self.systems, outfile)

    def ReadSpanch(self,ifile):
        # Reads a full Spansh dump, extracts all systems close to Canonn Space
        radius = 30
        rebuild = True
        
        print('Deep Thought...')
        nyes = nno = nnew = 0
        
        with gzip.open(ifile,"r") as bstream:
            while True:
                l = bstream.readline().decode()
                t = l.rstrip('\n').rstrip(',')
                if len(t) > 6 != '':
                    t = json.loads(t)
                    d = self.canonndistcube(t) 
                    if d <= radius:
                        t['CanonnDist'] = self.canonndist(t) 
                        t['CanonnDistCube'] = d
                        nyes += 1
                        try:
                            id = next(i for i, x in enumerate(self.systems) if x['name'] == t['name'])
                            if t['date'] != self.systems[id]['date'] or rebuild:
                                #print(f"Update {t['date']} {t['name']}  {nyes:,}")
                                self.systems[id] = t 
                                if self.systems[id].get('population',0) > 0 and (rebuild or not 'natives' in self.systems[id]):
                                    self.systems[id]['natives'] = api.eddbNatives(t['name'])
                        except StopIteration:
                            nnew += 1
                            print(f"New {t['date']} {t['name']}  {nnew:,}")
                            self.systems.append(t)
                            id = len(self.systems)-1
                            if self.systems[id].get('population',0) > 0 and (rebuild or not 'natives' in self.systems[id]):
                                self.systems[id]['natives'] = api.eddbNatives(t['name'])
                    else:
                        nno += 1
                        if nno % 500000 == 0:
                            print(f'... {nno:,}')
                if not l :
                    break
        return None

    def SpamSpanch(self,ifile):
        # Reads a full Spansh dump, extracts all systems close to Canonn Space
      
        print('Deep Thought...')
        nyes = nno = nnew = 0
        lookingfor = ['Kyli Flyuae AA-A h4']
        with gzip.open(ifile,"r") as bstream:
            while True:
                l = bstream.readline().decode()
                t = l.rstrip('\n').rstrip(',')
                if len(t) > 6 != '':
                    t = json.loads(t)

                    if t['name'] in lookingfor:
                        nyes += 1
                        for b in t['bodies']:
                            pass
                    else:
                        nno += 1
                        if nno % 500000 == 0:
                            print(f'... {nno:,}')
                if not l :
                    break
        return None

    def refreshcache(self):
        print(f'Refreshing BGS Data for {self.factionnames}:',end='')

        myfile = 'data\\LocalSpace.json'
        if not(os.path.isfile(myfile)):
            localSpace = dict()
        else:
            with open(myfile, 'r') as io:
                localSpace = json.load(io)


        # List of all systems the faction has a presence in.
        # This is the master structure that has additional data attached used for processing later
        faction_systems = list()
        for faction in self.factionnames:
            faction_systems += api.getfaction(faction)['faction_presence']

        # Loop through all the systems that the faction is present in
        for counter, sys in enumerate(faction_systems):
            update_progress(counter/len(faction_systems),sys['system_name'])
            # Previous Run
            # NB updated_at do not always match between Faction and System
            if sys['system_name'] in localSpace and localSpace[sys['system_name']] and sys['updated_at'] == localSpace[sys['system_name']]['updated_at']:
                # Same or broken api call
                pass
            else:
                localSpace[sys['system_name']] = api.getsystem(sys['system_name'],True)
                if not localSpace[sys['system_name']]:
                    continue
                localSpace[sys['system_name']]['empire'] = sys['empire']
                localSpace[sys['system_name']]['happytext'] = sys['happytext']
                localSpace[sys['system_name']]['happiness'] = sys['happiness']
                localSpace[sys['system_name']]['stations'] = api.getstations(sys['system_name'])

                localSpace[sys['system_name']]['sellsTritium'] = False
                for station in localSpace[sys['system_name']]['stations']:
                    if station['economy'] == '$economy_refinery' and station['type'] != 'crateroutpost' :
                        localSpace[sys['system_name']]['sellsTritium'] = True
                        break

                for f in localSpace[sys['system_name']]['factions']:
                    if f['name'] == sys['empire']:
                        localSpace[sys['system_name']]['empire'] = f
                        break

            localSpace[sys['system_name']]['fresh'] = self.lastick < EliteBGSDateTime(localSpace[sys['system_name']]['updated_at'])



        # Save Faction File
        with open(myfile, 'w') as io:
            json.dump(localSpace, io)

        update_progress(1,'Base Date Generated')
        return localSpace

    def canonndist(self,sys):
        '''
        Returns the minimum direct distance of a system to ANY local system
        '''
        closest = None
        for n,x in enumerate(self.localspace):
            cs = self.localspace[x]
            d = dist(sys['coords']['x'],cs['x'],sys['coords']['y'],cs['y'],sys['coords']['z'],cs['z'])
            if closest == None or d < closest:
                closest = d
        return closest

    def canonndistcube(self,sys):
        '''
        Returns the minimum coord delta of a system to ANY local system (expansion rules)
        '''

        closest = None
        for n,x in enumerate(self.localspace):
            cs = self.localspace[x]
            d = max([abs(sys['coords']['x']-cs['x']),abs(sys['coords']['y']-cs['y']),abs(sys['coords']['z']-cs['z'])])
            if closest == None or d < closest:
                closest = d
        return closest

    def findsystem(self,nameorid):
        try:
            if type(nameorid) is str:
                id = next(i for i, x in enumerate(self.systems) if x['name'] == nameorid)
            else:
                id = next(i for i, x in enumerate(self.systems) if x['id64'] == nameorid)
            if id:
                self.systems[id]['system_name'] = self.systems[id]['name'] #TODO should fix source data
                self.systems[id]['x'] = self.systems[id]['coords']['x']
                self.systems[id]['y'] = self.systems[id]['coords']['y']
                self.systems[id]['z'] = self.systems[id]['coords']['z']
                self.systems[id]['factions'].sort(key = lambda x: x['influence'], reverse=True)
                
            return self.systems[id]
        except StopIteration:
            #print(f'!System not found {nameorid}')
            return None
            
    def findlocalsystem(self,system_name):
        '''
        Return system details from local space or api
        '''
        if system_name in self.localspace:
            return self.localspace[system_name]
        else:
            return api.getsystem(system_name)

    def systemSellsTritium(self,system_name):
        sys = self.localspace(system_name)
        # TODO Stations not tested.
        for station in sys['stations']:
            if station.get('primaryEconomy','') == 'Refinery' and 'Planetary' not in station['type']:
                return True
        return False 

    def currentinf(self,system_name,faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction:
                return f['influence']
        return None

    def dayswon(self,system_name, faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction and len(f['conflicts'])>0:
                return f['conflicts'][0]['days_won']
        return(0)

    def assetatrisk(self,system_name, faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction and len(f['conflicts'])>0:
                return f['conflicts'][0]['stake']
        return('')





if __name__ == '__main__':
    bubble = Bubble()
    print(F'Done in {api.NREQ}')
    #bubble.SpamSpanch(bubble.SPANSH1MON)