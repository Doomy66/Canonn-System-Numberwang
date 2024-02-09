from dataclasses import dataclass, field
from math import sqrt
from EDDBFactions import HomeSystem
from datetime import datetime


@dataclass
class State:
    state: str  # NB can vary depending on source e.g 'Civil war' and 'Civilwar'
    active: str = 'A'  # Active, Pending or Recovering
    opponent: str = ''
    atstake: str = ''
    gain: str = ''
    dayswon: int = 0
    dayslost: int = 0

    def __str__(self) -> str:
        ans: str = f"{self.state}" + \
            f"{'Active' if self.active == 'A' else ' Pending' if self.active == 'P' else ' Recovering'}"
        if self.opponent and 'war' in self.state.lower():
            if self.active == 'R':
                if self.dayswon > self.dayslost:
                    ans += f" Won {self.gain}"
                elif self.dayswon < self.dayslost:
                    ans += f" Lost {self.atstake}"
                else:
                    ans += ' Drawn'
            else:
                ans += f" with {self.opponent} {self.dayswon} v {self.dayslost}"

        return ans


@dataclass
class Station:
    """ Station, Base, Fleet Carrier etc"""
    """ NOT YET IMPLEMENTED """
    id: int
    type: str
    name: str
    faction: str = ''
    systemname: str = ''  # denormalised
    # distance: float = 0
    # body: str = ''
    # allegiance: str = ''
    # government: str = ''
    # economy1: str = ''
    # economy2: str = ''
    # marketid: int
    # hasshipyard: bool = False
    # hasoutfitting: bool = False
    # services: list = field(default_factory=list[str])


@dataclass
class Presence:
    """ Contains A Factions Influence and States in a System"""
    id: int
    name: str
    allegiance: str = ''
    government: str = ''
    influence: float = 0
    happiness: str = ''
    isPlayer: bool = False
    isNative: bool = False  # Calculated by System.addsystem - Too slow to be a property
    states: list = field(default_factory=list[State])
    source: str = ''

    def __str__(self) -> str:
        return f"{self.name} ({self.influence}%) {'Player ' if self.isPlayer else ''}{'' if self.isNative else 'Non Native' }{'/'.join(str(x) for x in self.states)}"


@dataclass
class ExpansionTarget():
    """ Details of an Expansion Target """
    systemname: str
    score: float = 0
    extended: bool = False
    description: str = ''
    faction: Presence = None

    def __str__(self) -> str:
        ans = f"{'Extended ' if self.extended else ''}{self.description}"
        if self.description == 'Invasion':
            ans = f"{ans} of {self.faction.name} ({self.faction.influence:.2f}%)"
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

    @staticmethod
    def distance(a: "System", b: "System") -> float:
        """ Direct Straight Line Distance between 2 systems """
        return (round(sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2), 2))

    @staticmethod
    def cube_distance(a: "System", b: "System") -> float:
        """ Maximum Axis Difference between 2 systems """
        return (max(abs(a.x-b.x), abs(a.y-b.y), abs(a.z-b.z)))

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
