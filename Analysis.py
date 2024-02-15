from dataclasses import dataclass
from datetime import datetime, timedelta
from classes.BubbleExpansion import BubbleExpansion
from classes.Presense import Presence
from classes.System import System
from classes.State import State, Phase
from providers.EDSM import GetSystemsFromEDSM
from providers.EliteBGS import RefreshFaction
from api import dcohsummary
import CSNSettings

from Overrides import CSNOverRideRead
import pickle

dIcons = {"war": ':gun: ',  # 12/09/22 Stnadard Icons due to dead Discord
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
          "notfresh": ':arrows_counterclockwise: ',
          "thargoid1": '<:Thargoid:1020771117939568660>'}

SAFE_GAP = 15  # Urgent message if below...
IGNORE_GAP = 29  # Ignore any gap over...


@dataclass
class Message:
    """ CSN Message """
    systemname: str
    priority: int
    text: str
    emoji: str = ''
    override: str = ''


def WriteDiscord(myFactionName: str, Full: int, messages: list[Message]):
    # Load Old Messages
    oldmessages: list[Message] = []
    try:
        # CSNLog.info('Load Saved Messages')
        with open(f'data\\{myFactionName}CSNMessages.pickle', 'rb') as io:
            oldmessages = pickle.load(io)
    except:
        pass

    # TODO Compare with Old Messages
    pass


def ExpandMessage(message: Message, expandto: str, inf: float, gap: float, happy: str, gapfromtop: float) -> Message:
    """ String Expansion of variables in a message """
    message.text = message.text.format(
        expandto=expandto, inf=inf, gap=gap, happy=happy, gapfromtop=gapfromtop)
    return message


def GetOverrides(bubble: BubbleExpansion, myFactionName: str) -> list[Message]:
    """ Gets all Manual Missions or Overrides (from Google) and expands any embeded variables """
    # Load Overrides into Messages from Google
    messages: list[Message] = list(Message(systemname=_[0], priority=_[1], text=_[2],
                                           emoji=dIcons[_[3]], override=_[4]) for _ in CSNOverRideRead()[1:])
    # Replace f strings in Overrirdes
    for myMessage in (_ for _ in messages if ('{' in _.text)):
        system = bubble.getsystem(myMessage.systemname)
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


def Main(uselivedata=True):
    myFactionName = CSNSettings.myfaction
    bubble = BubbleExpansion(
        GetSystemsFromEDSM(myFactionName, 40))

    # Process Each System
    systems = bubble.faction_presence(myFactionName)
    system: System
    faction: Presence

    dhoc = dcohsummary()

    if uselivedata:
        RefreshFaction(bubble, myFactionName)
        bubble._ExpandAll()

    # Load Overrides
    messages: list[Message] = GetOverrides(bubble, myFactionName)

    # Process all faction systems
    for system in systems:
        # Precalculationa
        gap: float = round(system.influence -
                           (system.factions[1].influence if len(system.factions) > 1 else 0), 1)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == myFactionName), None)
        gapfromtop: float = round(
            system.influence - myPresence.influence if myPresence else 0, 1)

        # Standard System Message
        # Stale Data
        age: timedelta = (datetime.now()-system.updated).days
        if age > system.influence/10:
            myMessage = Message(
                system.name, 11, f"(Scan System to update data {int(age)} days old')", dIcons['data'])
            messages.append(myMessage)

        # TODO Retreats
        # TODO Invasions

        # DCOH Threat
        dcohthreat = next(
            (x for x in dhoc if x['sys_name'] == system.name), None)
        if dcohthreat and dcohthreat["progress"] < 100:
            myMessage = Message(
                system.name, 9, f'Thargoid {dcohthreat["threat"]} : Progress {int(dcohthreat["progress"])}%', dIcons['thargoid1'])
            messages.append(myMessage)

        # TODO Tritium Refinary Low Price Active/Pending
        # TODO GOLDRUSH

        if any(_.override == 'Override' and _.systemname == system.name for _ in messages):
            continue  # No Internal Message

        # Conflict for myFaction
        conflictstate: State = next(
            (_ for _ in myPresence.states if _.isConflict), None)
        if conflictstate:
            # Remove Peacetime Overrides
            for myMessage in messages[:]:
                if (myMessage.systemname == system.name) and (myMessage.override == 'Peacetime'):
                    messages.remove(myMessage)
            myMessage: Message = Message(
                system.name, 2, f"{str(conflictstate)}", dIcons[conflictstate.state.replace(' ', '').lower()])

            if conflictstate.phase == Phase.RECOVERING:
                myMessage.priority = 21
                myMessage.emoji = dIcons['info']
                messages.append(myMessage)
            else:
                messages.append(myMessage)
                continue
        elif any(_.systemname == system.name and _.override == 'Peacetime' for _ in messages):
            # Peacetime Override so no further message
            continue

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

    # Add 3 Lowest Gaps for Homework
    best = list((x for x in systems if (x.controllingFaction ==
                myFactionName and (len(x.factions) > 1) and (
                    SAFE_GAP <= (x.influence - x.factions[1].influence) <= IGNORE_GAP))))
    best = sorted(best, key=lambda x: (x.influence - x.factions[1].influence))
    for best3 in best[:3]:
        myMessage = Message(
            best3.name, 5, f"Suggestion: {myFactionName} Missions etc : gap to {best3.factions[1].name} is {best3.influence-best3.factions[1].influence:.1f}%", dIcons['mininf'])
        messages.append(myMessage)

    # TODO Fleet Carriers

    messages.sort(key=lambda x: x.priority)

    # Output
    # TODO Discord Full
    # TODO Discourd Update
    # TODO Patrol
    for myMessage in messages:
        if myMessage.priority <= 10 or myMessage.priority > 20:
            print(
                f"{myMessage.systemname:<30} - {myMessage.priority:<2} - {myMessage.text:<80} {myMessage.emoji}")

    # Save Messages for Update Comparison
    with open(f'data\\{myFactionName}CSNMessages.pickle', 'wb') as io:
        pickle.dump(messages, io)

    print(f"EBGS Requests : {CSNSettings.myGlobals['nRequests']}")


if __name__ == '__main__':
    """ 
        Tests and Examples of use
    """

    # # New Analysis
    Main(uselivedata=True)

    print(f"EBGS Requests : {CSNSettings.myGlobals['nRequests']}")
