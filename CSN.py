from datetime import datetime, timedelta
from classes.BubbleExpansion import BubbleExpansion
from classes.Presense import Presence
from classes.System import System
from classes.State import State, Phase
from classes.Message import Message, Overide
from classes.ExpansionTarget import ExpansionTarget
from providers.EDSM import GetSystemsFromEDSM
from providers.EliteBGS import RefreshFaction
from api import dcohsummary, getfleetcarrier
from CSNSettings import dIcons
import CSNSettings
import platform

from Overrides import CSNOverRideRead, CSNFleetCarrierRead, CSNPatrolWrite
import pickle
from discord import SyncWebhook

myFactionName: str = CSNSettings.myfaction
myBubble: BubbleExpansion = None
mySystems: list[System] = []


SAFE_GAP = 15  # Urgent message if below...
IGNORE_GAP = 29  # Ignore any gap over...


def WriteDiscord(myFactionName: str, Full: bool, messages: list[Message]) -> None:
    messages = list(filter(lambda _: _.isDiscord, messages))
    # Load Old Messages
    oldmessages: list[Message] = []

    if not Full:
        try:
            # CSNLog.info('Load Saved Messages')
            with open(f'data\\{myFactionName}CSNMessages.pickle', 'rb') as io:
                oldmessages = pickle.load(io)
        except:
            pass

        for message in oldmessages:
            if message in messages:
                # Remove Unchanged Messages
                messages.remove(message)
            elif (message.systemname not in list(x.systemname for x in messages)) and message.isDiscord:
                # Add Old Message as Complete
                message.complete = True
                messages.append(message)

    print(f"Discord Webhook : {'Full' if Full else 'Update'}...")
    if CSNSettings.wh_id and messages:
        webhook_text: str = ''
        webhook_extra: str = ''
        webhook = SyncWebhook.partial(CSNSettings.wh_id, CSNSettings.wh_token)
        message: Message
        for message in messages:
            thistext: str = f"{message.emoji}{message.systemname} : {'~~' if message.complete else ''}{message.text}{'~~ : Mission Complete' if message.complete else ''}\n"
            # Max len for a single hook is 2000 chars. A message can be approx 100 and there is the additional header text.
            if len(webhook_text) < 1850:
                webhook_text += thistext
            else:
                webhook_extra += thistext

        if webhook_text != '':
            print(webhook_text)
            webhook.send(
                f"{'**Full Report**' if Full else 'Latest News'} {dIcons['csnicon']} \n{webhook_text}")

        if webhook_extra != '':
            print(webhook_extra)
            webhook.send(
                f"...continued {dIcons['csnicon']} \n{webhook_extra}")
    else:
        print("...Nothing to Report to Discord")


def WritePatrol(messages: list[Message]):
    """ Convert Messages into Format Compatible with Google Sheet that is sent to EDMC\n"""
    """ System, X, Y, Z, TI=0, Faction=Canonn, Message, Icon"""
    patrol = []
    for message in messages:
        if message.isPatrol:
            system = myBubble.getsystem(message.systemname)
            patrol.append((message.systemname, system.x if system else 0, system.y if system else 0,
                          system.z if system else 0, 0, 'Canonn', message.text, message.emoji))
    print('Google Patrol...')
    CSNPatrolWrite(patrol)


def ExpandMessage(message: Message, expandto: str, inf: float, gap: float, happy: str, gapfromtop: float) -> Message:
    """ String Expansion of variables in a message """
    message.text = message.text.format(
        expandto=expandto, inf=inf, gap=gap, happy=happy, gapfromtop=gapfromtop)
    return message


def OverrideMessages() -> list[Message]:
    """ Gets all Manual Missions or Overrides (from Google) and expands any embeded variables """
    faction: Presence
    myPresence: Presence

    # Load Overrides into Messages from Google
    messages: list[Message] = list(Message(systemname=_[0], priority=_[1], text=_[2],
                                           emoji=dIcons[_[3]], override=Overide(_[4][:1])) for _ in CSNOverRideRead()[1:])
    # Replace f strings in Overrirdes
    for myMessage in (_ for _ in messages if ('{' in _.text)):
        system = myBubble.getsystem(myMessage.systemname)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == myFactionName), None)
        gap: float = round(
            system.influence - (system.factions[1].influence if len(system.factions) > 1 else 0), 2)
        gapfromtop: float = round(
            system.influence - myPresence.influence if myPresence else 0, 2)
        expandto: str = str(
            system.nextexpansion) if system.nextexpansion else 'None Detected'

        for faction in system.factions:
            if faction.name != myFactionName and faction.name in myMessage.text:
                myMessage = ExpandMessage(myMessage,
                                          expandto=expandto, inf=faction.inf, gap=abs(faction.influence-myPresence.influence), happy='<?>', gapfromtop=system.influence-faction.influence)
        else:
            myMessage = ExpandMessage(
                myMessage, expandto=expandto, inf=system.influence, gap=gap, happy='<?>', gapfromtop=gapfromtop)
    return messages


def StaleDataMessages() -> list[Message]:
    """ Checks Last Updated DateTime and Prompts Mission if Stales"""
    messages: list[Message] = []
    age: timedelta
    for system in mySystems:
        # Stale Data
        if (age := (datetime.now()-system.updated).days) > system.influence/10:
            myMessage = Message(
                system.name, 11, f"Scan System to update data {int(age)} days old", dIcons['data'])
            messages.append(myMessage)
    return messages


def DCOHThargoidMessages() -> list[Message]:
    """ Gets Thargoid Threat Messages"""
    dhoc = dcohsummary()
    messages: list[Message] = []
    for system in mySystems:
        dcohthreat = next(
            (x for x in dhoc if x['sys_name'] == system.name), None)
        if dcohthreat and dcohthreat["progress"] < 100:
            myMessage = Message(
                system.name, 9, f'Thargoid {dcohthreat["threat"]} : Progress {int(dcohthreat["progress"])}%', dIcons['thargoid1'])
            messages.append(myMessage)
    return messages


def RetreatMessages() -> list[Message]:
    """ Prevent Retreat of Full Systems to prevent normal Expansion """
    messages: list[Message] = []
    summary: list[str] = []
    for system in mySystems:
        faction: Presence
        # Mine, Currently Full, and there is another faction in simple range - Dont consider PF or Ignored, thats bad strategy
        if system.controllingFaction == myFactionName and system.factions and len(system.factions) > 6:
            if next((_ for _ in myBubble.cube_systems(system, myBubble.SIMPLERANGE) if _.controllingFaction != myFactionName), None):
                for faction in system.factions:
                    if faction.states and next((_ for _ in faction.states if _.state.lower() == 'retreat' and _.phase != Phase.RECOVERING), None):
                        myMessage = Message(
                            system.name, 7, f"Support {faction.name} to be above 5% to prevent Retreat ({round(faction.influence,1)}%)", dIcons['override'])
                        summary.append(system.name)
                        messages.append(myMessage)
    if summary:
        myMessage = Message('Retreats Detected in', 25,
                            ','.join(summary), dIcons['data'])
        messages.append(myMessage)

    return messages


def MarketMessages() -> list[Message]:
    pass
    # """ Interesting Market Messages """
    # """ TODO Tritium needs to know if Tritium is sold """
    # """ TODO Goldrush uses economy details of station 'extraction'ish """
    # messages: list[Message] = []

    # for system in mySystems:
    #     state: State
    #     sellsTritium: bool = False
    #     goldRushEconomy: bool = 'Extraction' in system.alleconomys ## A Faction's Station is Extraction, and a Faction's State is ISF
    #     for state in system.factions[0].states:
    #         if sellsTritium and state.state.lower() in {'drought', 'blight', 'terrorism'} and state.phase is not Phase.RECOVERING:
    #             myMessage = Message(
    #                 system.name, 24, f"Tritium Opportunity{' Pending' if state.phase==Phase.PENDING else ''}")
    #             messages.append(myMessage)
    #         if goldRushEconomy and state.state.lower() in {'infrastructurefailure'} and state.phase is not Phase.RECOVERING:
    #             myMessage = Message(
    #                 system.name, 24, f"Gold Rush {' Pending' if state.phase==Phase.PENDING else ''}", dIcons['data'])
    #             messages.append(myMessage)

    # return messages


def InvasionMessages(cycles: int = 5) -> list[Message]:
    """ Turns Invasion Data calulated earlier into relevent Messages """
    """ Only bothered with Non-Ignored PF """
    messages: list[Message] = []
    system: System
    target: ExpansionTarget
    for system in myBubble.systems:
        if system not in mySystems and system.nextexpansion and system.influence > CSNSettings.invasionparanoialevel and system.controllingdetails.isPlayer and not CSNSettings.isIgnored(system.controllingFaction):
            for i, target in enumerate(system.expansion_targets[:cycles]):
                if target.faction.name == myFactionName:
                    messages.append(Message(system.name,
                                    10, f"{system.controllingFaction} Possible {target.description} to {target.systemname} ({system.influence:.2f}%) Priority {i+1}", dIcons['data']))
                    break
    return messages


def FleetCarrierMessages() -> list[Message]:
    """ Location of Noted Fleet Carriers """
    messages: list[Message] = []

    carriers = CSNFleetCarrierRead()
    for carrier in carriers:
        currentsystem = None
        if carrier['id'][0] != '!':
            try:
                thiscarrier = getfleetcarrier(carrier['id'])
                currentsystem = thiscarrier['current_system']
                message = Message(
                    currentsystem, 9, f'{carrier["name"]} ({carrier["role"]})', dIcons['FC'])
                messages.append(message)
            except:
                pass
            if not currentsystem:
                print(f'!!! Fleet Carrier {carrier["id"]} Failed !!!')
    return messages


def FillInMessages(count: int = 3) -> list[Message]:
    """ 3 Systems with the lowest non urgent gaps """
    messages: list[Message] = []
    best = list((_ for _ in mySystems if (_.controllingFaction ==
                myFactionName and (len(_.factions) > 1) and (
                    SAFE_GAP <= (_.influence - _.factions[1].influence) <= IGNORE_GAP))))
    best = sorted(best, key=lambda x: (x.influence - x.factions[1].influence))
    for best3 in best[:count]:
        myMessage = Message(
            best3.name, 5, f"Suggestion: {myFactionName} Missions etc (gap to {best3.factions[1].name} is {best3.influence-best3.factions[1].influence:.1f}%)", dIcons['mininf'])
        messages.append(myMessage)
    return messages


def GenerateMissions(uselivedata=True, DiscordFullReport=True, DiscordUpdateReport=False):
    """ Generates all Messages for the Faction and outputs to Discord/Google"""
    global myBubble, mySystems
    print(f"CSN Analysis on {platform.node()}")
    myBubble = BubbleExpansion(
        GetSystemsFromEDSM(myFactionName, 40))
    mySystems = myBubble.faction_presence(myFactionName)

    if uselivedata:
        RefreshFaction(myBubble, myFactionName)
        myBubble._ExpandAll()

    messages: list[Message] = []
    # Manually Specified Messages
    messages.extend(OverrideMessages())
    # General Messages
    messages.extend(StaleDataMessages())
    messages.extend(DCOHThargoidMessages())
    messages.extend(RetreatMessages())
    messages.extend(InvasionMessages())
    messages.extend(FleetCarrierMessages())
    messages.extend(FillInMessages(count=3))

    # Probably wont implement. Low value.
    # TODO Tritium Refinary Low Price Active/Pending
    # TODO GOLDRUSH
    # messages.extend(MarketMessages())

    # Process all faction systems
    system: System
    for system in mySystems:
        # Precalculations
        gap: float = round(system.influence -
                           (system.factions[1].influence if len(system.factions) > 1 else 0), 1)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == myFactionName), None)
        gapfromtop: float = round(
            system.influence - myPresence.influence if myPresence else 0, 1)

        # Manual Override - No Internal Message for this System
        if any(_.override == Overide.OVERRIDE and _.systemname == system.name for _ in messages):
            continue

        # Conflict for myFaction
        conflictstate: State
        if (conflictstate := next(
                (_ for _ in myPresence.states if _.isConflict), None)):
            myMessage: Message = Message(
                system.name, 2, f"{str(conflictstate)}", dIcons[conflictstate.state.replace(' ', '').lower()])

            if conflictstate.phase == Phase.RECOVERING:
                myMessage.priority = 21
                myMessage.emoji = dIcons['info']
                messages.append(myMessage)
            else:
                messages.append(myMessage)
                # TODO ? Delete Peacetime Message ? Not normally required as Peacetimes are normally silent
                continue  # No More Internal Messages

        if any(_.systemname == system.name and _.override == Overide.PEACETIME for _ in messages):
            # Peacetime Override so no further message
            continue  # No More Internal Messages

        # Not Yet In Control
        if system.controllingFaction != myFactionName:
            myMessage: Message = Message(
                system.name, 3, f"Urgent: {myFactionName} Missons etc to gain system control (gap {gapfromtop:.1f}%)", dIcons['push'])
            messages.append(myMessage)
            continue

        # Gap Warning
        if gap <= SAFE_GAP:
            myMessage: Message = Message(
                system.name, 4, f"Required: {myFactionName} Missons etc : {system.factions[1].name} is threatening, gap is only {gap:.1f}%", dIcons['infgap'])
            messages.append(myMessage)
            continue

    # End of system loop
    messages.sort(key=lambda x: x.priority)

    # Output
    # Discord Full
    if DiscordFullReport:
        WriteDiscord(myFactionName=myFactionName,
                     Full=True, messages=messages[:])  # Copy of messages on purpose
    # Discourd Update
    if DiscordUpdateReport:
        WriteDiscord(myFactionName=myFactionName,
                     Full=False, messages=messages[:])  # Copy of messages on purpose

    # Write Patrol to Google Sheet
    WritePatrol(messages[:])

    # Save Messages for update comparison
    with open(f'data\\{myFactionName}CSNMessages.pickle', 'wb') as io:
        pickle.dump(messages, io)

    print(f"EBGS Requests : {CSNSettings.myGlobals['nRequests']}")


if __name__ == '__main__':
    """ 
        Tests and Examples of use
    """
    GenerateMissions(uselivedata=True,
                     DiscordUpdateReport=False, DiscordFullReport=True)
