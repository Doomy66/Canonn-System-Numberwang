from dataclasses import dataclass


@dataclass
class State:
    state: str  # NB can vary depending on source e.g 'Civil war' and 'Civilwar'
    phase: str = 'A'  # Active, Pending or Recovering
    opponent: str = ''
    atstake: str = ''
    gain: str = ''
    dayswon: int = 0
    dayslost: int = 0

    def __str__(self) -> str:
        ans: str = f"{self.state}" + \
            f"{'' if self.phase == 'A' else ' Pending' if self.phase == 'P' else ' Recovering'}"
        if self.opponent and self.isConflict:
            if self.phase == 'R':
                if self.dayswon > self.dayslost:
                    ans += f" Won {self.gain}"
                elif self.dayswon < self.dayslost:
                    ans += f" Lost {self.atstake}"
                else:
                    ans += ' Drawn'
            else:
                ans += f" with {self.opponent} ({self.dayswon} v {self.dayslost})"

        return ans

    @property
    def isConflict(self) -> bool:
        return ('war' in self.state.lower() or 'election' in self.state.lower())
