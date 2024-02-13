from dataclasses import dataclass
from .Presense import Presence


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
