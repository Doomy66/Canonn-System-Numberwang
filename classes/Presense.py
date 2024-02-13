from dataclasses import dataclass, field
from .State import State


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
