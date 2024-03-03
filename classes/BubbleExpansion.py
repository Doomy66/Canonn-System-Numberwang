from dataclasses import dataclass, field
from classes.Bubble import Bubble
from classes.System import System
from classes.Presense import Presence
from classes.ExpansionTarget import ExpansionTarget
import CSNSettings
import simplejson as json
from providers.EliteBGS import EBGSPreviousVisitors
import pickle
import os
from time import sleep


DATADIR = '.\data'

# Expansion : Couldnt work out how to use an Inheritance of System (with expension_targets) so added it to the base class


@dataclass
class BubbleExpansion(Bubble):
    """ Extension of Bubble class that calculates simple expansions for all systems. """
    """ Can calculate Extended on Demand """
    SIMPLERANGE: float = 20
    EXTENDEDRANGE: float = 30

    def __post_init__(self):
        self.systems = sorted(self.systems, key=lambda x: x.name)
        if self.empire == CSNSettings.FACTION:  # Keep the History file for your own faction
            self.HistoryLoad()
        self._ExpandAll()

    def _ExpandAll(self) -> None:
        """ Calculate Simple Expansion for all Systems, or Extended as specified in .env """
        print('Calculating Expansion Targets...')
        CSNSettings.CSNLog.info('Calculating Expansion Targets...')
        system: System
        for system in self.systems:
            system.expansion_targets = self.ExpandFromSystem(
                system, extended=(system.controllingFaction and system.controllingFaction == CSNSettings.FACTION and CSNSettings.EXTENDEDPHASE))
        self.saveExpansionJson()
        self.saveInvasionJson()

    def ExpandFromSystem(self, source_system: System, extended: bool = False) -> list:
        """ Calculate all expansion targets for a system"""
        targets: list[ExpansionTarget] = []
        for target_system in self.cube_systems(source_system, exclude_presense=source_system.controllingFaction):
            target_distance: float = source_system.distance(target_system)
            target_cube_distance: float = source_system.cube_distance(
                target_system)
            target_retreated_bonus = 100 if (source_system.controllingFaction in self.systemhistory[
                target_system.name]) else 0
            if len(target_system.factions) > 7:
                # Too many factions to invade
                pass
            elif not target_system.factions:
                # No factions - dead system or prison
                pass
            elif len(target_system.factions) < 7:
                # Expansion into a spare slot
                expansion = ExpansionTarget(
                    target_system.name, description='Expansion', score=target_retreated_bonus+target_distance/100, faction=target_system.factions[0])
                if target_cube_distance <= self.SIMPLERANGE:
                    targets.append(expansion)
                elif extended:
                    expansion.extended = True
                    targets.append(expansion)

            else:
                # Possible Invasion
                current_faction: Presence
                for current_faction in target_system.factions:
                    # Must NOT be a Native or Controlling Faction, or in a conflict
                    if not (current_faction.isNative or current_faction.name == target_system.controllingFaction or current_faction.activeconflict):
                        expansion = ExpansionTarget(
                            target_system.name, description='Invasion', faction=current_faction, score=target_retreated_bonus+current_faction.influence)
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
                             for s in self.systems if s.controllingFaction == CSNSettings.FACTION and s.nextexpansion)

        with open(f'data\\{CSNSettings.FACTION}EDSMExpansionTargets.json', 'w') as io:  # Dump to file
            json.dump(allexpansions, io, indent=4)

    @staticmethod
    def loadExpansionJson() -> list:
        """ Returns the best expansion target for all myfactions systems previously saved to json """
        targets = []
        with open(f'data\\{CSNSettings.FACTION}EDSMExpansionTargets.json', 'r') as io:
            targets = json.load(io)
        return targets

    def saveInvasionJson(self) -> None:
        """ Saves all factions invading myfactions systems\n"""
        """ Called from post_init so should already have been run """
        s: System
        allexpansions = list({'name': s.name, 'faction': s.controllingFaction, 'target': s.nextexpansion.systemname, 'expansionType': str(s.nextexpansion), 'influence': s.influence}
                             for s in self.systems if (s.nextexpansion and self.getsystem(s.nextexpansion.systemname).controllingFaction == CSNSettings.FACTION and s.influence > CSNSettings.PARANOIA_LEVEL))

        with open(f'data\\{CSNSettings.FACTION}EDSMInvasionTargets.json', 'w') as io:  # Dump to file
            json.dump(allexpansions, io, indent=4)

    @staticmethod
    def loadInvasionJson() -> list:
        """ Returns the best expansion target for all myfactions systems previously saved to json """
        targets = []
        with open(f'data\\{CSNSettings.FACTION}EDSMInvasionTargets.json', 'r') as io:
            targets = json.load(io)
        return targets

    def HistoryLoad(self) -> None:
        """ Loads, refreshes and saves System History. This is a Dict of Systems with a set containing ALL factions that have ever been present """
        """ BEWARE Assumes Bubble has been reduced to a faction and Never Reduces"""

        def HistorySave():
            os.makedirs(DATADIR, exist_ok=True)
            with open(os.path.join(DATADIR, self.empire+'EBGS_SysHist.pickle'), 'wb') as io:
                pickle.dump(self.systemhistory, io)

        self.systemhistory = dict()
        if os.path.exists(os.path.join(DATADIR, self.empire+'EBGS_SysHist.pickle')):
            with open(os.path.join(DATADIR, self.empire+'EBGS_SysHist.pickle'), 'rb') as io:
                self.systemhistory = pickle.load(io)
        print(
            f"Loading System History {len(self.systemhistory)}/{len(self.systems)}...")
        system: System
        anychanges: bool = False
        for system in self.systems:
            # if system.name == 'Varati':
            #     bubble.systemhistory[system.name] = set()  # TEST
            if system.population > 0 and not self.systemhistory.get(system.name, None):
                self.systemhistory[system.name] = set(
                    EBGSPreviousVisitors(system.name))
                anychanges = True
                sleep(5)  # Be nice to EBGS
            else:
                faction: Presence
                for faction in system.factions:
                    if faction.name not in self.systemhistory[system.name]:
                        print(
                            f" New Expansion Detected {system.name}, {faction.name}")
                        self.systemhistory[system.name].add(faction.name)
                        anychanges = True
        if anychanges:
            HistorySave()
