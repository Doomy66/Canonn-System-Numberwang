import json
from Bubble import whereami
import api


def sysdist(s1, s2):
    return((s1['x']-s2['x'])**2 + (s1['y']-s2['y'])**2 + (s1['z']-s2['z'])**2) ** 0.5


def simple(startsystem, thislist, bestans):
    '''
    Calulates an efficent route, from startsystem going to closest unvisited system each time.
    '''

    alist = list()
    alist.append(startsystem)
    bestans = 0
    while len(thislist) > 0:
        ## TODO turn this into a map
        for s in thislist:
            s['dist'] = sysdist(startsystem, s)
        thislist.sort(key=lambda x: x['dist'])
        bestans += thislist[0]['dist']
        startsystem = thislist.pop(0)
        alist.append(startsystem)

    return({'route': alist, 'dist': bestans})


def tsales(croute, cdist, rroute, best):
    '''
    Should be Travelling Salesman route, but not tried it in ages. Took far too long with any reasonable number of systems (as it should)
    '''
    if len(rroute) == 0:  # Route Complete
        if best == None or best['dist'] > cdist:
            best = {'route': croute, 'dist': cdist}
            print('')
            for p in best['route']:
                print(f"{p['system_name']} ({int(p['dist'])})", end=" ")
            print(int(cdist), 'ly')
        return(best)

    startsys = croute[-1] if len(croute) > 0 else None
    for s in rroute:
        thisdist = sysdist(startsys, s) if startsys != None else 0
        if best == None or thisdist+cdist < best['dist']:
            trroute = rroute[:]
            trroute.remove(s)
            tcroute = croute[:]
            tcroute.append(s)
            tcroute[-1]['dist'] = thisdist
            best = tsales(tcroute, cdist+thisdist, trroute, best)

    ##print('.', end='')
    return(best)


def HeatDeath():
    '''
    An early attempt to give the traveling salesman run a fighting chance by supplying the simple route as a starting point
    '''
    startlist = api.getfaction('Canonn')['faction_presence']

    answer = simple(startlist[0], startlist[1::].copy(), None)
    answer = tsales(list(), 0, answer['route'][:], None)

    print('BEST')
    for p in answer['route']:
        print(f"{p['system_name']} ({int(p.get('dist',0))})", end=" ")
    print(int(answer['dist']), 'ly')
    return None


def printRoute(route, title):
    print(f"*** {title} Route ***")
    jumps = 0
    for p in route['route']:
        if p.get('dist', 0) > 0:
            print(f"{p['system_name']}")
            jumps += 1

    print(f"*** {int(route['dist'])} ly, {jumps} Systems ***")


if __name__ == '__main__':
    # What list of systems do want to use ?
    mode = ['Manual', 'Full Tour', 'Expansion Check', 'Patrol'][3]

    # Look in Journals so you start the route in your current location 
    system_names = [whereami()]
    print(f'Starting from {whereami()}')
    if not system_names:
        system_names = []

    if mode == 'Manual':  # Manual List
        system_names += """Col 285 Sector TZ-O c6-23
Evenses
Mahatrents
Ngundjedes
Sekenks""".split('\n')
    elif mode == 'Full Tour':  # All Canonn Systems
        systems = api.getfaction('Canonn')['faction_presence']
        for sys in systems:
            system_names.append(sys['system_name'])
    elif mode == 'Expansion Check':  # All Canonn Systems over 70% Inf
        systems = api.getfaction('Canonn')['faction_presence']
        for sys in systems:
            if sys['influence'] >= 0.70:
                system_names.append(sys['system_name'])
    elif mode == 'Patrol':  # All Systems mentioned on the CSNPatrol
        patrol = api.CSNPatrol()
        for patrolLine in patrol:
            if patrolLine['icon'] not in [':information_source: ', ':clap: ', ':anchor: ']:
                system_names.append(patrolLine['system'])

    # Now we have a simple list of the system names, get full system data
    route = list()
    for system_name in system_names:
        sys = api.getsystem(system_name)
        # discard any that have already been scanned this tick
        # allways add the 1st one, its your current location/starting point
        if sys and ((not sys['fresh']) or (not route) or mode == 'Manual'):
            route.append(sys)

    printRoute(simple(route[0], route[1::].copy(), None), mode)


    print('Done', api.NREQ)

