from os.path import join
from Bubble import Bubble, update_progress
import simplejson as json
import os
import sys
import csv
import CSNSettings
from ExpansionTarget import InvasionAlert
from discord import Webhook, RequestsWebhookAdapter
from datetime import datetime
from Overrides import CSNAttractions, CSNOverRideRead, CSNSchedule
from Overrides import CSNOverRideReadSafe
from Overrides import CSNPatrolWrite
from Overrides import CSNFleetCarrierRead
import Bubble
import api

# Settings

M_INFGAP = 15  # Minimum difference in Inf before issueing a mission
M_MININF = 40  # Minimum Inf before issueing a mission
LOCAL_OVERRIDE = not CSNSettings.override_sheet

def Misson_Gen(argv=''):

    # print(argv)
    if "/?" in argv:
        print("Canonn System Numberwang:")
        print(" /new = Force all new data")
        print(" /safe = Do not post results to Google")
        print(" /wait = Pause console at end to review output")
        print(" /schedule = Run according to Patrol Schedule")

        quit

    # check if any action is scheduled and apply the specified argument, exit if no action scheduled
    if "/schedule" in argv:
        schedule = CSNSchedule()
        if schedule:
            argv += [f"/{schedule}"]
        else:
            print('No Schedule')
            return None

    bubble = Bubble.Bubble()
    faction_systems = bubble.localspace
    factionnames = bubble.factionnames
    orides = list

    if LOCAL_OVERRIDE:
        # Local Overrides
        oridefile = f'data\\{factionnames[0]}Overrides.csv'
        if os.path.isfile(oridefile):
            with open(oridefile, newline='') as io:
                reader = csv.reader(io, delimiter='\t')
                orides = list(reader)
            for x in orides[1:]:  # Yeah, can probably be done in 1 statement
                x[1] = int(x[1])
    elif '/safe' in argv:
        # Google Sheet Via Read
        orides = CSNOverRideReadSafe()
    else:
        # Google Sheet via API
        orides = CSNOverRideRead()

    try:
        with open(f'data\\{factionnames[0]}Message.json', 'r') as io:
            oldmessage = json.load(io)
    except:
        oldmessage = []
        
    try:
        with open(f'data\\{factionnames[0]}Invaders.json', 'r') as io:
            invaders = json.load(io)
    except:
        invaders = []

    messages = []
    active_states = []
    pending_states = []
    recovering_states = []
    ootsystems = []
    detected_retreats = []

    dIcons = {"war": '<:EliteEagle:231083794700959744> ',
              "election": ':ballot_box: ',
              "civilwar": '<:EliteEagle:231083794700959744> ',
              "override": '<:canonn:231835416548999168> ',
              "push": '<:Salute2:500679418692501506> ',
              "data": ':eyes: ',
              "infgap": ':dagger: ',
              "mininf": ':chart_with_downwards_trend: ',
              "info": ':information_source: ',
              "end": ':clap: ',
              "FC": ':anchor: ', 
              "notfresh": ':arrows_counterclockwise: '}

    print(f'CSN Missions:')
    # Create a single Message for each faction system
    faction_systems = dict(filter(lambda x: x[1],faction_systems.items()))
    for i, key in enumerate(faction_systems):
        update_progress(i/len(faction_systems),key)
        sys = faction_systems[key]
        if sys:
            sys['factions'].sort(key = lambda x: x['influence'],reverse=True)
            factions =sys['factions']
            empire = sys['empire']
            happytext = empire['faction_details']['faction_presence']['happiness']
            happy = 'Elated' if happytext=='$faction_happinessband1;' else 'Happy' if happytext=='$faction_happinessband2;' else 'Pieved'

            conflict = None

            if len(factions) > 1:
                gap = factions[0]["influence"]-factions[1]["influence"]
                gapfromtop = factions[0]["influence"]-(empire['influence'])
            else:
                gap = 100
                gapfromtop = 0

            updated = Bubble.EliteBGSDateTime(sys["updated_at"])
            age = datetime.now() - updated
            oride = list(filter(lambda x: x[0] == sys["system_name"], orides))
            faction_systems[key]['override'] = oride[0][4] if oride else 'Natural'

            if sys['name'] == 'DUBUG':
                print(f'Debug')

            # Single Message per sysme for Patrol
            if faction_systems[key]['override'] != 'Natural':  # OVERRIDE!
                for newmessage in oride:
                    messages.append(
                        amessage(sys, newmessage[1], newmessage[2].format(gap=gap, inf=empire['influence'],happy=happy)+'*',
                                dIcons['override'] if newmessage[3] == '' else dIcons[newmessage[3]]))
            
            if faction_systems[key]['override'] != 'Override':
                # Conflict Active
                if len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, empire['active_states']))) > 0:
                    conflict = empire["conflicts"][0]
                    messages.append(amessage(
                        sys, 2, '{3} against {0} ({1} v {2})'.format(
                            conflict["opponent_name"],
                            conflict["days_won"], bubble.dayswon(
                                sys["system_name"], conflict["opponent_name"]),
                            conflict["type"].title()),
                        dIcons[conflict["type"]],
                    ))
                    faction_systems[key]['override'] = 'Done'
                # Conflict Pending
                elif len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, empire['pending_states']))) > 0:
                    conflict = empire["conflicts"][0]
                    messages.append(amessage(
                        sys, 2, '{1} Pending with {0}. No action required while Pending, but you can prepare'.format(
                            conflict["opponent_name"],
                            conflict["type"].title()),
                        dIcons[conflict["type"]],
                    ))
                    faction_systems[key]['override'] = 'Done'

                if (not conflict) and faction_systems[key]['override'] in {'Addition', 'Natural'}:
                    # Not yet in control
                    if factions[0]['name'] not in factionnames:
                        messages.append(
                            amessage(sys, 3, f'Urgent: {sys["empire"]["name"]} {availableactions(faction_systems[key],factionnames)} to gain system control (gap {gapfromtop:4.3}%)', dIcons['push']))
                    # Gap to 2nd place is low
                    elif gap < M_INFGAP:
                        messages.append(
                            amessage(sys, 4, f'Required: {sys["empire"]["name"]} {availableactions(faction_systems[key],factionnames)} ({factions[1]["name"]} is threatening, gap is only {gap:4.3}%)', dIcons['infgap']))

            # Multi Messages
            # Data out of date
            if age.days > (factions[0]['influence']/10):
                messages.append(
                    amessage(sys, 11, f'Scan System to update data {int(age.days)} days old', dIcons['data']))

            # Pending Tritium Refinary Low Price
            if (len(list(filter(lambda x: x['state'] in {'drought', 'blight', 'terrorism'}, empire['pending_states']))) > 0) and sys.get('sellsTritium',False): 
                messages.append(
                    amessage(sys, 25, f'Tritium Opportunity Warning', dIcons['data']))

            # Active Tritium Refinary Low Price
            if (len(list(filter(lambda x: x['state'] in {'drought', 'blight', 'terrorism'}, empire['active_states']))) > 0) and sys.get('sellsTritium',False):
                messages.append(
                    amessage(sys, 24, f'Tritium Opportunity Active', dIcons['data']))

            # GOLDRUSH
            if next((x for x in empire['active_states']+empire['pending_states'] if x['state'] in {'infrastructurefailure'}),None):
                if next((x for x in sys['stations'] if x['economy'] in {'$economy_extraction;'}),None):
                    messages.append(
                        amessage(sys, 24, "Super " if next((x for x in empire['active_states']+empire['pending_states'] if x['state'] in {'civil liberty'}),None) else "" + f"Gold Rush Active or Pending", dIcons['data']))

            # Conflict Complete Info - Additional Message, not for Patrol, but for Discord
            if len(list(filter(lambda x: x['state'] in {'war', 'election', 'civilwar'}, empire['recovering_states']))) > 0:
                conflict = empire["conflicts"][0]
                if conflict["days_won"] == bubble.dayswon(sys["system_name"], conflict["opponent_name"]):
                    # Draw
                    asset = ''
                elif conflict["days_won"] > bubble.dayswon(sys["system_name"], conflict["opponent_name"]):
                    # Won
                    asset = bubble.assetatrisk(sys["system_name"],
                                        conflict["opponent_name"])
                    if asset != '':
                        asset = 'Gained ' + asset
                else:
                    # Lost
                    asset = conflict["stake"]
                    if asset != '':
                        asset = 'Lost ' + asset

                messages.append(amessage(
                    sys, 21, '{3} against {0} Complete ({1} v {2}) {4}'.format(
                        conflict["opponent_name"],
                        conflict["days_won"], bubble.dayswon(
                            sys["system_name"], conflict["opponent_name"]),
                        conflict["type"].title(),
                        asset),
                    dIcons["info"]))

            # Record All States for Usefull Summary Information
            for x in empire['active_states']:
                active_states.append([sys["system_name"], x["state"]])
            for x in empire['pending_states']:
                pending_states.append([sys["system_name"], x["state"]])
            for x in empire['recovering_states']:
                recovering_states.append([sys["system_name"], x["state"]])

            # Look for active Retreats
            for faction in sys['factions']:
                if next((x for x in faction['active_states'] if x['state'] == 'retreat'),None) and sys['name'] not in detected_retreats:
                    detected_retreats.append(sys['name'])

    update_progress(1)

    # Add Detected Retreats
    if detected_retreats:
        print('')
        messages.append(amessage('Retreats Detected in',25,', '.join(detected_retreats),dIcons['data']))

    # All Canonn Systems Processed
    # Messages for External Systems
    for ex in orides[1:]:
        if sum(faction_systems[x]["system_name"] == ex[0] for x in faction_systems) == 0:
            #exsys = bubble.findsystem(ex[0])
            exsys = api.getsystem(ex[0])
            if exsys:
                ex[2] = ex[2].replace('{inf}',f"{round(exsys['factions'][0]['influence'],1)}")                
                messages.append(amessage(exsys, ex[1], ex[2]+'*',
                                        dIcons['override'] if ex[3] == '' else dIcons[ex[3]],'None'))
            else:
                print(f'!Override Ignored : {ex[0]} {ex[2]}')

    # Invasion Alert
    if '/new' in argv: # Only worth processing once per day after the EDDB Data Dump at about 06:00
        invaders = InvasionAlert(factionnames[0])
    for sys in invaders:
        sys["system_name"] = sys["name"]
        # trim spurious data that was giving circular reference errors when trying to save
        sys['minor_faction_presences'] = list() 
        sys['xcube'] = list()
        if sys['controlling_minor_faction'] in sys['pf']: # Policy is we allow NPC to arrive so they fill the system and block PC factions
            messages.append(amessage(sys,10,f"{sys['controlling_minor_faction']} are targeting {sys['invading']} within {sys['cycles']} cycles : We should do something about this ({round(sys['influence'],1)}%)",dIcons['data']))

    # Lowest Gaps for PUSH message
    l = list(filter(lambda x: faction_systems[x]['override'] == 'Addition' or not hasmessage(
        messages, faction_systems[x]['system_name']), faction_systems))

    l.sort(key=lambda s: faction_systems[s]['factions'][0]['influence'] - faction_systems[s]['factions']
           [1]['influence'] if len(faction_systems[s]['factions']) > 1 else 100)

    for x in l[:3]:
        sys = faction_systems[x]
        if sys["factions"][0]["influence"]-sys["factions"][1]["influence"] < 35: # At a 35% Gap, it becomes spam
            messages.append(
                amessage(sys, 5, f'Suggestion: {sys["empire"]["name"]} {availableactions(sys,factionnames)} (gap to {sys["factions"][1]["name"]} is {sys["factions"][0]["influence"]-sys["factions"][1]["influence"]:4.3}%)', dIcons['mininf']))

    messages.sort()

    # Fleet Carrier Locations
    carriers = CSNFleetCarrierRead()
    for carrier in carriers:
        currentsystem = None
        if carrier['id'][0] != '!':
            try:
                thiscarrier = api.getfleetcarrier(carrier['id'])
                currentsystem = api.eddbSystem(thiscarrier['current_system'])
                messages.append(amessage(currentsystem, 9, f'{carrier["name"]} ({carrier["role"]})', dIcons['FC'],'Canonn'))
            except:
                pass
            if not currentsystem:
                print(f'!!! Fleet Carrier {carrier["id"]} Failed !!!')

    # Looks for changes in Discord suitable Messages since last run for WebHook
    messagechanges = []
    for x in messages:
        if (x not in oldmessage) or ('/new' in argv):
            messagechanges.append(x)
    # Looks to see what systems no longer have a message of any type
    for x in oldmessage:
        s = list(filter(lambda y: y[1] == x[1] and y[8] not in [dIcons['FC'],dIcons['info']], messages))
        if len(s) == 0 and x[8] not in [dIcons['FC'],dIcons['info']]:
            messagechanges.append(x)
            messagechanges[len(messagechanges) - 1][7] = '~~' + \
                messagechanges[len(messagechanges) - 1][7] + \
                '~~ : Mission Complete'
            messagechanges[len(messagechanges) - 1][8] = dIcons['end']

    for m in messages:
        print(f'{m[1]} : {m[7]}')

    # Write Orders various formats
    with open(f'data\\{factionnames[0]}Patrol.Csv', 'w') as io:  # CSV for Humans
        io.writelines(f'System,X,Y,Z,Priority,Message\n')
        io.writelines(
            f'{x[1]},{x[2]},{x[3]},{x[4]},{x[5]},{x[7]}\n' for x in messages)
    with open(f'data\\{factionnames[0]}DiscordPatrol.txt', 'w') as io:  # Text Version for Discord
        io.writelines(f'Canonn System Numberwang\n')
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] < 11 or x[0] > 20, messages))
    with open(f'data\\{factionnames[0]}DiscordWebhook.txt', 'w') as io:  # Webhook Text Version for Discord
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] < 11 or x[0] > 20, messagechanges))
    with open(f'data\\{factionnames[0]}Message.json', 'w') as io:  # Dump to file for comparison next run
        json.dump(messages, io, indent=4)
    with open(f'data\\{factionnames[0]}Invaders.json', 'w') as io:  # Dump to file for comparison next run
        json.dump(invaders, io, indent=4)

    # Discord Webhook
    if CSNSettings.wh_id and len(list(filter(lambda x: x[0] < 11 or x[0] > 20, messagechanges))) > 0 :
        wh_text = ''
        wh = Webhook.partial(CSNSettings.wh_id, CSNSettings.wh_token,
                             adapter=RequestsWebhookAdapter())
        for x in filter(lambda x: x[0] < 11 or x[0] > 20, messagechanges):
            wh_text += f"{x[8]}{x[1]} : {x[7]}{'' if x[9] else dIcons['notfresh'] }\n"
        if wh_text != '':
            wh.send(
                f'{"**Full Report**" if ("/new" in argv) else "Latest News"} <:canonn:231835416548999168> \n{wh_text}')

    # Patrol to send to Google
    patrol = []
    for x in filter(lambda x: x[0] <= 20, messages):
        patrol.append(x[1:9])
    if not('/safe' in argv):
        CSNPatrolWrite(patrol)

    if '/new' in argv:
        CSNAttractions(faction_systems)
    print('*** Missions Generated : Consuming {0} requests ***'.format(api.NREQ))
    if ('/wait') in argv:
        input("Press Enter to continue...")


def hasmessage(messages, sysname):
    for m in messages:
        if m[1] == sysname:
            return True
    return False

def amessage(sys, p, message, icon='', empire=''):
    # 0 Priority, 1 System Name, 2 x, 3 y, 4 z, 5 ?, 6 Faction, 7 Message, 8 Icon, 9 Fresh
    if isinstance(sys,str):
        return([p, sys, 0, 0, 0, 0, '', message, icon, True])
    else:
        return([p, sys["system_name"], sys["x"], sys["y"], sys["z"], 0, sys["empire"]["name"] if empire == '' and 'empire' in sys.keys() else empire, message, icon, True])



def availableactions(system,factionnames):
    '''
    Returns a text of available actions for the faction in that system which can be retricted if you dont own stations with the correct services
    '''
    stations = system['stations']
    slist = list()
    for station in stations:
        if station ['controlling_minor_faction_cased'] in factionnames:
            slist += list(x['name'] for x in station['services'])
        

    actions = ['Missions','Bounties']
    if 'commodities' in slist : actions += ['Trade']
    if 'exploration' in slist : actions += ['Data']

    return " and ".join([", ".join(actions[:-1]),actions[-1]] if len(actions) > 2 else actions)

if __name__ == '__main__':
    Misson_Gen(sys.argv[1:] + ["/Test1", "/!new"])