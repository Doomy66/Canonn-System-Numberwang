# Generates Messages/Missions for the faction
from datetime import datetime, timedelta
import platform
import pickle

import CSNSettings
from classes.BubbleExpansion import BubbleExpansion
from classes.Presense import Presence
from classes.System import System
from classes.State import State, Phase
from classes.Message import Message, Overide
from classes.ExpansionTarget import ExpansionTarget
from providers.EDSM import GetSystemsFromEDSM
from providers.EliteBGS import RefreshFaction
from providers.DiscordLink import WriteDiscord
from providers.Canonn import getfleetcarrier
from providers.DCOH import dcohsummary
from providers.GoogleSheets import CSNOverRideRead, CSNFleetCarrierRead, CSNPatrolWrite
from providers.ShortTermMemory import STM, SaveSTM


myBubble: BubbleExpansion = None  # type: ignore

SAFE_GAP = 15  # Urgent message if below...
IGNORE_GAP = 29  # Ignore any gap over...


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
                                           emoji=CSNSettings.ICONS[_[3]], override=Overide(_[4][:1])) for _ in CSNOverRideRead()[1:])
    # Replace f strings in Overrirdes
    for myMessage in (_ for _ in messages if ('{' in _.text)):
        system: System = myBubble.getsystem(myMessage.systemname)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == CSNSettings.FACTION), None)  # type: ignore
        gap: float = round(
            system.influence - (system.factions[1].influence if len(system.factions) > 1 else 0), 2)
        gapfromtop: float = round(
            system.influence - myPresence.influence if myPresence else 0, 2)
        expandto: str = str(
            system.nextexpansion) if system.nextexpansion else 'None Detected'

        for faction in system.factions:
            if faction.name != CSNSettings.FACTION and faction.name in myMessage.text:
                myMessage = ExpandMessage(myMessage,
                                          expandto=expandto, inf=faction.influence, gap=abs(faction.influence-myPresence.influence), happy='<?>', gapfromtop=system.influence-faction.influence)
        else:
            myMessage = ExpandMessage(
                myMessage, expandto=expandto, inf=system.influence, gap=gap, happy='<?>', gapfromtop=gapfromtop)
    return messages


def StaleDataMessages(mySystems: list[System]) -> list[Message]:
    """ Checks Last Updated DateTime and Prompts Mission if Stales"""
    messages: list[Message] = []
    age: timedelta
    for system in mySystems:
        # Stale Data
        if (age := (datetime.now()-system.updated).days) > system.influence/10:
            myMessage = Message(
                system.name, 11, f"Scan System to update data {int(age)} days old", CSNSettings.ICONS['data'])
            messages.append(myMessage)
    return messages


def DCOHThargoidMessages(mySystems: list[System]) -> list[Message]:
    """ Gets Thargoid Threat Messages"""
    dhoc = dcohsummary()
    messages: list[Message] = []
    for system in mySystems:
        dcohthreat = next(
            (x for x in dhoc if x['sys_name'] == system.name), None)
        if dcohthreat and dcohthreat["progress"] < 100:
            myMessage = Message(
                system.name, 9, f'Thargoid {dcohthreat["threat"]} : Progress {int(dcohthreat["progress"])}%', CSNSettings.ICONS['thargoid1'])
            messages.append(myMessage)
    return messages


def RetreatMessages(mySystems: list[System], myfaction: str = CSNSettings.FACTION) -> list[Message]:
    """ Prevent Retreat of Full Systems to prevent normal Expansion """
    messages: list[Message] = []
    summary: list[str] = []
    for system in mySystems:
        faction: Presence
        # Mine, Currently Full, and there is another faction in simple range - Dont consider PF or Ignored, thats bad strategy
        if system.controllingFaction == myfaction and system.factions and len(system.factions) > 6:
            if next((_ for _ in myBubble.cube_systems(system, myBubble.SIMPLERANGE) if _.controllingFaction != myfaction), None):
                for faction in system.factions:
                    if faction.states and next((_ for _ in faction.states if _.state.lower() == 'retreat' and _.phase != Phase.RECOVERING), None):
                        myMessage = Message(
                            system.name, 7, f"Support {faction.name} to be above 5% to prevent Retreat ({round(faction.influence,1)}%)", CSNSettings.ICONS['override'])
                        summary.append(system.name)
                        messages.append(myMessage)
    if summary:
        myMessage = Message('Retreats Detected in', 25,
                            ','.join(summary), CSNSettings.ICONS['data'])
        messages.append(myMessage)

    return messages


def InvasionMessages(systems: list[System], mySystems: list[System], max_cycles: int = 5, paranoia_level: float = CSNSettings.PARANOIA_LEVEL, myfaction: str = CSNSettings.FACTION, all_factions=False) -> list[Message]:
    """ Turns Invasion Data calulated earlier into relevent Messages """
    """ Only bothered with Non-Ignored PF unless all_factions is TRUE"""
    messages: list[Message] = []
    system: System
    target: ExpansionTarget
    for system in systems:
        if system not in mySystems and system.nextexpansion and system.influence > paranoia_level and \
                (all_factions or (system.controllingdetails.isPlayer and not CSNSettings.isIgnored(system.controllingFaction))):
            for i, target in enumerate(system.expansion_targets[:max_cycles]):
                if target.faction.name == myfaction:
                    messages.append(Message(system.name,
                                    10, f"{system.controllingFaction} Possible {target.description} to {target.systemname} ({system.influence:.2f}%) Priority {i+1}", CSNSettings.ICONS['data']))
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
                    currentsystem, 9, f'{carrier["name"]} ({carrier["role"]})', CSNSettings.ICONS['FC'])
                messages.append(message)
            except:
                pass
            if not currentsystem:
                print(f'!!! Fleet Carrier {carrier["id"]} Failed !!!')
    return messages


def FillInMessages(mySystems: list[System], count: int = 3) -> list[Message]:
    """ 3 Systems with the lowest non urgent gaps """
    messages: list[Message] = []
    # Yeah, showing off pythonic, not exactly readable
    best = list((_ for _ in mySystems if (_.controllingFaction ==
                CSNSettings.FACTION and (len(_.factions) > 1) and (
                    SAFE_GAP <= (_.influence - _.factions[1].influence) <= IGNORE_GAP))))
    best = sorted(best, key=lambda x: (x.influence - x.factions[1].influence))
    for best3 in best[:count]:
        myMessage = Message(
            best3.name, 5, f"Suggestion: {CSNSettings.FACTION} Missions etc (gap to {best3.factions[1].name} is {best3.influence-best3.factions[1].influence:.1f}%)", CSNSettings.ICONS['mininf'])
        messages.append(myMessage)
    return messages


def LightHouseExpansion() -> list[Message]:
    """ Check Lighthouse System and create live Expansion Message """
    global myBubble
    messages: list[Message] = []
    state: State = None
    if CSNSettings.LIGHTHOUSE and (system := myBubble.getsystem(CSNSettings.LIGHTHOUSE)):
        state = next(
            (x for x in system.controllingdetails.states if x.state.lower() == 'expansion'), State('None'))

        if state.state.lower() != STM.get('exp_state'):
            STM['exp_state'] = state.state.lower()
            STM['exp_timestamp'] = system.updated.timestamp()
            SaveSTM()

        if state.state.lower() == 'expansion':
            if state.phase == Phase.PENDING or state.phase == Phase.ACTIVE:
                recorded_date = datetime.fromtimestamp(STM['exp_timestamp'])
                planned_date = recorded_date + timedelta(days=10)
                # Detected early in the morning, so probably happened in yesterdays tick (until tick officially moves!)
                if (planned_date.time() <= datetime.strptime('08:00', '%H:%M').time()):
                    planned_date = planned_date + timedelta(days=-1)
                messages.append(
                    Message('', 25, f"Expansion Expected {planned_date.strftime('%a %d %b')}", CSNSettings.ICONS['info']))
            elif state.phase == Phase.RECOVERING:
                messages.append(
                    Message('', 25, 'Expansion Complete', CSNSettings.ICONS['data']))

    return messages


def GetSystemsWithLive(faction: str = CSNSettings.FACTION, range=40) -> list[System]:
    answer: list[System] = []
    answer = GetSystemsFromEDSM(faction, range)
    answer = RefreshFaction(answer, faction)
    return answer


def GenerateMissions(uselivedata=True, DiscordFullReport=True, DiscordUpdateReport=False):
    """ Generates all Messages for the Faction and outputs to Discord/Google"""
    global myBubble
    print(f"CSN Analysis on {platform.node()}")
    if uselivedata:
        myBubble = BubbleExpansion(GetSystemsWithLive())
    else:
        myBubble = BubbleExpansion(GetSystemsFromEDSM())

    mySystems = myBubble.faction_presence(CSNSettings.FACTION)

    messages: list[Message] = []
    # Manually Specified Messages
    messages.extend(OverrideMessages())
    # General Additional Messages
    messages.extend(StaleDataMessages(mySystems))
    messages.extend(DCOHThargoidMessages(mySystems))
    messages.extend(RetreatMessages(mySystems))
    messages.extend(InvasionMessages(myBubble.systems, mySystems))
    messages.extend(FleetCarrierMessages())
    messages.extend(FillInMessages(mySystems, count=3))
    messages.extend(LightHouseExpansion())

    # Probably wont implement. Low value.
    # TODO Tritium Refinary Low Price Active/Pending
    # TODO GOLDRUSH
    # messages.extend(MarketMessages())

    # System Status Message
    CSNSettings.CSNLog.info('System Messages')
    system: System
    for system in mySystems:
        # Precalculations
        gap: float = round(system.influence -
                           (system.factions[1].influence if len(system.factions) > 1 else 0), 1)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == CSNSettings.FACTION), None)
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
                system.name, 2, f"{str(conflictstate)}", CSNSettings.ICONS[conflictstate.state.replace(' ', '').lower()])

            if conflictstate.phase == Phase.RECOVERING:  # Conflict is over, so turn into information
                myMessage.priority = 21
                myMessage.emoji = CSNSettings.ICONS['info']
                messages.append(myMessage)
            else:
                messages.append(myMessage)
                # TODO ? Could delete Peacetime Message, but it is not normally required as Peacetimes are normally Discord silent
                continue  # No More Internal Messages

        if any(_.systemname == system.name and _.override == Overide.PEACETIME for _ in messages):
            # Peacetime Override so no further message
            continue  # No More Internal Messages

        # Not Yet In Control
        if system.controllingFaction != CSNSettings.FACTION:
            myMessage: Message = Message(
                system.name, 3, f"Urgent: {CSNSettings.FACTION} Missons etc to gain system control (gap {gapfromtop:.1f}%)", CSNSettings.ICONS['push'])
            messages.append(myMessage)
            continue

        # Gap Warning
        if gap <= SAFE_GAP:
            myMessage: Message = Message(
                system.name, 4, f"Required: {CSNSettings.FACTION} Missons etc : {system.factions[1].name} is threatening, gap is only {gap:.1f}%", CSNSettings.ICONS['infgap'])
            messages.append(myMessage)
            continue  # Does not need the continue but might add another condition in the future

    # End of system loop
    messages.sort(key=lambda x: x.priority)

    # Output
    # Discord Full
    if DiscordFullReport:
        WriteDiscord(Full=True, messages=messages[:])
    # Discourd Update
    if DiscordUpdateReport:
        WriteDiscord(Full=False, messages=messages[:])

    # Write Patrol to Google Sheet
    WritePatrol(messages[:])

    # Save Messages for update comparison
    with open(f'data\\{CSNSettings.FACTION}CSNMessages.pickle', 'wb') as io:
        pickle.dump(messages, io)

    print(f"Complete : EBGS Requests {CSNSettings.GLOBALS['nRequests']}")
    CSNSettings.CSNLog.info(
        f"Complete : EBGS Requests {CSNSettings.GLOBALS['nRequests']}\n")


if __name__ == '__main__':
    """ 
        Tests and Examples of use
    """
    # Default/Manual Usage
    full = False
    GenerateMissions(uselivedata=True,
                     DiscordUpdateReport=not full, DiscordFullReport=full)

    # TODO Make CSN Functions generic to be used as a toolkit in ExpandTest
    # TODO Get rid of Bubble, just use Bubble Expansion - Beware may start circular references.
