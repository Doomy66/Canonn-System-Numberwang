from DataClassesExpansion import BubbleExpansion, ExpansionTarget, System
from EDSM import GetSystemsFromEDSM


def xPrintTargets(system_name: str, targets: list[ExpansionTarget], length=5):
    """ Debugging Print of Targets"""
    print(f"{system_name}")
    for t in targets[:length]:
        print(f"  {t} [{t.score:.3f}]")


if __name__ == '__main__':
    myFactionName = 'Canonn'
    mySystemName = 'Yi Trica'
    myBubble: BubbleExpansion = BubbleExpansion(
        GetSystemsFromEDSM(myFactionName, 40))  # max(30, 20+20) to allow check for Simple Invasions
    myBubble.systems = sorted(myBubble.systems, key=lambda x: x.name)
    mySystem: System = myBubble.getsystem(mySystemName)
    targets: list[ExpansionTarget] = []

    # List Faction's all likely Expansions
    print(f"List {myFactionName}'s all likely Expansions")
    for source_system in myBubble.systems:
        if source_system.controllingFaction == myFactionName and source_system.factions[0].influence > 70:
            targets = source_system.expansion_targets
            if targets:
                xPrintTargets(source_system.name, targets)

    # Simple is calculated in Post Init
    print(f"\nSimple is calculated in Post Init")
    if mySystem.expansion_targets:
        xPrintTargets('Stored   '+mySystemName, mySystem.expansion_targets)

    # Need to recalculate to check for Extended
    print(f"Need to recalculate to check for Extended")
    targets = myBubble.ExpandFromSystem(mySystem, extended=True)
    if targets:
        xPrintTargets('Extended ' + mySystemName, targets, length=5)

    # Look for Simple Invasions of Player Factions into our Systems
    print(
        f"\nLook for Simple Invasions of Player Factions into {myFactionName} Systems")
    for source_system in myBubble.systems:
        if source_system.factions and source_system.factions[0].influence > 60 and source_system.factions[0].isPlayer:
            targets = source_system.expansion_targets
            if targets:
                for t in targets[:3]:  # Only look at the top 3 targets
                    if myBubble.getsystem(t.systemname).isfactionpresent(myFactionName):
                        xPrintTargets(
                            f"{source_system.name} ({source_system.factions[0].influence:.2f}) : {source_system.controllingFaction}", targets, length=3)
                        break
