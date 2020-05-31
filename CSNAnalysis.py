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
FACTION_CACHE = []  # Yeah, bad code I know, should have a Cache Class
NREQ = 0

def external_system(system_name):
    global NREQ
    url = 'https://elitebgs.app/api/ebgs/v4/systems'
    payload = {'name': system_name}
    r = requests.get(url, params=payload)
    try:
        myload = json.loads(r._content)["docs"][0]
    except:
        print(f'!System Not found : {system_name}')
        return(None)
    
    # consistent nameing between objects
    myload["system_name"] = myload["name"]
    NREQ += 1
    return(myload)


def getfactiondata(name):
    global FACTION_CACHE, NREQ
    s = list(filter(lambda x: x['name'] == name, FACTION_CACHE))
    if len(s) == 0:
        url = 'https://elitebgs.app/api/ebgs/v4/factions'
        payload = {'name': name}
        r = requests.get(url, params=payload)
        myload = json.loads(r._content)["docs"][0]
        x = myload["faction_presence"]
        FACTION_CACHE.append({"name": name, "sys": x})
        NREQ += 1
    else:
        x = s[0]["sys"]

    return(x)


def BGSDownloader():
    global NREQ
    print(f'Processing BGS Data for {factionname}')

    # List of all systems the faction has a presence in.
    # This is the master structure that has additional data attached used for processing later
    faction_systems = getfactiondata(factionname)

    # Loop through all the systems that the faction is present in
    for x in range(len(faction_systems)):
        # get full data on the system. contaings xyz and other factions
        sys = faction_systems[x]
        print(sys['system_name'])
        url = 'https://elitebgs.app/api/ebgs/v4/systems'
        payload = {'name': faction_systems[x]['system_name']}
        r = requests.get(url, params=payload)
        myload = json.loads(r.content)["docs"][0]
        inflist = myload["factions"]
        NREQ += 1
        # write x,y,z to parent
        sys["x"] = myload["x"]
        sys["y"] = myload["y"]
        sys["z"] = myload["z"]
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

        # inflist should now be full of all factions and their values for this system and can be added to the main structure
        sys["inflist"] = inflist

    # Save Faction File
    factionfile = 'Faction.json'
    if os.path.isfile(factionfile):
        os.remove(factionfile)
    with open(factionfile, 'w') as io:
        json.dump(faction_systems, io)

    print('Base Date Generated')


def Misson_Gen(argv):
    #print(argv)
    if "/?" in argv:
        print("Canonn System Numberwang:")
        print(" /new = Force new data")
        print(" /safe = Do not post results to Google")
        print(" /wait = Pause console at end to review output")
        quit

    myfile = 'Faction.json'
    if ('/new') in argv or not(os.path.isfile(myfile)):
        BGSDownloader()

    with open(myfile, 'r') as io:
        faction_systems = json.load(io)

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
    dIcons = {"war": ':EliteEagle: ' , 
        "election": ':ballot_box: ', 
        "civilwar": ':EliteEagle: ',
        "override": ':Salute: ',
        "push": ':Salute2: ',
        "data": ':eyes: ',
        "infgap": ':dagger: ',
        "mininf": ':worried: ',
        "info": ':information_source: '}


    print(f'CSN Missions:')
    # Create a single Message for each faction system
    for sys in faction_systems:
        # Sort all factions by influence
        inf = sorted(sys['inflist'],
                     key=lambda x: x['influence'], reverse=True)
        dformat = '%Y-%m-%dT%H:%M:%S'  # so much grief from this function
        age = datetime.now() - datetime.strptime(sys["updated_at"][:len(dformat)+2], dformat)  # print(age.days)
        # TODO Complete Conflict Info (active, pending, finished)
        # TODO Info messages

        oride = list(filter(lambda x: x[0] == sys["system_name"], orides))
        

        # Single Message per sysme for Patrol
        if len(oride) > 0:  # OVERRIDE!
            messages.append(
                amessage(sys, oride[0][1], oride[0][2]+'*', dIcons['override']))
        # Conflict Active
        elif len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'},sys['active_states']))) > 0:
            thisconflict = sys["conflicts"][0]  
            messages.append(amessage(
                sys, 2, '{3} against {0} ({1} v {2})'.format(
                    thisconflict["opponent_name"], 
                    thisconflict["days_won"], dayslost(sys["system_name"],thisconflict["opponent_name"]), 
                    thisconflict["type"].title()),
                dIcons[thisconflict["type"]],
                ))
        # Conflict Pending
        elif len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'},sys['pending_states']))) > 0:
            thisconflict = sys["conflicts"][0]  
            messages.append(amessage(
                sys, 2, '{1} Pending with {0}'.format(
                    thisconflict["opponent_name"], 
                    thisconflict["type"].title()),
                dIcons[thisconflict["type"]],
                ))
        # Push  conrol
        elif inf[0]['name'] != factionname:  
            messages.append(
                amessage(sys, 3, f'Boost {factionname} for system control', dIcons['push']))
        # Gap to 2nd place is low
        elif inf[0]['influence']-inf[1]['influence'] < M_INFGAP:  
            messages.append(
                amessage(sys, 4, f'Boost {factionname} - {inf[1]["name"]} is threatening ({inf[0]["influence"]-inf[1]["influence"]:4.3}%)', dIcons['infgap']))
        # Inf is too low
        elif inf[0]['influence'] < M_MININF:  
            messages.append(amessage(
                sys, 5, f'Boost {factionname} - vulnerable at {inf[0]["influence"]:4.3}%', dIcons['mininf']))
        # Data out of date
        elif age.days > (inf[0]['influence']/10):  
            messages.append(
                amessage(sys, 11, f'Scan System to update data {int(age.days)} days old', dIcons['data']))

        # Conflict Complete Info
        if len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'},sys['recovering_states']))) > 0:
            thisconflict = sys["conflicts"][0]
            if thisconflict["days_won"] == dayslost(sys["system_name"],thisconflict["opponent_name"]):
                # Draw
                asset=''
            elif  thisconflict["days_won"]>dayslost(sys["system_name"],thisconflict["opponent_name"]):
                # Won
                asset = assetatrisk(sys["system_name"],thisconflict["opponent_name"])
                if asset != '':
                    asset = 'Gained '+ asset
            else:
                # Lost
                asset = thisconflict["stake"]
                if asset != '':
                    asset = 'Lost '+ asset

            messages.append(amessage(
                sys, 21, '{3} against {0} Complete ({1} v {2}) {4}'.format(
                    thisconflict["opponent_name"], 
                    thisconflict["days_won"], dayslost(sys["system_name"],thisconflict["opponent_name"]), 
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
                messages.append(amessage(exsys, ex[1], ex[2]+'*', dIcons['override']))
            except:
                print(f'!Override Ignored : {ex[0]} {ex[2]}')
    messages.sort()

    # Looks for changes in Discord suitable Messages since last run for WebHook
    messagechanges = []
    for x in messages:
        if x not in oldmessage:
            messagechanges.append(x)
    # Looks to see what systems no longer have a message of any type
    for x in oldmessage:
        s = list(filter(lambda y: y[1] == x[1], messages))
        if len(s) == 0:
            messagechanges.append(x)
            messagechanges[len(messagechanges)-1][7] += ' : Misson Complete'
            messagechanges[len(messagechanges)-1][8] = dIcons['info']
    
    # Write Orders various formats
    with open(f'{factionname}Patrol.Csv', 'w') as io:  # CSV for Humans
        io.writelines(f'System,X,Y,Z,Priority,Message\n')
        io.writelines(
            f'{x[1]},{x[2]},{x[3]},{x[4]},{x[5]},{x[7]}\n' for x in messages)
    with open(f'{factionname}DiscordPatrol.txt', 'w') as io:  # Text Version for Discord
        io.writelines(f'Canonn System Numberwang\n')
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(lambda x: x[0]<11 or x[0]>20, messages))
    with open(f'{factionname}DiscordWebhook.txt', 'w') as io:  # Webhook Text Version for Discord
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(lambda x: x[0]<11 or x[0]>20, messagechanges))
    with open(f'{factionname}Message.json', 'w') as io:
        json.dump(messages,io, indent=4)


    # Discord Webhook
    if len(list(filter(lambda x: x[0]<11 or x[0]>20, messagechanges)))>0 and CSNSettings.wh_id != '':
        wh_text = ''
        wh = Webhook.partial(CSNSettings.wh_id, CSNSettings.wh_token,\
            adapter = RequestsWebhookAdapter())
        for x in filter(lambda x: x[0]<11 or x[0]>20, messagechanges):
            wh_text+=f'{x[8]}{x[1]} : {x[7]}\n' 
        if wh_text != '':
            wh.send(wh_text)

    # Patrol to send to Google
    patrol=[]
    for x in filter(lambda x : x[0]<=20, messages):
        patrol.append(x[1:8])
    if not('/safe' in argv):
        CSNPatrolWrite(patrol)

    for m in messages:
        print(f'{m[1]} : {m[7]}')


    print('*** Missions Generated : Consuming {0} requests ***'.format(NREQ))
    if ('/wait') in argv:
        input("Press Enter to continue...")

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
        
if __name__ == '__main__':
    Misson_Gen(sys.argv[1:]+["/Test2","/Test3"])
