from dataclasses import dataclass, field
from math import sqrt
from EDDBFactions import HomeSystem


@dataclass
class State:
    state: str
    active: bool


@dataclass
class Presence:
    """ Contains A Factions Influence and States in a System"""
    id: int
    name: str
    allegiance: str = ''
    government: str = ''
    influence: float = 0
    state: str = ''
    happiness: str = ''
    isPlayer: bool = False
    isNative: bool = False  # Calculated by System.addsystem
    states: list = field(default_factory=list[State])


@dataclass
class ExpansionTarget():
    """ Details of an Expansion Target """
    systemname: str
    score: float = 0
    extended: bool = False
    description: str = ''
    faction: Presence = None

    def __str__(self) -> str:
        ans = f"{self.systemname} : {'Extended ' if self.extended else ''}{self.description}"
        if self.description == 'Invasion':
            ans = f"{ans} of {self.faction.name} ({self.faction.influence:.2f})"
        return ans


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
    factions: list = field(default_factory=list[Presence])
    # Expansion : Couldnt work out how to use an Inheritance of System (with expension_targets) so added it to the base class
    expansion_targets: list = field(default_factory=list[ExpansionTarget])

    @staticmethod
    def distance(a: "System", b: "System") -> float:
        """ Direct Straight Line Distance between 2 systems """
        return (round(sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2), 2))

    @staticmethod
    def cube_distance(a: "System", b: "System") -> float:
        """ Maximum Axis Difference between 2 systems """
        return (max(abs(a.x-b.x), abs(a.y-b.y), abs(a.z-b.z)))

    def addfaction(self, f: Presence) -> None:
        """ Add or Upate Faction Presense to a System"""

        # Calculate Native Status
        if self.name in f.name:
            f.isNative = True
        else:
            f.isNative = self.name.lower() == HomeSystem(f.name)

        for i, x in enumerate(self.factions):
            if x.name == f.name:
                self.factions[i] = f
                return
        self.factions.append(f)
        self.factions = sorted(
            self.factions, key=lambda x: x.influence, reverse=True)

    def isfactionpresent(self, name: str) -> bool:
        """ Is a faction present in System """
        for f in self.factions:
            if f.name == name:
                return True
        return False


@dataclass
class Bubble:
    """ Contains a list of the Sytems. 
        Create your list of Sysems from a Factory of your choice """
    systems: list = field(default_factory=list[System])

    def getsystem(self, name: str) -> System:
        """ Returns a System object from it's name """
        """ Yes, probably could be a dict of sometype but too much for v0"""
        return next((x for x in self.systems if x.name.lower() == name.lower()), None)

    def distance(self, a: System, b: System) -> float:
        """ Direct Straight Line Distance between 2 systems """
        return (round(sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2), 2)) if (a and b) else None

    def cube_distance(self, a: System, b: System) -> float:
        """ Maximum Axis Difference between 2 systems """
        return (max(abs(a.x-b.x), abs(a.y-b.y), abs(a.z-b.z)))if (a and b) else None

    def cube_systems(self, system: System, range=30, exclude_presense: str = '') -> list["System"]:
        """ Returns List of all Systems within the range Sorted by Distance.\n
            Optionally excluding systems where faction name of exlude_presence is already present.\n
            Use Range of 20 for Simple Expansion, 30 for Extended\n
            Sorted by Distance
        """
        ans = sorted(list(filter(lambda x: self.cube_distance(
            system, x) <= range and (exclude_presense == '' or not x.isfactionpresent(exclude_presense)), self.systems)), key=lambda x: self.distance(x, system))
        return ans

    def faction_presence(self, factionname: str) -> list[System]:
        """ Returns a List of all System where the faction is present"""
        return list(filter(lambda x: x.isfactionpresent(factionname), self.systems))
