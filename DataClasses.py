import os
import datetime
import json
import requests
import gzip
from dataclasses import dataclass, field
from math import sqrt
import pickle


@dataclass
class Presence:
    id: int
    name: str
    allegiance: str = ''
    government: str = ''
    influence: float = 0
    state: str = ''
    happiness: str = ''
    isPlayer: bool = False
    isNative: bool = True  # Currently guessing via faction name !!
    # activestates:list =[]
    # recoveringStates:list = []
    # pendingStates:list = []


@dataclass
class System:
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
        for i, x in enumerate(self.factions):
            if x.name == f.name:
                self.factions[i] = f
                return
        self.factions.append(f)

    def isfactionpresent(self, name: str) -> bool:
        """ Is a faction present in System """
        for f in self.factions:
            if f.name == name:
                return True
        return False


@dataclass
class Bubble:
    """ Contains a list of the Sytems. Also loads the EDDB Faction Archive and applies to the systems on creation
        Create your list of sysems from a Factory of your choice """
    systems: list = field(default_factory=list[System])

    def __post_init__(self):
        print('Loading EDDB Factions Archive...')
        # Use archived EDDF Factions Data as its the best reliable source for Faction Presence's Native Status
        with open('EDDBFactions.pickle', 'rb') as io:
            eddbf = pickle.load(io)
            # Factions with the System name in them are already defaulted to be native
            for f in filter(lambda x: x['home_system_id'] and (x['home_system'] not in x['name']), eddbf):
                s = self.getsystem(f['home_system'])
                if s:  # System may not be in the list of systems for many valid reasons
                    for fp in s.factions:
                        if fp.name == f['name']:
                            fp.isNative = True

    def getsystem(self, name: str) -> System:
        return next((x for x in self.systems if x.name.lower() == name.lower()), None)

    def distance(self, a: System, b: System) -> float:
        """ Direct Straight Line Distance between 2 named systems """
        return (round(sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2), 2)) if (a and b) else None

    def cube_distance(self, a: System, b: System) -> float:
        """ Maximum Axis Difference between 2 named systems """
        return (max(abs(a.x-b.x), abs(a.y-b.y), abs(a.z-b.z)))if (a and b) else None

    def cube_systems(self, system: System, range=30, exclude_presense: str = '') -> list["System"]:
        """ Returns List of all Systems within the range Sorted by Distance.\n
            Optionally excluding systems where faction name of exlude_presence is already present.\n
            Use Range of 20 for Simple Expansion, 30 for Extended
        """
        ans = sorted(list(filter(lambda x: self.cube_distance(
            system, x) <= range and (exclude_presense == '' or not x.isfactionpresent(exclude_presense)), self.systems)), key=lambda x: self.distance(x, system))
        return ans

    def faction_presence(self, factionname: str) -> list[System]:
        """ Returns a List of all System where the faction is present"""
        return list(filter(lambda x: x.isfactionpresent(factionname), self.systems))
