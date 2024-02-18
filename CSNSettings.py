import logging
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Canonn Discord
wh_id = os.environ.get('wh_id')
wh_token = os.environ.get('wh_token')

# Canonn Google Sheet
override_workbook = os.environ.get('override_workbook')
override_sheet = os.environ.get('override_sheet')

# Faction Settings
myfaction = os.environ.get('myfaction')
extendedphase: bool = os.environ.get(
    'extendedphase')[:1].upper() in ['Y', 'T']

# Player Factions to treat as NPCs, either because they are inactive or other reasons
ignorepf = os.environ.get('ignorepf').split(",")
invasionparanoialevel = float(os.environ.get('invasionparanoialevel'))


def isIgnored(faction: str) -> bool:
    """ Returns True if faction name is in the list of ignored PF"""
    return faction in ignorepf


# No orders to boost inf for system control etc. Leave it to the system owner.
surrendered_systems = ['A List of System Names']

# Global Variables to count Requests
myGlobals = {'nRequests': 0}


def RequestCount() -> None:
    myGlobals['nRequests'] += 1


try:
    with open(f'data\\DiscordIcons.json', 'r') as io:
        dIcons = json.load(io)
except:
    dIcons = {}

logging.getLogger('googleapiclient.discovery_cache').setLevel(
    logging.ERROR)  # Else get spurious warnings

logging.basicConfig(filename='data\CSNLog.'+os.environ['COMPUTERNAME']+'.log',
                    filemode='a',
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    level=logging.INFO)


CSNLog = logging.getLogger('CSN')
CSNLog.info(f'Logging Configured for {myfaction}')
