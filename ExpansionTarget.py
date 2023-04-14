from ssl import ALERT_DESCRIPTION_BAD_CERTIFICATE_HASH_VALUE
from typing import Iterable
from Bubble import update_progress
import api
from datetime import datetime
from SpanshBGS import SpanshBGS, cubedist, sysdist
import simplejson as json

spansh = None # Global Variabel to store an instance of the Framework
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
    global spansh
    if not spansh:
        spansh = SpanshBGS()
    answers=list()

    # Default
    targetsys = spansh.system(system,live=live)
    factionspresent = list(x['name'] for x in targetsys['factions'])
    if assumeretreat:
        targetsys['numberoffactions'] = min(6,targetsys['numberoffactions'])
    if easyinvade:
        natives = spansh.natives(targetsys['name'])
        for f in targetsys['factions']:
            if f['name'] not in natives:
                f['influence'] = 0.01

    sysInRange = spansh.cubearea(system, range, live=live)
    sysInRange = list(filter(lambda x: x['controllingFaction']['name'] not in factionspresent,sysInRange))
    
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
                spansh.getstations(sys['name'])
                sys['tocycles'] = cycles
                sys['toexpansionType'] = target['expansionType']
                answers.append(sys)
                break
    update_progress(1)
    answers.sort(key=lambda x: x['tocycles'])
    if show:
        print('')
        print(f"# Quickest Expansions to {system} which has {len(targetsys['factions'])} factions")
        for answer in answers[:20]:
            print(f"{answer['name']} ({100*round(answer['influence'],1)}%) {answer['controllingFaction']['name']}- {answer['beststation']} * {answer['tocycles']} {answer['toexpansionType']}")
    return answers

def ExpansionFromSystem(system_name, show = False, avoided_systems = None, avoid_additional = None, useretreat = True, asfaction = None, organisedinvasions = False, live=False, reportsize = 8, extendedphase = False, simpleonly=False):
    '''
    Reports best expansion target for a faction from a system
    factionpresence option will ignore who owns the faction, and just ignore systems in the list - for long term planning where ownership may change.
    useretreat = consider if a faction has previously retreated
    '''
    rangeExtended  # Maximum Range for Expansion
    global spansh
    if not spansh:
        spansh = SpanshBGS()

    # Default
    sys = spansh.system(system_name,live=live)
    spansh.getstations(system_name)
    sys['target'] = 'No Expansion Available'  
    sys['priority'] = 1000
    if not avoided_systems:
        avoided_systems = list(x['name'] for x in spansh.systemspresent(asfaction if asfaction else sys['controllingFaction']['name']))
    
    if avoid_additional:
        avoided_systems.append(avoid_additional)

    sys['conflicts'] = spansh.activestates(system_name,True)

    sysInRange = spansh.cubearea(sys['name'], rangeSimple if simpleonly else rangeExtended,live=live)
    # Remove systems where faction is already present or other reasons
    sysInRange = list(filter(lambda x: x['name'] not in avoided_systems and x['name'] != sys['name'] and x['factions'], sysInRange))
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
            spansh.getstations(target['name']) # Load Station and Beststation into System

            # System Priorties : 0 < Simple Expansion Dist < 200 < Invasion + Lowest Non Native Ind < 300 < Extended Expansion Dist < 1000 < Nothing Found
            ## IanD Confirms priority is based on straight line distance NOT cubedist
            ## Jane Confirms Invasion happens before Extended (as we saw Aymarahuara > Tarasa)
            ## Cannot Invade Controlling Faction
            if (target['cubedist'] <= rangeSimple or extendedphase) and numberoffactions < 7: # Simple Expansion
                target['sys_priority'] = sysdist(target,sys) 
                target['expansionType'] = f"Expansion"
                target['expansionDetail'] = f"Simple"


                if useretreat and 'historic' in target.keys() and (asfaction if asfaction else sys['controllingFaction']['name']) in target['historic']: # Has previously retreated
                    target['sys_priority'] += 100
                    target['expansionType'] += f" (Retreated)"
                    target['expansionDetail'] = f"Retreated"

                bestpriority = min(bestpriority, target['sys_priority'])
            elif target['cubedist'] <= rangeSimple and numberoffactions == 7:  # Invasion
                natives = spansh.natives(target['name'])
                try:
                    target['factions'].sort(
                        key=lambda x: 100*x['influence'])
                    for targetfaction in target['factions'][:-1]: # Cannot Invade Controlling Faction
                        # TODO could exclude factions in conflict, but this is transitory and probably needs manual monitoring (GIGO)
                        if targetfaction['name'] not in natives:
                            target['sys_priority'] = 200 + 100*targetfaction['influence']
                            if organisedinvasions:
                                target['expansionType'] = f"Invasion of {targetfaction['name']} (Organised)"
                                target['expansionDetail'] = f"{targetfaction['name']}"
                            else:
                                target['expansionType'] = f"Invasion of {targetfaction['name']} ({round(100*targetfaction['influence'],1)}%)"
                                target['expansionDetail'] = f"{targetfaction['name']} ({round(100*targetfaction['influence'],1)}%)"
                            break
                except:
                    print(f"!! Dodgy Faction {target['name']=} in {sys['name']=}")
            elif numberoffactions < 7:  # Extended Expansion
                target['sys_priority'] = sysdist(target,sys) + 300
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
        print(f"Expansion from {sys['name']} ({100*round(sys['influence'],1)}%):")
        if not sysInRange or sysInRange[0]['sys_priority'] == 1000:
            print(f" ! No Candidates ")
        else:
            for cand in sysInRange[:reportsize]:
                if cand['sys_priority'] != 1000:
                    any_retreating = False
                    for f in cand['factions']:
                        if f['state'] == 'Retreat': ## Now Single State and no Pending
                            any_retreating = True

                    print(f" {cand['name']} : {cand['expansionType']}{' ('+', '.join(cand['pf'])+')' if cand['pf'] else ''} [{cand['beststation']}] in {cand['cycles']} cycles {'[Retreat Detected !!!]' if any_retreating else ''}")

    return sysInRange

def ExpansionCandidates(faction, show=False, prebooked=None, inflevel=70,live=False,extenedphase=False):
    global spansh
    print(f"Expansion Candidates for {faction}:")
    if not spansh:
        spansh = SpanshBGS()
    candidates = spansh.systemscontroled(faction)
    candidates = list(filter(lambda x: x['influence'] > inflevel/100 and x['factions'], candidates))
    # candidates.sort(key=lambda x: -100*(x['factions'][0]['happiness_id'])+100*x['influence'], reverse=True) ## Happiness GONE
    candidates.sort(key=lambda x: 100*x['influence'], reverse=True)
    for counter, c in enumerate(candidates):
        if c['name'] == 'DEBUG':
            print('debug')
        update_progress(counter/len(candidates),c['name'])
        alltargets = ExpansionFromSystem(c['name'],avoid_additional=prebooked,live=live,extendedphase=extenedphase)
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
                print(f" {'+' if 100*c['influence']<75 else ' '} {c['name'].ljust(26)} {c['beststation'].ljust(15)}> {c['expansion']['name']} ({c['expansion']['expansionType']}){' ('+', '.join(c['expansion']['pf'])+')' if c['expansion']['pf'] else ''} [{c['expansion']['beststation']}]")

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
    global spansh
    if not spansh:
        spansh = SpanshBGS()
    alertsystems = list()

    homesystems = list((x['name'] for x in spansh.systemspresent(faction,live=live)))
    donesystems = list()
    print(f'Checking for Future Invasions of {faction} Systems:')
    for counter, home in enumerate(homesystems):
        update_progress(counter/len(homesystems),home)
        invaders = filter(lambda x: x['name'] not in homesystems 
                        and x['name'] not in donesystems 
                        and x['population'] > 0
                        and x['influence'] > mininf/100
                        , spansh.cubearea(home, rangeSimple,live=live)) # 03/12/22 Only bother with Simple Range
        for invader in invaders:
            targets = list(filter(lambda x: x['name'] in homesystems,ExpansionFromSystem(invader['name'],live=live,simpleonly=True)[:lookahead])) # Check if next lookahead expansions will target the home faction
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
                print(f" {alert['controllingFaction']['name']} ({round(100*alert['influence'],1)}%) from {alert['name']} will {alert['invademessage']} to {alert['invading']} in {alert['cycles']} cycles  ")

    return alertsystems

def InvasionRoute(start_system_name,destination_system_name,maxcycles = 100,faction=None):
    '''
    Will calculate the quickest controlled expansion route between 2 systems.
    maxcycles is the number of additional cycles you are prepared to wait at each system
    '''
    global spansh
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
            controlled = list(x['name'] for x in spansh.systemspresent(faction))


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
                thisstep['owner']=sys['controllingFaction']['name']
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
    if not spansh:
        spansh = SpanshBGS()
    
    sys_start = spansh.system(start_system_name) # for distance calcs     
    sys_destination = spansh.system(destination_system_name) 
    
    ## Set target system for Easy Invasion
    natives = spansh.natives(destination_system_name)
    for f in sys_destination['factions']:
        if f['name'] not in natives:
            f['influence'] = 0.01

    route = [{'from':start_system_name,'expansionType':'Start','to':start_system_name,'routedist':0,'owener':sys_start['controllingFaction']['name'],'sys':sys_start}]
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

def FrameReset():
    global spansh
    spansh = None

if __name__ == '__main__':
    ## These functions use the daily EDDB data dump, so are upto 24 hours out of date, but no API calls and is significantly faster
    #ExpansionCandidates("Canonn",show=True)
    #ExpansionFromSystem("Pachanu",True)   
    #ExpansionFromSystem("Yi Trica",True)  
    #ExpansionToSystem("11 Cephei",easyinvade=True)            
    #ExpansionToSystem("Col 285 Sector KZ-C b14-1",simpleonly=True)      
    #InvasionRoute('Kongi','HR 8133',faction='Canonn')
    #InvasionAlert("Canonn",mininf = 60,lookahead = 4)

    #ExpansionFromSystem("Col 285 Sector XF-N c7-20",True)
    #ExpansionToSystem("Wanggu",show=True,simpleonly=True)            
    
 

    print(f"Done : API {api.NREQ}")
    
    