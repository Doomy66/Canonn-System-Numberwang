from dataclasses import dataclass
from DataClassesBase import Bubble, System, ExpansionTarget, Presence
import CSNSettings
import simplejson as json


# Expansion : Couldnt work out how to use an Inheritance of System (with expension_targets) so added it to the base class

@dataclass
class BubbleExpansion(Bubble):
    """ Extension of Bubble class that calculates simple expansions for all systems. """
    """ Can calculate Extended on Demand """
    SIMPLERANGE: float = 20
    EXTENDEDRANGE: float = 30

    def __post_init__(self):
        # Calculate Simple Expansion for all Systems, or Extended as specified in .env
        print('Calculating Expansion Targets...')
        system: System
        for system in self.systems:
            system.expansion_targets = self.ExpandFromSystem(
                system, extended=(system.controllingFaction == CSNSettings.myfaction and CSNSettings.extendedphase))
        self.savetojson()

    def ExpandFromSystem(self, source_system: System, extended: bool = False) -> list:
        targets: list[ExpansionTarget] = []
        for target_system in self.cube_systems(source_system, exclude_presense=source_system.controllingFaction):
            target_distance: float = source_system.distance(
                source_system, target_system)
            if len(target_system.factions) > 7:
                # Too many factions to invade
                pass
            elif len(target_system.factions) < 7:
                # Expansion into a spare slot
                expansion = ExpansionTarget(
                    target_system.name, description='Expansion', score=target_distance/100)
                if target_distance <= self.SIMPLERANGE:
                    targets.append(expansion)
                elif extended:
                    expansion.extended = True
                    targets.append(expansion)

            else:
                # Possible Invasion
                current_faction: Presence
                for current_faction in target_system.factions:
                    # Must NOT be a Native or Controlling Faction
                    if not (current_faction.isNative or current_faction.name == target_system.controllingFaction):
                        expansion = ExpansionTarget(
                            target_system.name, description='Invasion', faction=current_faction, score=current_faction.influence)
                        if target_distance <= self.SIMPLERANGE:
                            targets.append(expansion)
                        elif extended:
                            expansion.extended = True
                            targets.append(expansion)
        if targets:
            targets = sorted(targets, key=lambda x: x.score)
        return targets

    def savetojson(self) -> None:
        allexpansions = list({'name': s.name, 'target': s.nextexpansion.systemname, 'expansionType': str(s.nextexpansion)}
                             for s in self.systems if s.controllingFaction == CSNSettings.myfaction and s.nextexpansion)

        with open(f'data\\{CSNSettings.myfaction}EDSMExpansionTargets.json', 'w') as io:  # Dump to file
            json.dump(allexpansions, io, indent=4)
