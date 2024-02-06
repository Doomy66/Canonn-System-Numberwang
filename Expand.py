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

    for source_system in myBubble.systems:
        if source_system.controllingFaction == myFactionName and source_system.factions[0].influence > 70:
            targets = source_system.expansion_targets
            if targets:
                xPrintTargets(source_system.name, targets)

    # # Simple is calculated in Post Init,
    # if mySystem.expansion_targets:
    #     xPrintTargets('Stored   '+mySystemName, mySystem.expansion_targets)

    # # Need to recalculate to check for Extended
    # targets = myBubble.ExpandFromSystem(mySystem, extended=True)
    # if targets:
    #     xPrintTargets('Extended ' + mySystemName, targets, length=5)
