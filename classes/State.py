from dataclasses import dataclass
from enum import Enum


class Phase(Enum):
    """ Phase of a State. Active, Pending or Recovering"""
    ACTIVE = 'A'
    PENDING = 'P'
    RECOVERING = 'R'


@dataclass
class State:
    """ Contains information about one of a Factions states"""
    state: str  # NB can vary depending on source e.g 'Civil war' and 'Civilwar'
    phase: Phase = 'A'  # Active, Pending or Recovering
    opponent: str = ''
    atstake: str = ''
    gain: str = ''
    dayswon: int = 0
    dayslost: int = 0

    def __str__(self) -> str:
        ans: str = f"{self.state}"

        if self.opponent and self.isConflict:
            if self.phase == 'R':
                if self.dayswon > self.dayslost:
                    ans += f" Won {self.gain}"
                elif self.dayswon < self.dayslost:
                    ans += f" Lost {self.atstake}"
                else:
                    ans += ' Drawn'
            else:
                ans += f" with {self.opponent} ({self.dayswon} v {self.dayslost}) {' Pending' if self.phase==Phase.PENDING else ''}"
        else:
            ans += f"{'' if self.phase == Phase.ACTIVE else ' Pending' if self.phase == Phase.PENDING else ' Recovering'}"

        return ans

    @property
    def isConflict(self) -> bool:
        return ('war' in self.state.lower() or 'election' in self.state.lower())
