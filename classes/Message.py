from dataclasses import dataclass
from enum import Enum


class Overide(Enum):
    OVERRIDE = "O"
    ADDITIONAL = 'A'
    PEACETIME = 'P'
    NORMAL = 'N'


@dataclass
class Message:
    """ CSN Message """
    systemname: str
    priority: int
    text: str
    emoji: str = ''
    override: Overide = Overide.NORMAL
    complete: bool = False

    def __str__(self) -> str:
        return (f"{self.systemname} - {self.text}")

    @property
    def isDiscord(self) -> bool:
        return self.priority <= 10 or self.priority > 20

    @property
    def isPatrol(self) -> bool:
        return self.priority <= 20
