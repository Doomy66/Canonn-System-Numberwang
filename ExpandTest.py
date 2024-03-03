import CSNSettings
from classes.BubbleExpansion import BubbleExpansion
from classes.System import System
from classes.ExpansionTarget import ExpansionTarget
from providers.EDSM import GetSystemsFromEDSM
from providers.EliteBGS import EBGSLiveSystem, RefreshFaction


def xPrintTargets(system_name: str, targets: list[ExpansionTarget], length=5):
    """ Debugging Print of Targets"""
    print(f"{system_name}")
    oursysnames = list(
        x.name for x in myBubble.faction_presence(myFactionName))
    for t in targets[:length]:
        print(
            f"  {'*' if t.systemname in oursysnames else ' '}{t.systemname} : {t} [{t.score:.3f}]")


if __name__ == '__main__':
    """ 
        Tests and Examples of use of Expansion process
        Most of the Expansion Calculations are done automatically as part of the Creation of the BubbleExpansion object
        If LIVE values are required, then update relevant systems with live EBGS data and run Expansion check again.
    """
    myFactionName = CSNSettings.FACTION
    myBubble: BubbleExpansion = BubbleExpansion(
        GetSystemsFromEDSM(myFactionName, 40))  # max(30, 20+20) to allow check for Simple Invasions
    myBubble.systems = sorted(myBubble.systems, key=lambda x: x.name)
    # Update a Factions Systems
    mySystems: list[System] = myBubble.faction_presence(myFactionName)
    RefreshFaction(myBubble, myFactionName)
    myBubble._ExpandAll()

    # System Details
    mySystemName = 'Vorden'
    mySystemName = 'HIP 86568'
    mySystem: System = myBubble.getsystem(mySystemName)
    if targets := mySystem.expansion_targets:
        xPrintTargets(mySystem.name, targets, 9)

    # # List Faction's all likely Expansions
    # targets: list[ExpansionTarget]
    # source_system: System
    # print(f"List {myFactionName}'s all likely Expansions")
    # for source_system in myBubble.systems:
    #     if source_system.controllingFaction == myFactionName and source_system.factions[0].influence > 70:
    #         if targets := source_system.expansion_targets:
    #             xPrintTargets(source_system.name, targets)

    # # Simple is calculated in Post Init
    # print(f"\nSimple is calculated in Post Init unless the .env says otherwise")
    # if mySystem.expansion_targets:
    #     xPrintTargets('Default  '+mySystemName, mySystem.expansion_targets)

    # # Need to recalculate to check for Extended
    # print(f"Need to recalculate to check for Extended")
    # if targets := myBubble.ExpandFromSystem(mySystem, extended=True):
    #     xPrintTargets('Extended ' + mySystemName, targets, length=5)

    # # Look for Simple Invasions of Player Factions into our Systems
    # print(
    #     f"\nLook for Simple Invasions of Player Factions into {myFactionName} Systems")
    # for source_system in myBubble.systems:
    #     if source_system.factions and source_system.factions[0].influence > 60 and source_system.factions[0].isPlayer:
    #         if targets := source_system.expansion_targets:
    #             for t in targets[:3]:  # Only look at the top 3 targets
    #                 if myBubble.getsystem(t.systemname).isfactionpresent(myFactionName):
    #                     xPrintTargets(
    #                         f"{source_system.name} ({source_system.factions[0].influence:.2f}) : {source_system.controllingFaction}", targets, length=3)
    #                     break

    print(f"EBGS Requests : {CSNSettings.GLOBALS['nRequests']}")
