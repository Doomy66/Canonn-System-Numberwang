from dataclasses import dataclass, field
from classes.System import System
from math import sqrt
import CSNSettings


@dataclass
class Bubble:
    """ Contains a list of the Sytems. 
        Create your list of Sysems from a Factory of your choice """
    systems: list = field(default_factory=list[System])
    empire: str = CSNSettings.FACTION
    # key is system name, value is a set of all factions that have ever been present
    systemhistory: dict[str, set[str]] = field(
        default_factory=dict[str, set[str]])

    def getsystem(self, name: str) -> System | None:
        """ Returns a System object from it's name """
        """ Yes, probably could be a dict of sometype but too much for v0"""
        return next((x for x in self.systems if x.name.lower() == name.lower()), None)

    def distance(self, a: System, b: System) -> float:
        """ Direct Straight Line Distance between 2 systems """
        return (round(sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2), 2)) if (a and b) else 0

    def cube_distance(self, a: System, b: System) -> float:
        """ Maximum Axis Difference between 2 systems """
        return (max(abs(a.x-b.x), abs(a.y-b.y), abs(a.z-b.z)))if (a and b) else 0

    def cube_systems(self, system: System, range: float = 30, exclude_presense: str = '') -> list["System"]:
        """ Returns List of all Systems within the range Sorted by Distance.\n
            Optionally excluding systems where faction name of exlude_presence is already present.\n
            Use Range of 20 for Simple Expansion, 30 for Extended\n
            Sorted by Distance
        """
        ans = sorted(list(filter(lambda x: self.cube_distance(
            system, x) < range and x.population and (exclude_presense == '' or not x.isfactionpresent(exclude_presense)), self.systems)), key=lambda x: self.distance(x, system))
        return ans

    def faction_presence(self, factionname: str) -> list[System]:
        """ Returns a List of all System where the faction is present"""
        return list(filter(lambda x: x.isfactionpresent(factionname), self.systems))
