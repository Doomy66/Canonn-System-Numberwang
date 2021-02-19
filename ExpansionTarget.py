import api

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

if __name__ == '__main__':
    expansionTargets("Canonn","")
    #expansionTargets("Marquis du Ma'a", "Menhitae") ## Give a faction AND System and it will list all Expansion Targets for that system
    
