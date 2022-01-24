from ssl import ALERT_DESCRIPTION_BAD_CERTIFICATE_HASH_VALUE
from typing import Iterable
from Bubble import update_progress
import api
from datetime import datetime
from EDDBFramework import EDDBFrame, cubedist, sysdist
import simplejson as json

eddb = None # Global Variabel to store an instance of the EDDBFramework
rangeSimple = 20
rangeExtended = 30

def ExpansionToSystem(system,show=True,simpleonly = False,assumeretreat=False,easyinvade=False,live=False,avoidsystem=''):
    ''' 
    Returns systems that would expand INTO a given system the soonest 
    simplyonly = restricts range
    assumeretreat = assumes the number of factions is 6 or lower
    easyinvade = assumes NonNatives have a tiny Inf
    '''
    range = rangeSimple if simpleonly else rangeExtended  # Maximum Range for Expansion
    global eddb
    if not eddb:
        eddb = EDDBFrame()
    answers=list()

    # Default
    targetsys = eddb.system(system,live=live)
    factionspresent = list(x['name'] for x in targetsys['minor_faction_presences'])
    if assumeretreat:
        targetsys['numberoffactions'] = min(6,targetsys['numberoffactions'])
    if easyinvade:
        natives = eddb.natives(targetsys['name'])
        for f in targetsys['minor_faction_presences']:
            if f['name'] not in natives:
                f['influence'] = 0.01

    sysInRange = eddb.cubearea(system, range, live=live)
    sysInRange = list(filter(lambda x: x['controlling_minor_faction'] not in factionspresent,sysInRange))
    
    print(f'# Looking for {"Simple " if simpleonly else""}expansions TO {system} in {len(sysInRange)} targets' + (", assuming a Retreat happens" if assumeretreat else "") + (", avoiding "+avoidsystem if avoidsystem else ""))
    for i,sys in enumerate(sysInRange):
        update_progress(i/len(sysInRange),sys['name'])
        if sys['name'] == 'DEBUG':
            print('Debug')
        targets = ExpansionFromSystem(sys['name'],avoid_additional=avoidsystem)
        cycles = 0
        for target in targets:
            cycles += 1 if target['sys_priority'] < 300 else 2
            if target['name'] == system:
                #print(f"{sys['name']} [{sys['controlling_minor_faction']}] ({round(sys['influence'],1)}%) in {cycles}")
                eddb.getstations(sys['name'])
                sys['tocycles'] = cycles
                sys['toexpansionType'] = target['expansionType']
                answers.append(sys)
                break
    update_progress(1)
    answers.sort(key=lambda x: x['tocycles'])
    if show:
        print('')
        print(f"# Quickest Expansions to {system} which has {len(targetsys['minor_faction_presences'])} factions")
        for answer in answers[:20]:
            print(f"{answer['name']} ({round(answer['influence'],1)}%) {answer['controlling_minor_faction']}- {answer['beststation']} * {answer['tocycles']} {answer['toexpansionType']}")
    return answers

def ExpansionFromSystem(system_name, show = False, avoided_systems = None, avoid_additional = None, useretreat = True, asfaction = None, organisedinvasions = False, live=False, reportsize = 8):
    '''
    Reports best expansion target for a faction from a system
    factionpresence option will ignore who owns the faction, and just ignore systems in the list - for long term planning where ownership may change.
    useretreat = consider if a faction has previously retreated
    '''
    rangeExtended  # Maximum Range for Expansion
    global eddb
    if not eddb:
        eddb = EDDBFrame()

    # Default
    sys = eddb.system(system_name,live=live)
    eddb.getstations(system_name)
    sys['target'] = 'No Expansion Available'  
    sys['priority'] = 1000
    if not avoided_systems:
        avoided_systems = list(x['name'] for x in eddb.systemspresent(asfaction if asfaction else sys['controlling_minor_faction']))
    
    if avoid_additional:
        avoided_systems.append(avoid_additional)

    sys['conflicts'] = eddb.activestates(system_name,True)

    sysInRange = eddb.cubearea(sys['name'], rangeExtended,live=live)
    # Remove systems where faction is already present or other reasons
    sysInRange = list(filter(lambda x: x['name'] not in avoided_systems and x['name'] != sys['name'], sysInRange))
    sysInRange.sort(key=lambda x: cubedist(x,sys))

    if len(sysInRange):
        bestpriority = 1000
        for target in sysInRange:
            if target['name'] == 'DEBUG': ## DEBUG
                print(f"{target['name']=}")
            # Default in case nothing is found
            target['sys_priority'] = 1000
            target['expansionType'] = 'None'
            target['cubedist'] = cubedist(target,sys)
            numberoffactions = target['numberoffactions']
            eddb.getstations(target['name']) # Load Station and Beststation into System

            # System Priorties : 0 < Simple Expansion Dist < 200 < Invasion + Lowest Non Native Ind < 300 < Extended Expansion Dist < 1000 < Nothing Found
            ## IanD Confirms priority is based on straight line distance NOT cubedist
            ## Jane Confirms Invasion happens before Extended (as we saw Aymarahuara > Tarasa)
            ## Cannot Invade Controlling Faction
            if target['cubedist'] <= rangeSimple and numberoffactions < 7: # Simple Expansion
                target['sys_priority'] = sysdist(target,sys) 
                target['expansionType'] = f"Expansion"
                target['expansionDetail'] = f"Simple"


                if useretreat and 'historic' in target.keys() and (asfaction if asfaction else sys['controlling_minor_faction']) in target['historic']: # Has previously retreated
                    target['sys_priority'] += 100
                    target['expansionType'] += f" (Retreated)"
                    target['expansionDetail'] = f"Retreated"

                bestpriority = min(bestpriority, target['sys_priority'])
            elif target['cubedist'] <= rangeSimple and numberoffactions == 7:  # Invasion
                natives = eddb.natives(target['name'])
                try:
                    target['minor_faction_presences'].sort(
                        key=lambda x: x['influence'])
                    for targetfaction in target['minor_faction_presences'][:-1]: # Cannot Invade Controlling Faction
                        # TODO could exclude factions in conflict, but this is transitory and probably needs manual monitoring (GIGO)
                        if targetfaction['name'] not in natives:
                            target['sys_priority'] = 200 + targetfaction['influence']
                            if organisedinvasions:
                                target['expansionType'] = f"Invasion of {targetfaction['name']} (Organised)"
                                target['expansionDetail'] = f"{targetfaction['name']}"
                            else:
                                target['expansionType'] = f"Invasion of {targetfaction['name']} ({round(targetfaction['influence'],1)}%)"
                                target['expansionDetail'] = f"{targetfaction['name']} ({round(targetfaction['influence'],1)}%)"
                            break
                except:
                    print(f"!! Dodgy Faction {target['name']=} in {sys['name']=}")
            elif numberoffactions < 7:  # Extended Expansion
                target['sys_priority'] = 300 + sysdist(target,sys)
                target['expansionType'] = f"Expansion (Extended)"
                target['expansionDetail'] = f"Extended"
                bestpriority = min(bestpriority, target['sys_priority'])

        # Sort all candidate systems in priority order
        sysInRange.sort(key=lambda x: x['sys_priority'])
        cycles = 0
        for cyclesys in sysInRange:
            cycles += 1 if cyclesys['sys_priority'] < 300 else 2 # Simple (0+) Retreated (100+) and Invasion (200+) are 1 cycle
            cyclesys['cycles'] = cycles
        sysInRange = list(filter(lambda x: x['sys_priority'] != 1000,sysInRange))

    if show:
        print(f"Expansion from {sys['name']} ({round(sys['influence'],1)}%):")
        if not sysInRange or sysInRange[0]['sys_priority'] == 1000:
            print(f" ! No Candidates ")
        else:
            for cand in sysInRange[:reportsize]:
                if cand['sys_priority'] != 1000:
                    any_retreating = False
                    for f in cand['minor_faction_presences']:
                        if 'Retreat' in list(x['name'] for x in f['active_states']) + list(x['name'] for x in f['pending_states']):
                            any_retreating = True

                    print(f" {cand['name']} : {cand['expansionType']}{' ('+', '.join(cand['pf'])+')' if cand['pf'] else ''} [{cand['beststation']}] in {cand['cycles']} cycles {'[Retreat Detected !!!]' if any_retreating else ''}")

    return sysInRange

def ExpansionCandidates(faction, show=False, prebooked=None, inflevel=70,live=False):
    global eddb
    print(f"Expansion Candidates for {faction}:")
    if not eddb:
        eddb = EDDBFrame()
    candidates = eddb.systemscontroled(faction)
    candidates = list(filter(lambda x: x['influence'] > inflevel, candidates))
    candidates.sort(key=lambda x: -100*(x['minor_faction_presences'][0]['happiness_id'])+x['influence'], reverse=True)
    for counter, c in enumerate(candidates):
        if c['name'] == 'DEBUG':
            print('debug')
        update_progress(counter/len(candidates),c['name'])
        alltargets = ExpansionFromSystem(c['name'],avoid_additional=prebooked,live=live)
        if alltargets:
            c['expansion'] = alltargets[0].copy()
            ## TODO ## Conflict check for source system - Not really worth it while Happiness is so broken
        else:
            c['expansion'] = list()
    update_progress(1)

    if show:
        print(f"Expansion Candidates for {faction}:")
        for c in candidates:
            if c['expansion']:
                print(f" {'+' if c['influence']<75 else '^' if c['minor_faction_presences'][0]['happiness_id'] == 1  else ' '} {c['name'].ljust(26)} {c['beststation'].ljust(15)}> {c['expansion']['name']} ({c['expansion']['expansionType']}){' ('+', '.join(c['expansion']['pf'])+')' if c['expansion']['pf'] else ''} [{c['expansion']['beststation']}]")

    # Save simple next expansion results as json for CSN and others 
    savelist = []
    for e in list(filter(lambda x: x['expansion'] , candidates)): ## Strip down data to stop Circular Ref during dump
        savelist.append({'name':e['name'], 'target':e['expansion']['name'], 'expansionType':e['expansion']['expansionType']})
    with open(f'data\\{faction}ExpansionTargets.json', 'w') as io:  # Dump to file 
        json.dump(savelist, io, indent=4)


    return list(filter(lambda x: x['expansion'] , candidates))
        
def InvasionAlert(faction,mininf=70, show=True, lookahead=3, live=False):
    '''
    Will report all systems that would expand into a faction system within lookahead cycles
    '''
    global eddb
    if not eddb:
        eddb = EDDBFrame()
    alertsystems = list()

    homesystems = list((x['name'] for x in eddb.systemspresent(faction,live=live)))
    donesystems = list()
    print(f'Checking for Future Invasions of {faction} Systems:')
    for counter, home in enumerate(homesystems):
        update_progress(counter/len(homesystems),home)
        invaders = filter(lambda x: x['name'] not in homesystems 
                        and x['name'] not in donesystems 
                        and x['population'] > 0
                        and x['influence'] > mininf
                        , eddb.cubearea(home, rangeExtended,live=live))
        for invader in invaders:
            targets = list(filter(lambda x: x['name'] in homesystems,ExpansionFromSystem(invader['name'],live=live)[:lookahead])) # Check if next lookahead expansions will target the home faction
            if targets:
                alertsystems.append(invader.copy())
                alertsystems[-1]['invading']=targets[0]['name']
                alertsystems[-1]['cycles'] = targets[0]['cycles']
                alertsystems[-1]['invadetype'] = targets[0]['expansionType']
                alertsystems[-1]['invademessage'] = 'Expand'  if targets[0]['expansionType'][0] == 'E' else 'Invade '+targets[0]['expansionDetail']
            donesystems.append(invader['name'])
    update_progress(1)

    if show:
        if alertsystems:
            alertsystems.sort(key=lambda x: x['cycles'])
            print(f"Possible Invasions of {faction} space:")
            alertsystems.sort(key=lambda x: x['influence'], reverse=True)
            for alert in alertsystems:
                print(f" {alert['controlling_minor_faction']} ({round(alert['influence'],1)}%) from {alert['name']} will {alert['invademessage']} to {alert['invading']} in {alert['cycles']} cycles  ")

    return alertsystems

def InvasionRoute(start_system_name,destination_system_name,maxcycles = 100,faction=None):
    '''
    Will calculate the quickest controlled expansion route between 2 systems.
    maxcycles is the number of additional cycles you are prepared to wait at each system
    '''
    global eddb
    def spider():
        '''
        recursive depth first
        '''
        nonlocal route, allroutes, bestdist, tdepth
        currentsys = route[-1]['sys']
        currentdist = sysdist(currentsys,sys_destination)
        thisstep = {'from':currentsys['name'],'expansionType':None,'to':None ,'routedist':route[-1]['routedist'],'owner':None,'sys':None}
        controlled = list()
        if faction:
            controlled = list(x['name'] for x in eddb.systemspresent(faction))


        if currentsys['name'] == sys_destination['name']: #reached the end
            print(f"! Route Found : Total Phases {route[-1]['routedist']}")
            if (not bestdist) or route[-1]['routedist'] < bestdist:
                allroutes.append(route.copy())
                bestdist = min(route[-1]['routedist'],bestdist) if bestdist else route[-1]['routedist']
        else: # take the next set of expansions
            exp = ExpansionFromSystem(currentsys['name'],avoided_systems = controlled + list(x['to'] for x in route),useretreat = False,organisedinvasions=True)
            for sys in exp[:maxcycles]:
                thisstep['expansionType']=sys['expansionType']
                thisstep['to']=sys['name']
                thisstep['owner']=sys['controlling_minor_faction']
                thisstep['sys']=sys
                thisstep['routedist'] += 1 ## To Extended takes 2

                # TODO prevent backtracking
                if 'best' not in sys.keys():        
                    sys['best'] = thisstep['routedist']+1
                else:
                    sys['best'] = min(sys['best'],thisstep['routedist']+1) 
                
                route.append(thisstep.copy()) # expand
                xdist = sysdist(sys,sys_destination)
                if xdist < currentdist and ((not bestdist) or thisstep['routedist']<bestdist) and (sys['best'] > thisstep['routedist']): # follow the expansion if it is usefull
                    print(' '*tdepth+f"{currentsys['name']} > {sys['name']} ({thisstep['expansionType']}) ({thisstep['routedist']}) ({round(xdist,1)})")
                    tdepth += 1
                    spider()

            # all done, pop the route off
            for sys in exp[:maxcycles]:
                route.pop()
        tdepth -= 1
        return

    print(f"Invasion Route from {start_system_name} to {destination_system_name}:")
    if not eddb:
        eddb = EDDBFrame()
    
    sys_start = eddb.system(start_system_name) # for distance calcs     
    sys_destination = eddb.system(destination_system_name) 
    
    ## Set target system for Easy Invasion
    natives = eddb.natives(destination_system_name)
    for f in sys_destination['minor_faction_presences']:
        if f['name'] not in natives:
            f['influence'] = 0.01

    route = [{'from':start_system_name,'expansionType':'Start','to':start_system_name,'routedist':0,'owener':sys_start['controlling_minor_faction'],'sys':sys_start}]
    allroutes = list()
    bestdist = None
    tdepth = 0
    spider()

    if allroutes:
        allroutes.sort(key=lambda x: x[-1]['routedist'])
        print(f"\n**Route from {start_system_name} to {destination_system_name}:")
        for n in allroutes[0][1:]:
            print(f"{n['from']} > {n['to']} ({n['owner']}): {n['expansionType']} ({n['routedist']})")
    else:
        print('Failed for some unknown reason')
    
    return

def EDDBReset():
    global eddb
    eddb = None

if __name__ == '__main__':
    ## These functions use the daily EDDB data dump, so are upto 24 hours out of date, but no API calls and is significantly faster
    #ExpansionCandidates("Canonn",show=True)
    #ExpansionFromSystem("Pachanu",True)   
    #ExpansionToSystem("11 Cephei",easyinvade=True)            
    #ExpansionToSystem("Col 285 Sector KZ-C b14-1",simpleonly=True)      
    #InvasionRoute('Kongi','HR 8133',faction='Canonn')
    #InvasionAlert("Canonn",mininf = 60,lookahead = 4)
    #ExpansionFromSystem("Col 285 Sector XF-N c7-20",True)
    #ExpansionToSystem("Wanggu",show=True,simpleonly=True)            
    
 

    print(f"Done : API {api.NREQ}")
    
    