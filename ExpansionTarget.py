from ssl import ALERT_DESCRIPTION_BAD_CERTIFICATE_HASH_VALUE
from typing import Iterable
from Bubble import update_progress
import api
from datetime import datetime
from EDDBFramework import EDDBFrame, cubedist, sysdist

eddb = None # Global Variabel to store an instance of the EDDBFramework
rangeSimple = 20
rangeExtended = 30


def EBGS_expansionTargets(faction, knownsys=None):
    '''
    Reports best expansion target for all a factions expandable systems,
    or all expansion targets for a specfic knownsys.
    Standalone version requires no other CSN data, but uses more API calls.
    '''
    mininf = 70
    range = 30  # Should be 30 for normal running, use a lower number during R&D
    candidates = list()
    proposedNL = list()

    print(
        f"*** Expansion Targets for {faction} {' - '+knownsys+' ' if knownsys else ''}***")

    # fetch all faction systems over 70% influence and sort into reverse Inf order
    allSystems = api.getfaction(faction)['faction_presence']
    if not knownsys:
        allSourceSystems = list(
            filter(lambda x: x['influence'] >= (mininf/100), allSystems))
        allSourceSystems.sort(key=lambda x: x['influence'], reverse=True)
    else:
        allSourceSystems = list(
            filter(lambda x: x['system_name'] == knownsys, allSystems))

    for sys in allSourceSystems:
        # Default
        sys['expansionTarget'] = 'No Expansion Available'  
        sys['sys_priority'] = 1000
        sys['anyconflict'] = ''

        sys['allconflicts'] = api.getsystem(sys['system_name'])['conflicts']
        if sys['allconflicts']:
            for c in sys['allconflicts']:
                if c['status'] == 'active' or (c['status'] == 'pending' and not sys['anyconflict']):
                    sys['anyconflict'] = 'but ' + c['status'].capitalize() + ' ' + c['type'].capitalize()

        sys['happytext'] = 'Elated' if sys['happiness'] == '$faction_happinessband1;' else 'Happy' if sys['happiness'] == '$faction_happinessband2;' else 'Pissed Off'
    
    allSourceSystems.sort(key = lambda x: x['happytext'])

    for sys in allSourceSystems:
        sysInRange = api.getnearsystems(sys['system_name'], range)
        # Remove systems where faction is already present
        sysInRange = list(filter(lambda x: faction not in list(
            y['name'] for y in x['factions']), sysInRange))
        sysInRange.sort(key=lambda x:x['cubedist'])

        if len(sysInRange):
            bestpriority = 1000
            for target in sysInRange:
                # Default in case nothing is found
                target['sys_priority'] = 1000
                target['expansionType'] = 'None'
                # System Priorties : 0 < Simple Expansion Dist < 100 < Extended Expansion Dist < 200 < Invasion + Lowest Non Native Ind < 1000 < Nothing Found
                # Simple Expansion
                if target['cubedist'] <= 20 and len(target['factions']) < 7:
                    target['sys_priority'] = target['distanceFromReferenceSystem']
                    target['expansionType'] = f"Simple Expansion to {target['name']}"
                    if knownsys:
                        candidates.append(
                            {'priority': target['sys_priority'], 'target': target['expansionType']})
                    bestpriority = min(bestpriority, target['sys_priority'])
                elif len(target['factions']) < 7:  # Extended Expansion
                    target['sys_priority'] = 100 + \
                        target['distanceFromReferenceSystem']
                    target['expansionType'] = f"Extended Expansion to {target['name']}"
                    if knownsys:
                        candidates.append(
                            {'priority': target['sys_priority'], 'target': target['expansionType']})
                    bestpriority = min(bestpriority, target['sys_priority'])
                elif bestpriority>=200 or knownsys:  # Invasion
                    natives = api.eddbNatives(target['name'])
                    try:
                        target['factions'].sort(
                            key=lambda x: x['faction_details']['faction_presence']['influence'])
                        for targetfaction in target['factions']:
                            # TODO could exclude factions in conflict, but this is transitory and probably needs manual monitoring (GIGO)
                            # TODO include factions inf and conflict status in message
                            if targetfaction['name'] not in natives:
                                target['sys_priority'] = 200 + \
                                    targetfaction['faction_details']['faction_presence']['influence']
                                target['expansionType'] = f"Invasion of {target['name']} ({targetfaction['name']})"
                                if knownsys:
                                    candidates.append(
                                        {'priority': target['sys_priority'], 'target': target['expansionType']})
                                break
                    except:
                        print(f"!! Dodgy Faction in {target['name']} ({sys['system_name']})")


            # Sort all candidate systems in priority order
            sysInRange.sort(key=lambda x: x['sys_priority'])
            sys['expansionTarget'] = sysInRange[0]['expansionType']
            sys['sys_priority'] = sysInRange[0]['sys_priority']

        if sys['sys_priority'] == 1000:
            proposedNL.append(sys)
            #print(f"{sys['system_name']} FAILED")
        else:
            print(
                f"{sys['system_name']} ({int(100*sys['influence'])}%) {sys['happytext']} {sys['anyconflict']}: {sys['expansionTarget']}")

            if candidates:
                candidates.sort(key=lambda x: x['priority'])
                for candidate in candidates:
                    print('...'+candidate['target'])

    if proposedNL:
        print('** No Target : '+ ', '.join(map(lambda x: f"{x['system_name']} ({sys['happytext']})", proposedNL)))
    print(f'*** Complete. Number of API Requests:{api.NREQ} ***')

def ExpansionToSystem(system,show=True,simpleonly = False):
    ''' Returns systems that would expand INTO a given system the soonest '''
    range = rangeSimple if simpleonly else rangeExtended  # Maximum Range for Expansion
    global eddb
    if not eddb:
        eddb = EDDBFrame()
    answers=list()

    # Default
    targetsys = eddb.system(system)
    factionspresent = list(x['name'] for x in targetsys['minor_faction_presences'])

    sysInRange = eddb.cubearea(system, range)
    sysInRange = list(filter(lambda x: x['controlling_minor_faction'] not in factionspresent,sysInRange))
    
    print(f'# Looking for {"Simple " if simpleonly else""}expansions TO {system} in {len(sysInRange)} targets')
    for i,sys in enumerate(sysInRange):
        update_progress(i/len(sysInRange),sys['name'])
        targets = ExpansionFromSystem(sys['name'])
        cycles = 0
        for target in targets:
            cycles += 1 if target['expansionType'][0] == 'S' else 2
            if target['name'] == system:
                #print(f"{sys['name']} [{sys['controlling_minor_faction']}] ({round(sys['influence'],1)}%) in {cycles}")
                eddb.getstations(sys['name'])
                sys['tocycles'] = cycles
                answers.append(sys)
                break
    update_progress(1)
    answers.sort(key=lambda x: x['tocycles'])
    if show:
        print('')
        print(f"# Quickest Expansions to {system} which has {len(targetsys['minor_faction_presences'])} factions")
        for answer in answers[:10]:
            print(f"{answer['name']} ({round(answer['influence'],1)}%) {answer['controlling_minor_faction']}- {answer['beststation']} * {answer['tocycles']}")
    return answers

def ExpansionFromSystem(system_name, show = False, factionpresence = None, prebooked_system_name = None, useretreat = True):
    '''
    Reports best expansion target for a faction from a system
    factionpresence option will ignore who owns the faction, and just ignore systems in the list - for long term planning where ownership may change.
    '''
    rangeExtended  # Maximum Range for Expansion
    global eddb
    if not eddb:
        eddb = EDDBFrame()

    # Default
    sys = eddb.system(system_name)
    eddb.getstations(system_name)
    sys['target'] = 'No Expansion Available'  
    sys['priority'] = 1000
    if not factionpresence:
        factionpresence = eddb.systemspresent(sys['controlling_minor_faction'])
    
    if prebooked_system_name:
        factionpresence.append(eddb.system(prebooked_system_name))

    systoignore = list(x['name'] for x in factionpresence) ## Just using names as system can hold changing values 
    ## TODO Investigate change factionpresence param to be a list of names so I dont have to gather it every cycle

    sys['conflicts'] = eddb.activestates(system_name,True)

    sysInRange = eddb.cubearea(sys['name'], rangeExtended)
    # Remove systems where faction is already present or other reasons
    sysInRange = list(filter(lambda x: x['name'] not in systoignore and x['name'] != sys['name'], sysInRange))
    sysInRange.sort(key=lambda x: cubedist(x,sys))

    if len(sysInRange):
        bestpriority = 1000
        for target in sysInRange:
            if target['name'] == 'DEBUG': ## DEBUG
                print('')
            # Default in case nothing is found
            target['sys_priority'] = 1000
            target['expansionType'] = 'None'
            target['cubedist'] = cubedist(target,sys)
            eddb.getstations(target['name']) # Load Station and Beststation into System

            # System Priorties : 0 < Simple Expansion Dist < 100 < Extended Expansion Dist < 200 < Invasion + Lowest Non Native Ind < 1000 < Nothing Found
            ## ID Confirms priority is based on straight line distance NOT cubedist
            if target['cubedist'] <= rangeSimple and len(target['minor_faction_presences']) < 7: # Simple Expansion
                target['sys_priority'] = sysdist(target,sys) 
                target['expansionType'] = f"Simple Expansion"
                bestpriority = min(bestpriority, target['sys_priority'])
            elif len(target['minor_faction_presences']) < 7:  # Extended Expansion
                target['sys_priority'] = 100 + sysdist(target,sys)
                target['expansionType'] = f"Extended Expansion"
                bestpriority = min(bestpriority, target['sys_priority'])
            elif len(target['minor_faction_presences']) == 7:  # Invasion # TODO Unknown if Invasion is limited to Simple range
                natives = eddb.natives(target['name'])
                try:
                    target['minor_faction_presences'].sort(
                        key=lambda x: x['influence'])
                    for targetfaction in target['minor_faction_presences']:
                        # TODO could exclude factions in conflict, but this is transitory and probably needs manual monitoring (GIGO)
                        if targetfaction['name'] not in natives:
                            target['sys_priority'] = 200 + targetfaction['influence']
                            target['expansionType'] = f"Invasion of {targetfaction['name']}"
                            break
                except:
                    print(f"!! Dodgy Faction {target['name']} in {sys['name']}")
            
            if useretreat and 'historic' in target.keys() and sys['controlling_minor_faction'] in target['historic']: # Has previously retreated
                target['sys_priority'] += 300

        # Sort all candidate systems in priority order
        sysInRange.sort(key=lambda x: x['sys_priority'])
        cycles = 0
        for cyclesys in sysInRange:
            cycles += 1 if cyclesys['expansionType'][0] == 'S' else 2
            cyclesys['cycles'] = cycles

    if show:
        print(f"Expansion from {sys['name']} ({round(sys['influence'],1)}%):")
        if not sysInRange or sysInRange[0]['sys_priority'] == 1000:
            print(f" ! No Candidates ")
        else:
            for cand in sysInRange[:8]:
                if cand['sys_priority'] != 1000:
                    print(f" {cand['name']} : {cand['expansionType']}{' ('+', '.join(cand['pf'])+')' if cand['pf'] else ''} [{cand['beststation']}] in {cand['cycles']} cycles")
    return sysInRange

def ExpansionCandidates(faction, show=False, prebooked=None, inflevel=70):
    global eddb
    print(f"Expansion Candidates for {faction}:")
    if not eddb:
        eddb = EDDBFrame()
    candidates = eddb.systemscontroled(faction)
    candidates = list(filter(lambda x: x['influence'] > inflevel, candidates))
    candidates.sort(key=lambda x: -100*(x['minor_faction_presences'][0]['happiness_id'])+x['influence'], reverse=True)
    for counter, c in enumerate(candidates):
        update_progress(counter/len(candidates),c['name'])
        alltargets = ExpansionFromSystem(c['name'],False,None,prebooked)
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

    return list(filter(lambda x: x['expansion'] , candidates))
        
def InvasionAlert(faction,mininf=70, show=True, lookahead=3):
    '''
    Will report all systems that would expand into a faction system within lookahead cycles
    '''
    global eddb
    if not eddb:
        eddb = EDDBFrame()
    alertsystems = list()

    homesystems = list((x['name'] for x in eddb.systemspresent(faction)))
    donesystems = list()
    print(f'Checking for Future Invasions of {faction} Systems:')
    for counter, home in enumerate(homesystems):
        update_progress(counter/len(homesystems),home)
        invaders = filter(lambda x: x['name'] not in homesystems 
                        and x['name'] not in donesystems 
                        and x['population'] > 0
                        and x['influence'] > mininf
                        , eddb.cubearea(home, rangeExtended))
        for invader in invaders:
            targets = list(filter(lambda x: x['name'] in homesystems,ExpansionFromSystem(invader['name'])[:lookahead])) # Check if next lookahead expansions will target the home faction
            if targets:
                alertsystems.append(invader.copy())
                alertsystems[-1]['invading']=targets[0]['name']
                alertsystems[-1]['cycles'] = targets[0]['cycles']
            donesystems.append(invader['name'])
    update_progress(1)

    if show:
        if alertsystems:
            alertsystems.sort(key=lambda x: x['cycles'])
            print(f"Possible Invasions of {faction} space:")
            alertsystems.sort(key=lambda x: x['influence'], reverse=True)
            for alert in alertsystems:
                print(f" {alert['controlling_minor_faction']} from {alert['name']} targeting {alert['invading']} in {alert['cycles']} cycles (inf {round(alert['influence'],1)}%) ")

    return alertsystems

def InvasionRoute(fromsys,tosys,maxcycles = 5):
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
        currentsys = route[-1]
        currentdist = sysdist(currentsys,destsys)
        routedist = currentsys['routedist'] if 'routedist' in currentsys.keys() else 0
        db = list(x['name'] for x in route)
        if currentsys['name'] == destsys['name']: #reached the end
            print(f'! Route Found : Total Phases {routedist}')
            if (not bestdist) or routedist < bestdist:
                allroutes.append(route.copy())
                bestdist = min(routedist,bestdist) if bestdist else routedist
        else: # take the next set of expansions
            exp = ExpansionFromSystem(currentsys['name'],False,route,None,False)
            for sys in exp[:maxcycles]:
                routedist += 1 if sys['expansionType'][0]=='S' else 2
                sys['routedist'] = routedist

                # prevent backtracking
                if 'best' not in sys.keys():        
                    sys['best'] = sys['routedist']+1
                else:
                    sys['best'] = min(sys['best'],sys['routedist']+1) 
                
                route.append(sys.copy()) # expand
                route[-1]['from'] = currentsys['name']
                xdist = sysdist(sys,destsys)
                if xdist < currentdist and ((not bestdist) or routedist<bestdist) and (sys['best'] > routedist): # follow the expansion if it is usefull
                    tdepth += 1
                    print(' '*tdepth+f"{currentsys['name']} > {sys['name']} ({routedist}) ({round(xdist,1)})")
                    spider()

            # all done, pop the route off
            for sys in exp[:maxcycles]:
                routedist -= 1 if sys['expansionType'][0]=='S' else 2
                route.pop()
        tdepth -= 1
        return

    print(f"Invasion Route from {fromsys} to {tosys}:")
    if not eddb:
        eddb = EDDBFrame()
    
    startsys = eddb.system(fromsys) # for distance calcs     
    destsys = eddb.system(tosys) # for distance calcs
    totaldist = sysdist(startsys,destsys) # for progress bar

    route = [startsys]
    route[0]['from'] = 'Start'
    route[0]['expansionType'] = 'Home'
    route[0]['routedist'] = 0
    allroutes = list()
    bestdist = None
    tdepth = 0
    spider()

    if allroutes:
        allroutes.sort(key=lambda x: x[-1]['routedist'])
        print(f"\n**Route from {fromsys} to {tosys}:")
        for n in allroutes[0]:
            print(f"{n['from']} > {n['name']} ({n['controlling_minor_faction']}): {n['expansionType']} ({n['routedist']})")
    else:
        print('Failed for some unknown reason')
    
    return


if __name__ == '__main__':
    ## These functions use EliteBGS API, so the data is live, but uses a LOT of API Calls and is the slower method
    #EBGS_expansionTargets("Canonn","")
    #EBGS_expansionTargets("Marquis du Ma'a", "Menhitae") ## Give a faction AND System and it will list all Expansion Targets for that system
    
    ## These functions use the daily EDDB data dump, so are upto 24 hours out of date, but no API calls and is significantly faster

    # Currently Raising for Defensive Purposes
    #ExpansionFromSystem("Chelka",True)
    #ExpansionFromSystem("Dvorotri",True)
    #ExpansionFromSystem("HIP 100284",True) 
    #ExpansionFromSystem("Kungati",True) 
     
    ## Canonn Exansion Planning
    #ExpansionCandidates("Canonn",True)
    #ExpansionCandidates("Canonn",True,None,40)

    #ExpansionFromSystem("Kongi",True)
    #ExpansionFromSystem("Rishnum",True)    
    #ExpansionFromSystem("Bactrimpox",True)    
    #ExpansionFromSystem("Chematja",True)    
    #ExpansionFromSystem("Jarildekald",True)    
    #ExpansionFromSystem("Lelalakan",True)    
     

    ## System Under Threat
    #InvasionAlert("Canonn",mininf = 50,lookahead = 4)
    #InvasionAlert("Canonn")
    #ExpansionToSystem("Cnephtha",True,True)                ## 5
    #ExpansionToSystem("Pipedu",True,True)                  ## 6
    #ExpansionToSystem("Meinjhalie",True,True)              ## 5
    #ExpansionToSystem("Njoere",True,True)                  ## 7 PROTECTED
    #ExpansionToSystem("Rishnum",True,True)                 ## 6
    #ExpansionToSystem("Cephei Sector BA-A d107",True,True) ## 3 Not enough available factions to try and fill
    #ExpansionToSystem("HIP 54529")                         ## 5 Factions - Run EXTENTED, 5 Cycles is best for SIMPLE
    
    
   

    ## Marquis du Ma'a
    #ExpansionCandidates("Marquis du Ma'a",True,None)
    #ExpansionFromSystem("Luvalla",True)


    ## Stellanebula Project
    #ExpansionCandidates("Stellanebula Project",True,None)
    #ExpansionFromSystem("HIP 117029",True)
    #ExpansionFromSystem("Dakinn",True)
    #ExpansionFromSystem("Kaititja",True)
    #ExpansionFromSystem("Heheng De",True)



    ## IPX
    #ExpansionCandidates("Interplanetary Explorations",True,None)
    #ExpansionFromSystem("Cephei Sector BA-A d85",True)
    #ExpansionFromSystem("Keiadjara",True)



    #InvasionRoute('Varati','Sol')
    #InvasionRoute('Varati','Bactrimpox')
    #InvasionRoute('Bactrimpox','Manktas',99)

    ## All Expansions from Orbital Systems with Simple Expansions still available
    #allexp = ExpansionCandidates("Canonn",True,None,40)
    #for exp in allexp:
        #if exp['beststation'] == 'Orbital':
            #if exp['expansion']['expansionType'][0] == 'S':
                #ExpansionFromSystem(exp['name'],True)
    print(f"Done : API {api.NREQ}")
    
    