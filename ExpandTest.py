import CSNSettings
from classes.BubbleExpansion import BubbleExpansion
from classes.System import System
from classes.ExpansionTarget import ExpansionTarget
import CSN


def printexpansions(system_name: str, targets: list[ExpansionTarget], length=5):
    """ Debugging Print of Targets"""
    print(f"\nExpansions from {system_name}")
    oursysnames = list(
        x.name for x in myBubble.faction_presence(myFactionName))
    for t in targets[:length]:
        print(
            f"  {'*' if t.systemname in oursysnames else ' '}{t} {myBubble.cube_distance(myBubble.getsystem(system_name),myBubble.getsystem(t.systemname)):.2f}cly {myBubble.distance(myBubble.getsystem(system_name),myBubble.getsystem(t.systemname)):.2f}ly [{t.score:.3f}]")


if __name__ == '__main__':
    """ 
        Examples of use of Expansion process
        Expansion Calculations are done automatically as part of the Creation of the BubbleExpansion object
    """
    # Defaults to settings, but can change it to spy on others. NB, data will not be as quite as good in regards to previous retreats.
    # DONT go fiddling with CSNSettings.FACTION, it will bugger up SystemHistory
    myFactionName = CSNSettings.FACTION

    if True:
        myBubble: BubbleExpansion = BubbleExpansion(
            CSN.GetSystemsFromEDSM(myFactionName, 40))  # Basic Info
    else:
        myBubble: BubbleExpansion = BubbleExpansion(
            CSN.GetSystemsWithLive(myFactionName, 40))  # With Live EBGS Data

    # List of just Factions Systems
    mySystems: list[System] = myBubble.faction_presence(myFactionName)

    # Factions next expansions
    targets: list[ExpansionTarget]
    source_system: System
    print(f"\nList {myFactionName}'s all likely Expansions")
    for source_system in myBubble.systems:
        if source_system.controllingFaction == myFactionName and source_system.factions[0].influence > 75:
            if targets := source_system.expansion_targets:
                printexpansions(source_system.name, targets, length=3)

    # TODO Invasion of Faction

    # System of Interest
    mySystemName = 'Suhte'
    mySystem: System = myBubble.getsystem(mySystemName)

    # Systems Expansion Targets
    if targets := mySystem.expansion_targets:
        printexpansions(mySystem.name, targets, 20)

    # TODO Single System Invasion Threats Regardless of Player Faction Status (change all_factions to FALSE for Player Factions only)
    threats_to_system = CSN.InvasionMessages(myBubble.systems,
                                             [mySystem], max_cycles=3, paranoia_level=60, myfaction=mySystem.controllingFaction, all_factions=True)
    print(f"\nThreats to {mySystemName}")
    for message in threats_to_system:
        print(message)

    print(f"EBGS Requests : {CSNSettings.GLOBALS['nRequests']}")
