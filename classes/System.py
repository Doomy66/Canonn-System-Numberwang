from dataclasses import dataclass, field
from datetime import datetime
from .Presense import Presence
from .ExpansionTarget import ExpansionTarget
from providers.EDDBFactions import HomeSystem
from math import sqrt


@dataclass
class System:
    """ Contains information about a System and its Factions"""
    """ Has some duplicated static methods from Bubble for work before it is added to a Bubble"""
    source: str  # Source of Data
    id: int
    id64: int
    name: str
    x: float
    y: float
    z: float
    allegiance: str = ''
    government: str = ''
    state: str = ''
    economy: str = ''
    security: str = ''
    population: int = 0
    controllingFaction: str = ''
    influence = 0
    factions: list = field(default_factory=list[Presence])
    # stations: list = field(default_factory=list[Station])
    # Only Pouplated in BubbleExpansion Sub-Class
    expansion_targets: list = field(default_factory=list[ExpansionTarget])
    updated: datetime = datetime.now()

    def __str__(self) -> str:
        ans = f"{self.name} : {self.controllingFaction} ({self.influence}%)"
        for faction in self.factions:
            ans += f"\n    {faction}"
        return ans

    def distance(self, othersystem: "System") -> float:
        """ Direct Straight Line Distance between 2 systems """
        return (round(sqrt((self.x-othersystem.x)**2+(self.y-othersystem.y)**2+(self.z-othersystem.z)**2), 2))

    def cube_distance(self, othersystem: "System") -> float:
        """ Maximum Axis Difference between 2 systems """
        return (max(abs(self.x-othersystem.x), abs(self.y-othersystem.y), abs(self.z-othersystem.z)))

    def addfaction(self, faction: Presence) -> None:
        """ Add or Upate Faction Presense to a System"""

        faction.source = self.source
        # Calculate Native Status
        if self.name in faction.name:
            faction.isNative = True
        else:
            faction.isNative = self.name.lower() == HomeSystem(faction.name)

        f: Presence
        for i, f in enumerate(self.factions):
            if f.name == faction.name:
                self.factions[i] = faction
                return
        self.factions.append(faction)
        self.factions = sorted(
            self.factions, key=lambda x: x.influence, reverse=True)

    def isfactionpresent(self, name: str) -> bool:
        """ Is a faction present in System """
        for f in self.factions:
            if f.name == name:
                return True
        return False

    @property
    def nextexpansion(self) -> ExpansionTarget:
        """ The next expected Expansion """
        if self.expansion_targets:
            return self.expansion_targets[0]
        return None

    @property
    def influence(self) -> float:
        return self.factions[0].influence if self.factions else 0
