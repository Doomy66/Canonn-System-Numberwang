import requests
import simplejson as json
import os
import sys
import csv
import discord
import CSNSettings
from discord import Webhook, RequestsWebhookAdapter, File
from datetime import datetime
from Overrides import CSNOverRideRead
from Overrides import CSNOverRideReadSafe
from Overrides import CSNPatrolWrite

# Settings
factionname = CSNSettings.factionname
M_INFGAP = 15  # Minimum difference in Inf before issueing a mission
M_MININF = 40  # Minimum Inf before issueing a mission
LOCAL_OVERRIDE = False  # Use a local Override file or look up the Canonn Overrides page
# Globel Variables
FACTION_CACHE = dict()  
SYSTEM_CACHE = dict()

NREQ = 0

def external_system(system_name,id=0):
    global NREQ
    url = 'https://eddbapi.kodeblox.com/api/v4/systems'
    if id == 0:
        payload = {'name': system_name}
    else:
        payload = {'eddbid': id}

    r = requests.get(url, params=payload)
    try:
        myload = json.loads(r._content)["docs"][0]
    except:
        print(f'!System Not found : {system_name}{id}')
        return(None)

    # consistent nameing between objects
    myload["system_name"] = myload["name"]
    NREQ += 1
    return(myload)

def sysnatives(name):
    global NREQ
    ans = list()
    url = 'https://eddbapi.kodeblox.com/api/v4/factions'
    payload = {'homesystemname': name}
    r = requests.get(url, params=payload)
    myload = json.loads(r._content)["docs"]
    NREQ += 1

    for f in myload:
        ans.append(f['name'])
    return ans

def getfactiondata(name, force = False, fulldata = False):
    global FACTION_CACHE, NREQ
    if force or not name in FACTION_CACHE:
        url = 'https://elitebgs.app/api/ebgs/v4/factions'
        payload = {'name': name}
        r = requests.get(url, params=payload)
        myload = json.loads(r._content)["docs"][0]
        FACTION_CACHE[name]=myload

        NREQ += 1
    if fulldata:
        return FACTION_CACHE[name]
    else:
        return FACTION_CACHE[name]['faction_presence']
    
def getsystemdata(name):
    global SYSTEM_CACHE,NREQ
    if not name in SYSTEM_CACHE:
        url = 'https://elitebgs.app/api/ebgs/v4/systems'
        payload = {'name': name}
        r = requests.get(url, params=payload)
        myload = json.loads(r.content)["docs"][0]
        SYSTEM_CACHE[name] = myload
        NREQ += 1
    return SYSTEM_CACHE[name]

def fcsystem(station):
    global NREQ
    url = 'https://eddbapi.kodeblox.com/api/v4/stations'
    payload = {'name': station}
    r = requests.get(url, params=payload)
    myload = json.loads(r._content)["docs"][0]
    NREQ += 1
    s_id = myload['system_id']
    sys = external_system('',s_id)

    return(sys)

def BGSDownloader(argv=''):
    global NREQ
    print(f'Processing BGS Data for {factionname}')

    myfile = 'Faction.json'
    if not(os.path.isfile(myfile)):
        oldsl = []
    else:
        with open(myfile, 'r') as io:
            oldsl = json.load(io)

    # List of all systems the faction has a presence in.
    # This is the master structure that has additional data attached used for processing later
    faction_systems = getfactiondata(factionname,True)

    # Loop through all the systems that the faction is present in
    for sys in faction_systems:

        # get full data on the system. contaings xyz and other factions
        print(sys['system_name'])
        # Previous Run
        olds = list(
            filter(lambda o: o['system_name'] == sys['system_name'], oldsl))

        if len(olds) == 1 and olds[0]['updated_at'] == sys['updated_at']:  # No Change
            myload = olds[0]
            inflist = olds[0]['inflist']
        else:  # Reread entire system
            NREQ += 1
            url = 'https://elitebgs.app/api/ebgs/v4/systems'
            payload = {'name': sys['system_name']}
            r = requests.get(url, params=payload)
            myload = json.loads(r.content)["docs"][0]
            inflist = myload["factions"]
            # Loop through all the factions that are present in the system
            for y in range(len(inflist)):
                thisf = inflist[y]
                print('.'+thisf["name"])
                ffaction = getfactiondata(thisf["name"])
                # get other factions data to find influence and states
                ffactionsys = list(
                    filter(lambda x: x['system_name'] == sys["system_name"], ffaction))[0]
                # copy other faction influence data
                thisf["influence"] = ffactionsys["influence"]*100
                thisf["active_states"] = ffactionsys["active_states"]
                thisf["conflicts"] = ffactionsys["conflicts"]
                thisf["pending_states"] = ffactionsys["pending_states"]

        # write x,y,z to parent
        sys["x"] = myload["x"]
        sys["y"] = myload["y"]
        sys["z"] = myload["z"]
        sys["population"] = myload["population"]
        sys["eddb_id"] = myload["eddb_id"]
        sys["system_address"] = int(myload["system_address"]) # FD's System ID as per the Journal

        # inflist should now be full of all factions and their values for this system and can be added to the main structure
        sys["inflist"] = inflist

    # Save Faction File
    factionfile = 'Faction.json'
    if os.path.isfile(factionfile):
        os.remove(factionfile)
    with open(factionfile, 'w') as io:
        json.dump(faction_systems, io)

    print('Base Date Generated')
    return faction_systems


def Misson_Gen(argv):
    # print(argv)
    if "/?" in argv:
        print("Canonn System Numberwang:")
        print(" /new = Force new data")
        print(" /safe = Do not post results to Google")
        print(" /wait = Pause console at end to review output")
        quit

    faction_systems = BGSDownloader(argv)

    if LOCAL_OVERRIDE:
        # Local Overrides
        oridefile = f'{factionname}Overrides.csv'
        if os.path.isfile(oridefile):
            with open(oridefile, newline='') as io:
                reader = csv.reader(io, delimiter='\t')
                orides = list(reader)
            for x in orides[1:]:  # Yeah, can probably be done in 1 statement
                x[1] = int(x[1])
    elif '/safe' in argv:
        # Google Sheer Via Read
        orides = CSNOverRideReadSafe()
    else:
        # Google Sheet via API
        orides = CSNOverRideRead()

    try:
        with open(f'{factionname}Message.json', 'r') as io:
            oldmessage = json.load(io)
    except:
        oldmessage = []

    messages = []
    active_states = []
    pending_states = []
    recovering_states = []

    dIcons = {"war": '<:EliteEagle:231083794700959744> ',
              "election": ':ballot_box: ',
              "civilwar": '<:EliteEagle:231083794700959744> ',
              "override": '<:canonn:231835416548999168> ',
              "push": '<:Salute2:500679418692501506> ',
              "data": ':eyes: ',
              "infgap": ':dagger: ',
              "mininf": ':chart_with_downwards_trend: ',
              "info": ':information_source: ',
              "end": ':clap: '}

    print(f'CSN Missions:')
    # Create a single Message for each faction system
    for sys in faction_systems:
        # Sort all factions by influence
        sys['inflist'] = sorted(sys['inflist'],
                     key=lambda x: x['influence'], reverse=True)
        inf = sys['inflist']
        updated = EliteBGSDateTime(sys["updated_at"])
        age = datetime.now() - updated
        oride = list(filter(lambda x: x[0] == sys["system_name"], orides))

        # Single Message per sysme for Patrol
        if len(oride) > 0:  # OVERRIDE!
            messages.append(
                amessage(sys, oride[0][1], oride[0][2]+'*',
                         dIcons['override'] if oride[0][3] == '' else dIcons[oride[0][3]]))
        # Conflict Active
        elif len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, sys['active_states']))) > 0:
            thisconflict = sys["conflicts"][0]
            messages.append(amessage(
                sys, 2, '{3} against {0} ({1} v {2})'.format(
                    thisconflict["opponent_name"],
                    thisconflict["days_won"], dayslost(
                        sys["system_name"], thisconflict["opponent_name"]),
                    thisconflict["type"].title()),
                dIcons[thisconflict["type"]],
            ))
        # Conflict Pending
        elif len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, sys['pending_states']))) > 0:
            thisconflict = sys["conflicts"][0]
            messages.append(amessage(
                sys, 2, '{1} Pending with {0}'.format(
                    thisconflict["opponent_name"],
                    thisconflict["type"].title()),
                dIcons[thisconflict["type"]],
            ))
        # Not yet in control
        elif inf[0]['name'] != factionname:
            messages.append(
                amessage(sys, 3, f'Boost {factionname} for system control', dIcons['push']))
        # Gap to 2nd place is low
        elif len(inf) > 1 and inf[0]['influence']-inf[1]['influence'] < M_INFGAP:
            messages.append(
                amessage(sys, 4, f'Boost {factionname} - {inf[1]["name"]} is threatening ({inf[0]["influence"]-inf[1]["influence"]:4.3}%)', dIcons['infgap']))
        # Data out of date
        elif age.days > (inf[0]['influence']/10):
            messages.append(
                amessage(sys, 11, f'Scan System to update data {int(age.days)} days old', dIcons['data']))

        # Conflict Complete Info - Additional Message, not for Patrol, but for Discord
        if len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, sys['recovering_states']))) > 0:
            thisconflict = sys["conflicts"][0]
            if thisconflict["days_won"] == dayslost(sys["system_name"], thisconflict["opponent_name"]):
                # Draw
                asset = ''
            elif thisconflict["days_won"] > dayslost(sys["system_name"], thisconflict["opponent_name"]):
                # Won
                asset = assetatrisk(sys["system_name"],
                                    thisconflict["opponent_name"])
                if asset != '':
                    asset = 'Gained ' + asset
            else:
                # Lost
                asset = thisconflict["stake"]
                if asset != '':
                    asset = 'Lost ' + asset

            messages.append(amessage(
                sys, 21, '{3} against {0} Complete ({1} v {2}) {4}'.format(
                    thisconflict["opponent_name"],
                    thisconflict["days_won"], dayslost(
                        sys["system_name"], thisconflict["opponent_name"]),
                    thisconflict["type"].title(),
                    asset),
                dIcons["info"]))

        # Record All States for Usefull Summary Information
        for x in sys['active_states']:
            active_states.append([sys["system_name"], x["state"]])
        for x in sys['pending_states']:
            pending_states.append([sys["system_name"], x["state"]])
        for x in sys['recovering_states']:
            recovering_states.append([sys["system_name"], x["state"]])

    # Messages for External Systems
    for ex in orides[1:]:
        if sum(x["system_name"] == ex[0] for x in faction_systems) == 0:
            exsys = external_system(ex[0])
            try:
                messages.append(amessage(exsys, ex[1], ex[2]+'*',
                                         dIcons['override'] if ex[3] == '' else dIcons[ex[3]]))
            except:
                print(f'!Override Ignored : {ex[0]} {ex[2]}')

    # Lowest Gaps for PUSH message
    l = list(filter(lambda x: not hasmessage(messages,x['system_name']),faction_systems))
    l.sort(key = lambda s: s['inflist'][0]['influence'] - s['inflist'][1]['influence'] if len(s['inflist'])>1 else 100 )
    for sys in l[:3]:
        messages.append(
            amessage(sys, 5, f'Boost {factionname} to crush the hopes of {sys["inflist"][1]["name"]} (gap is {sys["inflist"][0]["influence"]-sys["inflist"][1]["influence"]:4.3}%)', dIcons['mininf']))

    messages.sort()

    # Fleet Carrier Locations
    try:
        messages.append(amessage(fcsystem('TNY-09Z'), 9, 'Dryad University (Mining and Mission Trade)', dIcons['info']))
    except:
        print('!!! Fleet Carrier TNY-09Z Failed !!!')
    try:
        messages.append(amessage(fcsystem('LFV-84Z'), 9, 'Gnosis B (Science Trade)', dIcons['info']))
    except:
        print('!!! Fleet Carrier LFV-84Z Failed !!!')
    try:
        messages.append(amessage(fcsystem('QLF-TQM'), 9, 'Symmachia (Mining and Mission Trade)', dIcons['info']))
    except:
        print('!!! Fleet Carrier QLF-TQM Failed !!!')
    try:        
        messages.append(amessage(fcsystem('N0K-L9Z'), 9, 'Jormungandr (Conflict Support)', dIcons['info']))
    except:
        print('!!! Fleet Carrier N0K-L9Z Failed !!!')
    try:
        messages.append(amessage(fcsystem('XF4-91W'), 9, 'Valhalla (Conflict Support)', dIcons['info']))
    except:
        print('!!! Fleet Carrier XF4-91W Failed !!!')
    try:
        messages.append(amessage(fcsystem('M9G-B1Z'), 9, 'Hoxxes Lament (Mining Carrier)', dIcons['info']))
    except:
        print('!!! Fleet Carrier M9G-B1Z Failed !!!')

    # Looks for changes in Discord suitable Messages since last run for WebHook
    messagechanges = []
    for x in messages:
        if (x not in oldmessage) or ('/new' in argv):
            messagechanges.append(x)
    # Looks to see what systems no longer have a message of any type
    for x in oldmessage:
        s = list(filter(lambda y: y[1] == x[1], messages))
        if len(s) == 0 and x[8] != dIcons['info']:
            messagechanges.append(x)
            messagechanges[len(messagechanges) - 1][7] = '~~'+ messagechanges[len(messagechanges) - 1][7] + '~~ : Misson Complete'
            messagechanges[len(messagechanges) - 1][8] = dIcons['end']

    for m in messages:
        print(f'{m[1]} : {m[7]}')

    # Write Orders various formats
    with open(f'{factionname}Patrol.Csv', 'w') as io:  # CSV for Humans
        io.writelines(f'System,X,Y,Z,Priority,Message\n')
        io.writelines(
            f'{x[1]},{x[2]},{x[3]},{x[4]},{x[5]},{x[7]}\n' for x in messages)
    with open(f'{factionname}DiscordPatrol.txt', 'w') as io:  # Text Version for Discord
        io.writelines(f'Canonn System Numberwang\n')
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] < 11 or x[0] > 20, messages))
    with open(f'{factionname}DiscordWebhook.txt', 'w') as io:  # Webhook Text Version for Discord
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] < 11 or x[0] > 20, messagechanges))
    with open(f'{factionname}Message.json', 'w') as io: # Dump to file for comparison next run
        json.dump(messages, io, indent=4)

    # Discord Webhook
    if len(list(filter(lambda x: x[0] < 11 or x[0] > 20, messagechanges))) > 0 and CSNSettings.wh_id != '':
        wh_text = ''
        wh = Webhook.partial(CSNSettings.wh_id, CSNSettings.wh_token,
                             adapter=RequestsWebhookAdapter())
        for x in filter(lambda x: x[0] < 11 or x[0] > 20, messagechanges):
            wh_text += f'{x[8]}{x[1]} : {x[7]}\n'
        if wh_text != '':
            wh.send(
                f'{"**Full Report**" if ("/new" in argv) else "Latest News"} <:canonn:231835416548999168> \n{wh_text}')

    # Patrol to send to Google
    patrol = []
    for x in filter(lambda x: x[0] <= 20, messages):
        patrol.append(x[1:8])
    if not('/safe' in argv):
        CSNPatrolWrite(patrol)

    print('*** Missions Generated : Consuming {0} requests ***'.format(NREQ))
    if ('/wait') in argv:
        input("Press Enter to continue...")

def hasmessage(messages,sysname):
    for m in messages:
        if m[1] == sysname:
            return True
    return False

def amessage(sys, p, message, icon=''):
    return([p, sys["system_name"], sys["x"], sys["y"], sys["z"], 0, factionname, message, icon])


def dayslost(system_name, faction):
    try:
        return(list(filter(lambda x: x["system_name"] == system_name, getfactiondata(faction)))[0]["conflicts"][0]["days_won"])
    except:
        return(0)


def assetatrisk(system_name, faction):
    try:
        return(list(filter(lambda x: x["system_name"] == system_name, getfactiondata(faction)))[0]["conflicts"][0]["stake"])
    except:
        return('')


def EliteBGSDateTime(s):
    dformat = '%Y-%m-%dT%H:%M:%S'  # so much grief from this function
    return(datetime.strptime(s[:len(dformat) + 2], dformat))


if __name__ == '__main__':
    Misson_Gen(sys.argv[1:] + ["/Test2", "/Test3"])
