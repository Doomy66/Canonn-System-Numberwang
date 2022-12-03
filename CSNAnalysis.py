from os.path import join
from re import T
from Bubble import Bubble, update_progress
import simplejson as json
import os
import sys
import csv
import CSNSettings
from ExpansionTarget import EDDBReset, ExpansionCandidates, InvasionAlert
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
        print(" /invade = Check for Invasions (part of /new)")
        print(" /expansion = Recalculate Expansion Targets (part of /new)")

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
    all_overrides = list

    if LOCAL_OVERRIDE:
        # Local Overrides
        oridefile = f'data\\{factionnames[0]}Overrides.csv'
        if os.path.isfile(oridefile):
            with open(oridefile, newline='') as io:
                reader = csv.reader(io, delimiter='\t')
                all_overrides = list(reader)
            for x in all_overrides[1:]:  # Yeah, can probably be done in 1 statement
                x[1] = int(x[1])
    elif '/safe' in argv:
        # Google Sheet Via Read
        all_overrides = CSNOverRideReadSafe()
    else:
        # Google Sheet via API
        all_overrides = CSNOverRideRead()

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

    
    # Expansion Targets
    if '/new' in argv or '/expansion' in argv: # Only worth processing once per day after the EDDB Data Dump at about 06:00
        ExpansionCandidates(factionnames[0],inflevel=60,live=True,prebooked=list(faction_systems)[-1],extenedphase=CSNSettings.extendedphase)  # Will save results as a json for loading
        EDDBReset() # EDDB Frame may be mangled, reset so Invasion Alert still works
    try:
        with open(f'data\\{factionnames[0]}ExpansionTargets.json', 'r') as io:
            expansiontargets = json.load(io)
    except:
        expansiontargets = []


    messages = []
    active_states = []
    pending_states = []
    recovering_states = []
    detected_retreats = []

    dIcons = {"war": ':gun: ', #12/09/22 Stnadard Icons due to dead Discord
              "election": ':ballot_box: ',
              "civilwar": '<:EliteEagle:1020771075207991407> ',
              "override": '<:Salute2:1020771111073480715> ',
              "push": ':arrow_heading_up: ',
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
            happy = 'Elated' if happytext=='$faction_happinessband1;' else 'Happy' if happytext=='$faction_happinessband2;' else 'Discontent' if happytext=='$faction_happinessband3;' else '<SNAFU '+ happytext+'>'
            #happy = 'Elated' if happytext=='$faction_happinessband1;' else 'Happy' # Forget about the "none" bug. SEP
            expandto = 'None Detected'
            for e in expansiontargets:
                if e['name'] == sys['name']:
                    expandto = e['target']
                    if e['expansionType'] == 'Expansion (Extended)':
                        expandto += ' (Extended)'
                    elif e['expansionType'][0] == 'I':
                        expandto += ' ('+e['expansionType']+')'
            #print(f"{sys['name']} expanding to {expandto}")

            conflict = None

            if len(factions) > 1:
                gap = round(factions[0]["influence"]-factions[1]["influence"],1)
                gapfromtop = round(factions[0]["influence"]-(empire['influence']),1)
            else:
                gap = 100
                gapfromtop = 0

            updated = Bubble.EliteBGSDateTime(sys["updated_at"])
            age = datetime.now() - updated
            system_overrides = list(filter(lambda x: x[0] == sys["system_name"], all_overrides))
            faction_systems[key]['override'] = system_overrides[0][4] if system_overrides else 'Natural'

            if sys['name'] == 'debug':
                print(f'Debug')

            # Single Message per sysme for Patrol
            if faction_systems[key]['override'] != 'Natural':  # OVERRIDE!
                for newmessage in system_overrides:
                    # Default to Empire Faction
                    message_faction = empire['name']
                    message_inf = round(empire['influence'],1)
                    message_conflict = ''
                    # Look for another faction mentioned in the override
                    for f in faction_systems[key]['factions']:
                        if f['name'] in newmessage[2] and f['name'] != empire['name']:
                            message_faction = f['name']
                            message_inf = round(f['influence'],1)
                            if len(f['conflicts']): # There is a conflict
                                opponent = list(filter(lambda x: x['name']==f['conflicts'][0]['opponent_name'],faction_systems[key]['factions']))
                                if opponent:
                                    message_conflict = f"({f['conflicts'][0]['status'].capitalize() if f['conflicts'][0]['status'] else 'Complete'} {f['conflicts'][0]['days_won']} v {opponent[0]['conflicts'][0]['days_won']})"
                                    #print(message_conflict)

                    messages.append(
                        amessage(sys, newmessage[1], newmessage[2].format(gap=gap, inf=message_inf,happy=happy,conflict=message_conflict,expandto=expandto)+'*',
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

                if (not conflict) and faction_systems[key]['override'] in {'Addition', 'Natural'} and sys['name'] not in CSNSettings.surrendered_systems:
                    # Not yet in control
                    if factions[0]['name'] not in factionnames:
                        messages.append(
                            amessage(sys, 3, f'Urgent: {sys["empire"]["name"]} {availableactions(faction_systems[key],factionnames)} to gain system control (gap {gapfromtop:4.3}%)', dIcons['push']))
                        faction_systems[key]['override'] = 'Done'
                    # Gap to 2nd place is low
                    elif gap < M_INFGAP:
                        messages.append(
                            amessage(sys, 4, f'Required: {sys["empire"]["name"]} {availableactions(faction_systems[key],factionnames)} ({factions[1]["name"]} is threatening, gap is only {gap:4.3}%)', dIcons['infgap']))
                        faction_systems[key]['override'] = 'Done'

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
                if next((x for x in faction['active_states'] if x['state'] == 'retreat'),None) and sys['name'] not in detected_retreats and len(sys['factions'])>6:
                    detected_retreats.append(sys['name'])

            # Look for Non-Native Conflicts ##TODO But dont have Native Faction Info in Bubble. Hidden in the heavy load of EDDBFrame


    update_progress(1)

    # Add Detected Retreats
    if detected_retreats:
        print('')
        messages.append(amessage('Retreats Detected in',25,', '.join(detected_retreats),dIcons['data']))

    # All Canonn Systems Processed
    # Messages for External Systems
    for newmessage in all_overrides[1:]:
        if sum(faction_systems[x]["system_name"] == newmessage[0] for x in faction_systems) == 0:
            #exsys = bubble.findsystem(ex[0])
            exsys = api.getsystem(newmessage[0])
            if exsys:
                message_inf = round(exsys['factions'][0]['influence'],1)
                message_gap = round(exsys['factions'][0]['influence']-message_inf,1) 
                message_conflict = ''

                # Look for another faction mentioned in the override
                for f in exsys['factions']:
                    if f['name'] in newmessage[2]: #and f['name'] != exsys['controlling_minor_faction_cased']: ## Not sure what that limitation was for, but was preventing reporting of Conflict of Controlling Faction
                        message_faction = f['name']
                        message_inf = round(f['influence'],1)
                        message_gap = round(exsys['factions'][0]['influence']-message_inf,1) 

                        if len(f['conflicts']): # There is a conflict
                            opponent = list(filter(lambda x: x['name']==f['conflicts'][0]['opponent_name'],exsys['factions']))
                            if opponent:
                                message_conflict = f"({f['conflicts'][0]['status'].capitalize() if f['conflicts'][0]['status'] else 'Complete'} {f['conflicts'][0]['days_won']} v {opponent[0]['conflicts'][0]['days_won']})"
                                #print(message_conflict)



                newmessage[2] = newmessage[2].replace('{inf}',f"{message_inf}")                
                newmessage[2] = newmessage[2].replace('{gap}',f"{message_gap}")                
                newmessage[2] = newmessage[2].replace('{conflict}',f"{message_conflict}")                
                messages.append(amessage(exsys, newmessage[1], newmessage[2]+'*',
                                        dIcons['override'] if newmessage[3] == '' else dIcons[newmessage[3]],'None'))
            else:
                print(f'!Override Ignored : {newmessage[0]} {newmessage[2]}')

    # Invasion Alert
    if '/new' in argv or '/invade' in argv: # Only worth processing once per day after the EDDB Data Dump at about 06:00
        invaders = InvasionAlert(factionnames[0],live=True,lookahead=2)
    for sys in invaders:
        sys["system_name"] = sys["name"]
        # trim spurious data that was giving circular reference errors when trying to save
        sys['minor_faction_presences'] = list() 
        sys['xcube'] = list()
        if sys['controlling_minor_faction'] in sys['pf']: # Policy is we allow NPC to arrive so they fill the system and block PC factions
            messages.append(amessage(sys,10,f"{sys['controlling_minor_faction']} ({round(sys['influence'],1)}%) will {sys['invademessage']} {'to' if sys['invadetype'][0]=='E' else 'in'} {sys['invading']} within {sys['cycles']} cycles : {('Support Non-Native Factions in '+sys['invading']) if sys['invadetype'][0]=='I' else ''}",dIcons['data']))
            #print('')

    # Lowest Gaps for PUSH message
    l = list(filter(lambda x: x not in CSNSettings.surrendered_systems and (faction_systems[x]['override'] in {'Addition','Natural'} or not hasmessage(
        messages, faction_systems[x]['system_name'])), faction_systems))

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
    print('Saving Local Text...')
    with open(f'data\\{factionnames[0]}Patrol.Csv', 'w') as io:  # CSV for Humans
        io.writelines(f'System,X,Y,Z,Priority,Message\n')
        io.writelines(
            f'{x[1]},{x[2]},{x[3]},{x[4]},{x[5]},{x[7]}\n' for x in messages)
    with open(f'data\\{factionnames[0]}DiscordPatrol.txt', 'w') as io:  # Text Version for Discord
        io.writelines(f'Canonn System Numberwang\n')
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] <= 10 or (x[0] > 20 and x[0] <=30) , messages))
    with open(f'data\\{factionnames[0]}DiscordWebhook.txt', 'w') as io:  # Webhook Text Version for Discord
        io.writelines(f'{x[8]}{x[1]} : {x[7]}\n' for x in filter(
            lambda x: x[0] < 11 or (x[0] > 20 and x[0] <=30), messagechanges))
    with open(f'data\\{factionnames[0]}Message.json', 'w') as io:  # Dump to file for comparison next run
        json.dump(messages, io, indent=4)
    with open(f'data\\{factionnames[0]}Invaders.json', 'w') as io:  # Dump to file for comparison next run
        json.dump(invaders, io, indent=4)

    # Discord Webhook
    print('Webhook...')

    if CSNSettings.wh_id and len(list(filter(lambda x: x[0] < 11 or x[0] > 20, messagechanges))) > 0 :
        wh_text = ''
        wh_text_continued = ''
        wh = Webhook.partial(CSNSettings.wh_id, CSNSettings.wh_token,
                             adapter=RequestsWebhookAdapter())
        for x in filter(lambda x: x[0] < 11 or (x[0] > 20 and x[0]<=30), messagechanges):
            if len(wh_text) < 1850: # Max len for a single hook is 2000 chars. A message can be approx 100 and there is the additional header text.
                wh_text += f"{x[8]}{x[1]} : {x[7]}{'' if x[9] else dIcons['notfresh'] }\n"
            else:
                wh_text_continued += f"{x[8]}{x[1]} : {x[7]}{'' if x[9] else dIcons['notfresh'] }\n"

        print(f"Web Hook Text length is limited to 2000 chars : {len(wh_text)} + {len(wh_text_continued)}")
        ## csnicon = '<:canonn:231835416548999168>'
        csnicon = '<:canonn:1020771055532511312>'
        if wh_text != '':
            wh.send(
                f'{"**Full Report**" if ("/new" in argv) else "Latest News"} {csnicon} \n{wh_text}')
        if wh_text_continued != '':
            wh.send(
                f'"...continued {csnicon} \n{wh_text_continued}')

    # Patrol to send to Google
    patrol = []
    for x in filter(lambda x: x[0] <= 20, messages):
        patrol.append(x[1:9])
    if not('/safe' in argv):
        print('Google Patrol...')

        CSNPatrolWrite(patrol)

    if '/new' in argv:
        print('Google Attractions...')
        #CSNAttractions(faction_systems)    ## TODO Check - It looked like it was causing a hang but could just be too long
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
    Misson_Gen(sys.argv[1:] + ["/!expansion", "/!new"])