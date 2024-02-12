from dataclasses import dataclass
from DataClassesExpansion import BubbleExpansion
from DataClassesBase import Presence, System, ExpansionTarget, State
from enum import Enum
from EDSM import GetSystemsFromEDSM
from EliteBGS import RefreshFaction
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
IGNORE_GAP = 30  # Ignore any gap over...


def xPrintTargets(system_name: str, targets: list[ExpansionTarget], length=5):
    """ Debugging Print of Targets"""
    print(f"{system_name}")
    for t in targets[:length]:
        print(f"  {t.systemname} : {t} [{t.score:.3f}]")


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


def Main(live=True):
    myFactionName = CSNSettings.myfaction
    bubble = BubbleExpansion(
        GetSystemsFromEDSM(myFactionName, 40))

    # Process Each System
    systems = bubble.faction_presence(myFactionName)
    system: System
    faction: Presence

    if live:
        RefreshFaction(bubble, myFactionName)
        # TODO Recalc Expansions

    # Load Overrides into Messages from Google
    messages: list[Message] = list(Message(systemname=x[0], priority=x[1], text=x[2],
                                           emoji=x[3], override=x[4]) for x in CSNOverRideRead()[1:])
    # Replace f strings in Overrirdes
    for message in (_ for _ in messages if ('{' in _.text)):
        system = bubble.getsystem(message.systemname)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == myFactionName), None)
        gap: float = system.influence - \
            (system.factions[1].influence if len(system.factions) > 1 else 0)
        gapfromtop: float = system.influence - myPresence.influence if myPresence else 0
        expandto: str = str(
            system.nextexpansion) if system.nextexpansion else 'None Detected'

        for faction in system.factions:
            if faction.name != myFactionName and faction.name in message.text:
                message = ExpandMessage(message,
                                        expandto=expandto, inf=faction.inf, gap=abs(faction.influence-myPresence.influence), happy='<?>', gapfromtop=system.influence-faction.influence)
        else:
            message = ExpandMessage(
                message, expandto=expandto, inf=system.influence, gap=gap, happy='<?>', gapfromtop=gapfromtop)

    for system in systems:
        # Precalculations
        gap: float = system.influence - \
            (system.factions[1].influence if len(system.factions) > 1 else 0)
        myPresence: Presence = next(
            (_ for _ in system.factions if _.name == myFactionName), None)
        gapfromtop: float = system.influence - myPresence.influence if myPresence else 0

        # Standard System Message

        # TODO Additional Flavour Messages (Some may go AFTER Override Check)
        # Aged
        # Tritium Refinary Low Price Active/Pending
        # GOLDRUSH
        # DCOH Threat
        # Retreats
        # Invasions

        if any(_.override == 'Override' and _.systemname == system.name for _ in messages):
            continue  # No Internal Message

        # Conflict for myFaction
        conflictstate: State = next(
            (_ for _ in myPresence.states if _.isConflict), None)
        if conflictstate:
            # Remove Peacetime Overrides
            for message in messages[:]:
                if (message.systemname == system.name) and (message.override == 'Peacetime'):
                    messages.remove(message)

            # messages = list(
            #     filter(lambda message: ((message.systemname == system.name) and (message.override != 'Peacetime')), messages))
            myMessage: Message = Message(
                system.name, 2, f"{str(conflictstate)}")
            messages.append(myMessage)
            if conflictstate.phase:
                continue
        elif any(_.systemname == system.name and _.override == 'Peacetime' for _ in messages):
            # Peacetime Override so no further message
            continue

        # Not Yet In Control
        if system.controllingFaction != myFactionName:
            myMessage: Message = Message(
                system.name, 3, f"Urgent: {myFactionName} Missons etc to gain system control (gap {gapfromtop:4.3}%)", dIcons['push'])
            messages.append(myMessage)
            continue

        # Gap Warning
        if gap <= SAFE_GAP:
            myMessage: Message = Message(
                system.name, 4, f"Required: {myFactionName} Missons etc ({system.factions[1].name} is threatening, gap is only {gap:4.3}%)", dIcons['infgap'])
            messages.append(myMessage)
            continue

        # End of system loop

    # Add 3 Lowest Gaps for Homework
    best = list((x for x in systems if (x.controllingFaction ==
                myFactionName and (len(x.factions) > 1) and (
                    SAFE_GAP <= (x.influence - x.factions[1].influence) <= IGNORE_GAP))))
    best = sorted(best, key=lambda x: (x.influence - x.factions[1].influence))
    for best3 in best[:3]:
        message = Message(
            best3.name, 5, f"Suggestion: {myFactionName} Missions etc (gap to {best3.factions[1].name} is {best3.influence-best3.factions[1].influence:.2f}%)", dIcons['mininf'])
        messages.append(message)

    # TODO Process Overrides for Non-Faction Systems
    # TODO Fleet Carriers

    messages.sort(key=lambda x: x.priority)

    # Output
    # TODO Discord Full
    # TODO Discourd Update
    # TODO Patrol
    for message in messages:
        print(f"{message.systemname:<30} - {message.priority:<2} - {message.text}")

    # Save Messages for Update Comparison
    with open(f'data\\{myFactionName}CSNMessages.pickle', 'wb') as io:
        pickle.dump(messages, io)

    print(f"EBGS Requests : {CSNSettings.myGlobals['nRequests']}")


if __name__ == '__main__':
    """ 
        Tests and Examples of use
        Most of the Expansion Calculations are done automatically as part of the Creation of the BubbleExpansion object
        If LIVE values are required, then update relevant systems with live EBGS data and run Expansion check again.
    """

    # # New Analysis
    Main(live=True)

    print(f"EBGS Requests : {CSNSettings.myGlobals['nRequests']}")
