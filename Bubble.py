import os
import sys
import json

import CSNSettings
from datetime import datetime
import api

home = os.environ.get('USERPROFILE')
if home == None:
    home = ""
journalfolder = home + f'\\Saved Games\\Frontier Developments\\Elite Dangerous'
harddrive = home + f'\\Downloads\\'


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
    return (datetime.strptime(s[:len(dformat) + 2], dformat))


def whereami():
    try:
        with open(journalfolder+'\\NavRoute.json', 'r') as io:
            return json.load(io)['Route'][-1]['StarSystem']
    except:
        return


def update_progress(progress, status=''):
    # update_progress() : Displays or updates a console progress bar
    # Accepts a float between 0 and 1. Any int will be converted to a float.
    # A value under 0 represents a 'halt'.
    # A value at 1 or bigger represents 100%
    barLength = 30  # Modify this to change the length of the progress bar
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
    text = "\rPercent: [{0}] {1}% {2}".format(
        "#"*block + "-"*(barLength-block), round(progress*100, 1), status.ljust(40))
    sys.stdout.write(text)
    sys.stdout.flush()


class Bubble():
    mainfaction = CSNSettings.myfaction

    def __init__(self):
        # systems with faction presence, full uptodate detail
        self.lastick = api.getlasttick()
        self.localspace = self.refreshcache()

        # self.systems is currently EMPTY !! Can all be trashed or moved to look at Spansh
        # all nearby systems, has only stale or structural data

    def refreshcache(self):
        print(f'Refreshing BGS Data for {self.mainfaction}:', end='')

        myfile = 'data\\LocalSpace.json'
        if not (os.path.isfile(myfile)):
            localSpace = dict()
        else:
            with open(myfile, 'r') as io:
                localSpace = json.load(io)

        # List of all systems the faction has a presence in.
        # This is the master structure that has additional data attached used for processing later
        faction_systems: list = api.getfaction(CSNSettings.myfaction)[
            'faction_presence']

        # Loop through all the systems that the faction is present in
        for counter, sys in enumerate(faction_systems):
            update_progress(counter/len(faction_systems), sys['system_name'])
            # Previous Run
            # NB updated_at do not always match between Faction and System
            if sys['system_name'] in localSpace and localSpace[sys['system_name']] and sys['updated_at'] == localSpace[sys['system_name']]['updated_at']:
                # Same or broken api call
                pass
            else:
                latest = api.getsystem(sys['system_name'], True)
                # Skip if API Fails or no channge in Factions (Tick Lag)
                if (not latest) or (sys['system_name'] in localSpace and latest['factions'] == localSpace[sys['system_name']]['factions']):
                    continue
                localSpace[sys['system_name']] = latest
                localSpace[sys['system_name']]['empire'] = sys['empire']
                localSpace[sys['system_name']]['happytext'] = sys['happytext']
                localSpace[sys['system_name']]['happiness'] = sys['happiness']
                localSpace[sys['system_name']]['stations'] = api.getstations(
                    sys['system_name'])

                localSpace[sys['system_name']]['sellsTritium'] = False
                for station in localSpace[sys['system_name']]['stations']:
                    if station['economy'] == '$economy_refinery' and station['type'] != 'crateroutpost':
                        localSpace[sys['system_name']]['sellsTritium'] = True
                        break

                for f in localSpace[sys['system_name']]['factions']:
                    if f['name'] == sys['empire']:
                        localSpace[sys['system_name']]['empire'] = f
                        break

            localSpace[sys['system_name']]['fresh'] = self.lastick < EliteBGSDateTime(
                localSpace[sys['system_name']]['updated_at'])

        # Remove Retreated Systems
        for s in localSpace.copy():
            if s in list(x['system_name'] for x in faction_systems):
                pass
            else:
                del localSpace[s]

        # Save Faction File
        with open(myfile, 'w') as io:
            json.dump(localSpace, io)

        update_progress(1, 'Base Date Generated')
        return localSpace

    def canonndist(self, sys):
        '''
        Returns the minimum direct distance of a system to ANY local system
        '''
        closest = None
        for n, x in enumerate(self.localspace):
            cs = self.localspace[x]
            d = dist(sys['coords']['x'], cs['x'], sys['coords']
                     ['y'], cs['y'], sys['coords']['z'], cs['z'])
            if closest == None or d < closest:
                closest = d
        return closest

    def canonndistcube(self, sys):
        '''
        Returns the minimum coord delta of a system to ANY local system (expansion rules)
        '''

        closest = None
        for n, x in enumerate(self.localspace):
            cs = self.localspace[x]
            d = max([abs(sys['coords']['x']-cs['x']), abs(sys['coords']
                    ['y']-cs['y']), abs(sys['coords']['z']-cs['z'])])
            if closest == None or d < closest:
                closest = d
        return closest

    def findsystem(self, nameorid):
        try:
            if type(nameorid) is str:
                id = next(i for i, x in enumerate(
                    self.systems) if x['name'] == nameorid)
            else:
                id = next(i for i, x in enumerate(
                    self.systems) if x['id64'] == nameorid)
            if id:
                # TODO should fix source data
                self.systems[id]['system_name'] = self.systems[id]['name']
                self.systems[id]['x'] = self.systems[id]['coords']['x']
                self.systems[id]['y'] = self.systems[id]['coords']['y']
                self.systems[id]['z'] = self.systems[id]['coords']['z']
                self.systems[id]['factions'].sort(
                    key=lambda x: x['influence'], reverse=True)

            return self.systems[id]
        except StopIteration:
            # print(f'!System not found {nameorid}')
            return None

    def findlocalsystem(self, system_name):
        '''
        Return system details from local space or api
        '''
        if system_name in self.localspace:
            return self.localspace[system_name]
        else:
            return api.getsystem(system_name)

    def systemSellsTritium(self, system_name):
        sys = self.localspace(system_name)
        # TODO Stations not tested.
        for station in sys['stations']:
            if station.get('primaryEconomy', '') == 'Refinery' and 'Planetary' not in station['type']:
                return True
        return False

    def currentinf(self, system_name, faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction:
                return f['influence']
        return None

    def dayswon(self, system_name, faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction and len(f['conflicts']) > 0:
                return f['conflicts'][0]['days_won']
        return (0)

    def assetatrisk(self, system_name, faction):
        sys = self.findlocalsystem(system_name)
        for f in sys['factions']:
            if f['name'] == faction and len(f['conflicts']) > 0:
                return f['conflicts'][0]['stake']
        return ('')


if __name__ == '__main__':
    bubble = Bubble()
    print(F'Done in {api.NREQ}')
