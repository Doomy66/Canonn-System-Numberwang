import api
from EDDBFramework import EDDBFrame, cubedist, sysdist

eddb = list()

def expansionTargets(faction, knownsys=None):
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

def EDDBExpansionFromSystem(faction, system, excluded = None,show = False):
    '''
    Reports best expansion target for a faction from a system
    excluded can be the precalculated faction presence - If None it will be loaded (Time saver)
    '''
    print(f".Expansion Targets for {faction} - {system}")
    range = 30  # Should be 30 for normal running, use a lower number during R&D
    global eddb
    if not eddb:
        eddb = EDDBFrame()

    # Default
    if excluded:
        factionpresence = excluded
    else:
        factionpresence = eddb.systemspresent(faction)
    sys = eddb.system(system)
    sys['target'] = 'No Expansion Available'  
    sys['priority'] = 1000

    sys['conflicts'] = eddb.activestates(system,True)

    sysInRange = eddb.cubearea(sys['name'], range)
    # Remove systems where faction is already present
    sysInRange = list(filter(lambda x: x not in factionpresence and x['name'] != sys['name'], sysInRange))
    sysInRange.sort(key=lambda x: cubedist(x,sys))

    if len(sysInRange):
        bestpriority = 1000
        for target in sysInRange:
            # Default in case nothing is found
            target['sys_priority'] = 1000
            target['expansionType'] = 'None'
            target['cubedist'] = cubedist(target,sys)
            # System Priorties : 0 < Simple Expansion Dist < 100 < Extended Expansion Dist < 200 < Invasion + Lowest Non Native Ind < 1000 < Nothing Found
            # Simple Expansion
            if cubedist(target,sys) <= 20 and len(target['minor_faction_presences']) < 7:
                target['sys_priority'] = sysdist(target,sys)
                target['expansionType'] = f"Simple Expansion"
                bestpriority = min(bestpriority, target['sys_priority'])
            elif len(target['minor_faction_presences']) < 7:  # Extended Expansion
                target['sys_priority'] = 100 + sysdist(target,sys)
                target['expansionType'] = f"Extended Expansion"
                bestpriority = min(bestpriority, target['sys_priority'])
            elif len(target['minor_faction_presences']) == 7:  # Invasion
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


        # Sort all candidate systems in priority order
        sysInRange.sort(key=lambda x: x['sys_priority'])

    if show:
        print(f"Expansion from {sys['name']}:")
        if not sysInRange or sysInRange[0]['sys_priority'] == 1000:
            print(f" ! No Candidates ")
        else:
            for cand in sysInRange[:4]:
                if cand['sys_priority'] != 1000:
                    print(f" {cand['name']} : {cand['expansionType']}")
    return sysInRange

def EDDBExpansionCandidates(faction, show=False):
    global eddb
    print(f".Expansion Candidates for {faction}")
    if not eddb:
        eddb = EDDBFrame()
    excludedtargets = eddb.systemspresent(faction)
    candidates = eddb.systemscontroled(faction)
    candidates = list(filter(lambda x: x['minor_faction_presences'][0]['influence'] > 70, candidates))
    candidates.sort(key=lambda x: -100*(x['minor_faction_presences'][0]['happiness_id'])+x['minor_faction_presences'][0]['influence'], reverse=True)
    for c in candidates:
        alltargets = EDDBExpansionFromSystem(faction,c['name'],excludedtargets)
        if alltargets:
            c['expansion'] = alltargets[0].copy()
            print(f"  {c['expansion']['name']} ({c['expansion']['expansionType']})")
            ## TODO ## Conflict check for source system
        else:
            c['expansion'] = list()

    if show:
        print(f"Expansion Candidates for {faction}:")
        for c in candidates:
            if c['expansion']:
                print(f" {'+' if c['minor_faction_presences'][0]['influence']<75 else '^' if c['minor_faction_presences'][0]['happiness_id'] == 1  else ' '} {c['name'].ljust(26)} > {c['expansion']['name']} ({c['expansion']['expansionType']})")

    return list(filter(lambda x: x['expansion'] , candidates))
        
def EDDBInvasionAlert(faction,show=False):
    global eddb
    if not eddb:
        eddb = EDDBFrame()
    alertsystems = list()

    homesystems = list((x['name'] for x in eddb.systemspresent(faction)))
    donesystems = list()
    for home in homesystems:
        print(f".Checking all populated systems near {home}")
        invaders = filter(lambda x: x['name'] not in homesystems 
                        and x['name'] not in donesystems 
                        and x['population'] > 0
                        and x['minor_faction_presences'][0]['influence'] > 70
                        , eddb.cubearea(home, 30))
        for invader in invaders:
            targets = EDDBExpansionFromSystem(invader['minor_faction_presences'][0]['name'],invader['name'])
            if targets and targets[0]['name'] in homesystems:
                alertsystems.append(invader.copy())
                alertsystems[-1]['invading']=targets[0]['name']
            donesystems.append(invader['name'])

    if show:
        if alertsystems:
            print(f"Possible Invasions of {faction} space:")
            alertsystems.sort(key=lambda x: x['minor_faction_presences'][0]['influence'], reverse=True)
            for alert in alertsystems:
                print(f" {alert['controlling_minor_faction']} from {alert['name']} targeting {alert['invading']} (inf {alert['minor_faction_presences'][0]['influence']}%)")

    return alertsystems


if __name__ == '__main__':
    #expansionTargets("Canonn","")
    #expansionTargets("Marquis du Ma'a", "Menhitae") ## Give a faction AND System and it will list all Expansion Targets for that system
    #EDDBExpansionFromSystem("Canonn","Aknango",None,True)
    EDDBExpansionCandidates("Canonn",True)
    print('')
    EDDBInvasionAlert("Canonn",True)
    
