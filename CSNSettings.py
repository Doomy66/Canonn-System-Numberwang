import logging
import platform
from dotenv import dotenv_values
import json

myEnv = dotenv_values('.env.'+platform.node())
if not myEnv:
    myEnv = dotenv_values()

# Canonn Discord
WEBHOOK_ID = myEnv.get('wh_id')
WEBHOOK_TOKEN = myEnv.get('wh_token')

# Canonn Google Sheet
OVERRIDE_WORKBOOK = myEnv.get('override_workbook')

# Faction Settings
FACTION: str = myEnv.get('myfaction')
EXTENDEDPHASE: bool = myEnv.get(
    'extendedphase')[:1].upper() in ['Y', 'T']
HOME = myEnv.get('home')

# Player Factions to treat as NPCs, either because they are inactive or other reasons
_IGNOREPF = myEnv.get('ignorepf').split(",")
_ALLIES = myEnv.get('allies').split(",")
_PARTNERS = myEnv.get('partners').split(",")
PARANOIA_LEVEL = float(myEnv.get('invasionparanoialevel'))
LIGHTHOUSE = myEnv.get('lighthousesystem')

# dIcons from json file
try:
    with open(f'resources\\DiscordIcons.json', 'r') as io:
        ICONS = json.load(io)
except:
    ICONS = {}


def isIgnored(faction: str) -> bool:
    """ Returns True if faction name is in the list of ignored PF or an Ally"""
    return isAlly(faction) or (faction in _IGNOREPF)


def isAlly(faction: str) -> bool:
    """ Returns True if faction name is in the list of Allied PF"""
    return faction in _ALLIES


def isPartner(faction: str) -> bool:
    """ Returns True if faction name is in the list of Partner PF"""
    return faction in _PARTNERS


# No orders to boost inf for system control etc. Leave it to the system owner. Not Used Yet.
surrendered_systems = ['A List of System Names']

# Global Variables to count Requests
GLOBALS = {'nRequests': 0}

# Keep a track of API Requests


def RequestCount() -> None:
    GLOBALS['nRequests'] += 1


logging.getLogger('googleapiclient.discovery_cache').setLevel(
    logging.ERROR)  # Else get spurious warnings

logging.basicConfig(filename='data\CSNLog.'+platform.node()+'.log',
                    filemode='a',
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    level=logging.INFO)


CSNLog = logging.getLogger('CSN')
CSNLog.info(f'>>>>>>>> Start Logging for {FACTION}')
