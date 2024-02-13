from dataclasses import dataclass
from DataClassesBase import Bubble, System, ExpansionTarget, Presence
import CSNSettings
import simplejson as json
from EliteBGS import LiveSystemDetails


# Expansion : Couldnt work out how to use an Inheritance of System (with expension_targets) so added it to the base class

@dataclass
class BubbleExpansion(Bubble):
    """ Extension of Bubble class that calculates simple expansions for all systems. """
    """ Can calculate Extended on Demand """
    SIMPLERANGE: float = 20
    EXTENDEDRANGE: float = 30

    def __post_init__(self):
        self.systems = sorted(self.systems, key=lambda x: x.name)
        self._ExpandAll()

    def _ExpandAll(self) -> None:
        """ Calculate Simple Expansion for all Systems, or Extended as specified in .env """
        print('Calculating Expansion Targets...')
        CSNSettings.CSNLog.info('Calculating Expansion Targets...')
        system: System
        for system in self.systems:
            # print('.', end='')
            system.expansion_targets = self.ExpandFromSystem(
                system, extended=(system.controllingFaction and system.controllingFaction == CSNSettings.myfaction and CSNSettings.extendedphase))
        self.saveExpansionJson()
        self.saveInvasionJson()
        print('')

    def ExpandFromSystem(self, source_system: System, extended: bool = False) -> list:
        """ Calculate all expansion targets for a system"""
        targets: list[ExpansionTarget] = []
        for target_system in self.cube_systems(source_system, exclude_presense=source_system.controllingFaction):
            target_distance: float = source_system.distance(target_system)
            target_cube_distance: float = source_system.cube_distance(
                target_system)
            if len(target_system.factions) > 7:
                # Too many factions to invade
                pass
            elif len(target_system.factions) < 7:
                # Expansion into a spare slot
                expansion = ExpansionTarget(
                    target_system.name, description='Expansion', score=target_distance/100)
                if target_cube_distance <= self.SIMPLERANGE:
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
                        if target_cube_distance <= self.SIMPLERANGE:
                            targets.append(expansion)
                        elif extended:
                            expansion.extended = True
                            targets.append(expansion)
        if targets:
            targets = sorted(targets, key=lambda x: x.score)
        return targets

    def saveExpansionJson(self) -> None:
        """ Saves best expansion target for all myfactions systems\n"""
        """ Called from post_init so should already have been run """
        allexpansions = list({'name': s.name, 'target': s.nextexpansion.systemname, 'expansionType': str(s.nextexpansion)}
                             for s in self.systems if s.controllingFaction == CSNSettings.myfaction and s.nextexpansion)

        with open(f'data\\{CSNSettings.myfaction}EDSMExpansionTargets.json', 'w') as io:  # Dump to file
            json.dump(allexpansions, io, indent=4)

    @staticmethod
    def loadExpansionJson() -> list:
        """ Returns the best expansion target for all myfactions systems previously saved to json """
        targets = []
        with open(f'data\\{CSNSettings.myfaction}EDSMExpansionTargets.json', 'r') as io:
            targets = json.load(io)
        return targets

    def saveInvasionJson(self) -> None:
        """ Saves all player factions invading myfactions systems\n"""
        """ Called from post_init so should already have been run """
        s: System
        allexpansions = list({'name': s.name, 'faction': s.controllingFaction, 'target': s.nextexpansion.systemname, 'expansionType': str(s.nextexpansion), 'influence': s.influence}
                             for s in self.systems if (s.nextexpansion and self.getsystem(s.nextexpansion.systemname).controllingFaction == CSNSettings.myfaction and s.influence > CSNSettings.invasionparanoialevel and s.factions[0].isPlayer and s.controllingFaction not in CSNSettings.ignorepf))

        with open(f'data\\{CSNSettings.myfaction}EDSMInvasionTargets.json', 'w') as io:  # Dump to file
            json.dump(allexpansions, io, indent=4)

    @staticmethod
    def loadInvasionJson() -> list:
        """ Returns the best expansion target for all myfactions systems previously saved to json """
        targets = []
        with open(f'data\\{CSNSettings.myfaction}EDSMInvasionTargets.json', 'r') as io:
            targets = json.load(io)
        return targets
