import logging
import os

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

# No orders to boost inf for system control etc. Leave it to the system owner.
surrendered_systems = ['A List of System Names']


logging.getLogger('googleapiclient.discovery_cache').setLevel(
    logging.ERROR)  # Else get spurious warnings

logging.basicConfig(filename='data\CSNLog.'+os.environ['COMPUTERNAME']+'.log',
                    filemode='a',
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    level=logging.INFO)


CSNLog = logging.getLogger('CSN')
CSNLog.info('Logging Configured')
