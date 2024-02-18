import logging
import os
import platform
from dotenv import load_dotenv, dotenv_values, find_dotenv
import json

myEnv = dotenv_values('.env.'+platform.node())
if not myEnv:
    myEnv = dotenv_values()

# Canonn Discord
wh_id = myEnv.get('wh_id')
wh_token = myEnv.get('wh_token')

# Canonn Google Sheet
override_workbook = myEnv.get('override_workbook')
override_sheet = myEnv.get('override_sheet')

# Faction Settings
myfaction = myEnv.get('myfaction')
extendedphase: bool = myEnv.get(
    'extendedphase')[:1].upper() in ['Y', 'T']

# Player Factions to treat as NPCs, either because they are inactive or other reasons
ignorepf = myEnv.get('ignorepf').split(",")
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
    with open(f'resources\\DiscordIcons', 'r') as io:
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
