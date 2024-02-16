from dataclasses import dataclass, field


@dataclass
class Station:
    """ Station, Base, Fleet Carrier etc"""
    """ NOT YET IMPLEMENTED """
    id: int
    type: str
    name: str
    faction: str = ''
    # distance: float = 0
    # body: str = ''
    # allegiance: str = ''
    # government: str = ''
    economy1: str = ''
    economy2: str = ''
    # marketid: int
    hasshipyard: bool = False
    hasoutfitting: bool = False
    services: list = field(default_factory=list[str])
