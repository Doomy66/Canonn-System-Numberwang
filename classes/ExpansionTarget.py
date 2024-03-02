from dataclasses import dataclass
from classes.Presense import Presence


@dataclass
class ExpansionTarget():
    """ Details of an Expansion Target """
    systemname: str
    score: float = 0
    extended: bool = False
    description: str = ''
    faction: Presence = None

    def __str__(self) -> str:
        ans = f"{self.systemname}{'*' if self.extended else ''} ({self.faction.name})"
        if self.description == 'Invasion':
            ans = f"{self.systemname} {self.description} of {self.faction.name} ({self.faction.influence:.2f}%)"
        return ans
