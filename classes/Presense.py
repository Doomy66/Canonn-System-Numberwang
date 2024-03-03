from dataclasses import dataclass, field
from classes.State import State, Phase


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

    @property
    def activeconflict(self) -> State:
        """ Conflict State if available """
        return next((x for x in self.states if x.isConflict and x.phase in (Phase.ACTIVE, Phase.PENDING)), None)
