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
