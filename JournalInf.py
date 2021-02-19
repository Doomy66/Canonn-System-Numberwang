import os
import simplejson as json
from datetime import datetime
import api

JFOLDER = os.environ.get('USERPROFILE') + \
    f'\\Saved Games\\Frontier Developments\\Elite Dangerous'


def isjfile(f):
    # Checks if a file is a Journal and after the last tick
    global JFOLDER
    return os.path.isfile(JFOLDER+'\\'+f) and f.endswith('.log') and datetime.utcfromtimestamp(os.path.getmtime(JFOLDER+'\\'+f)) > LASTTICK


def jLoad(f):
    global JFOLDER
    x = []
    with open(JFOLDER+'\\'+f, encoding="utf8") as io:
        for l in io:
            x.append(json.loads(l))
    return(x)

def lHappy(e):
    sysname = e['StarSystem']
    try:
        for lFaction in e['Factions']:
            if lFaction['Name'] == 'Canonn':
                pass
                # print('=',sysname,lFaction['Happiness_Localised'])
    except:
        pass
    return

class SysNames():
    # Dictionary of id and name with failable name lookup
    def __init__(self):
        self = {}

    def add(self, id, name):
        self.__dict__[id] = name

    def name(self, id):
        try:
            return(self.__dict__[id])
        except:
            return("<Unkown>")


class ActionLog(list):
    # List of reported Events in usefull structure
    def add(self, sys, faction, event, num=1, inf=0, ton=0, profit=0):
        for i in self:
            if i["sys"] == sys and i["faction"] == faction and i["event"] == event:
                i["count"] += num
                i["inf"] += inf
                i['ton'] += ton
                i['profit'] += profit
                num = 0
        if num != 0:
            self.append({"sys": sys, "faction": faction,
                         "event": event, "count": num, "inf": inf, 'ton': ton, 'profit': profit})


LASTTICK = api.getlasttick()

print(f'.Scanning {JFOLDER} since UTC {LASTTICK}')
dir = sorted(filter(lambda x: isjfile(x), os.listdir(JFOLDER)), reverse=True)

myactions = ActionLog()
systems = SysNames()

ignore = {'Music', 'ReceiveText', 'NpcCrewPaidWage', 'ReservoirReplenished', 'DockingGranted', 'DockingRequested', 'DockingDenied', 'Screenshot',
          'Scan', 'NavBeaconScan', 'FSSSignalDiscovered', 'ShipTargeted', 'Loadout', 'EngineerProgress', 'FSDTarget', 'FSSDiscoveryScan', 'Scanned',
          'RefuelAll', 'BuyAmmo', 'MaterialCollected', 'Fileheader', 'Commander', 'Synthesis', 'ModuleSwap', 'ModuleStore', 'ModuleSellRemote', 'MassModuleStore', 'ModuleSell',
          'SetUserShipName', 'ShipyardBuy', 'ShipyardNew', 'EngineerCraft',
          'Materials', 'LoadGame', 'Rank', 'Progress', 'Reputation', 'Missions', 'Statistics', 'Cargo', 'Friends', 'SquadronStartup', 'SendText', 'SharedBookmarkToSquadron',
          'ModuleInfo', 'StartJump', 'SupercruiseExit', 'UnderAttack', 'Shutdown', 'USSDrop', 'MiningRefined', 'ProspectedAsteroid', 'SAASignalsFound',
          'LaunchDrone', 'ApproachSettlement', 'Market', 'MarketBuy', 'Deliver', 'Mission_Delivery', 'Collect', 'MissionAccepted', 'SupercruiseEntry', 'CargoDepot', 'ApproachBody',
          'Bounty', 'Shutdown', 'SAAScanComplete', 'DatalinkScan', 'DatalinkVoucher', 'MissionRedirected', 'LeaveBody', 'Interdicted', 'PayBounties',
          'Repair', 'HullDamage', 'LaunchFighter', 'WingAdd', 'WingJoin', 'CrewAssign', 'FighterDestroyed', 'RestockVehicle', 'ModuleBuy', 'WingLeave', 'DockFighter',
          'RepairAll', 'HeatWarning', 'BuyDrones', 'FSSAllBodiesFound', 'MaterialTrade', 'ShipyardSwap', 'ShipyardTransfer', 'StoredShips', 'FighterRebuilt', 'WingInvite',
          'EjectCargo', 'FuelScoop', 'Shipyard', 'Undocked', 'NavRoute', 'Outfitting', 'StoredModules', 'FetchRemoteModule', 'RebootRepair', 'ModuleRetrieve', 'BuyExplorationData',
          'CarrierTradeOrder', 'CarrierStats', 'CarrierFinance', 'CarrierJumpRequest', 'CarrierBuy', 'CarrierCrewServices', 'CarrierBankTransfer', 'CargoTransfer', 'CarrierDepositFuel', '!CarrierJump'
          }

for f in dir:
    print('..'+f, end='')
    currentsys = ''
    sysname = ''
    currentfaction = ''
    startsystem = ''

    j = jLoad(f)
    for e in j:
        if e['event'] == 'Docked':
            systems.add(e['SystemAddress'], e['StarSystem'])
            currentsys = e['SystemAddress']
            sysname = e['StarSystem']
            currentfaction = e['StationFaction']['Name']
            startsystem = sysname if startsystem == '' else startsystem
            lHappy(e)
        elif e['event'] == 'FSDJump':
            systems.add(e['SystemAddress'], e['StarSystem'])
            currentsys = e['SystemAddress']
            sysname = e['StarSystem']
            try:
                currentfaction = e['SystemFaction']['Name']
                lHappy(e)
            except:
                currentfaction = ''  # Unpopulated system
            startsystem = sysname if startsystem == '' else startsystem
        elif e['event'] == 'Location':
            systems.add(e['SystemAddress'], e['StarSystem'])
            currentsys = e['SystemAddress']
            sysname = e['StarSystem']
            try:
                currentfaction = e['SystemFaction']['Name']
                lHappy(e)
            except:
                currentfaction = ''  # Unpopulated system
            startsystem = sysname if startsystem == '' else startsystem
        elif e['event'] == 'MultiSellExplorationData':
            myactions.add(currentsys, currentfaction,
                          e['event'], 1, 0, 0, e['BaseValue'])  # 1 Check for FC UC
        elif e['event'] == 'MarketSell':
            if currentfaction != 'FleetCarrier':
                if 'BlackMarket' in list(e.keys()) and e['BlackMarket']:
                    myactions.add(currentsys, currentfaction,
                                  'BlackMarketSell', 1, 0, e['Count'], e['Count']*(e['SellPrice']-e['AvgPricePaid']))
                elif e['SellPrice'] >= e['AvgPricePaid']:
                    myactions.add(currentsys, currentfaction, e['event'], 1, 0, e['Count'], e['Count']*(
                        e['SellPrice']-e['AvgPricePaid']))
                else:
                    myactions.add(currentsys, currentfaction, e['event']+'Loss', -1, 0, e['Count'], e['Count']*(
                        e['SellPrice']-e['AvgPricePaid']))
        elif e['event'] == 'MissionCompleted':
            for f in e['FactionEffects']:
                for i in f['Influence']:
                    if i['Trend'] == 'UpGood':
                        myactions.add(i['SystemAddress'], f['Faction'],
                                      e['event'], 1, len(i['Influence']))
                    else:
                        myactions.add(i['SystemAddress'],
                                      f['Faction'] if f['Faction'] != '' else e['TargetFaction'] if 'TargetFaction' in e.keys(
                        ) else '',
                            'MissionTarget', 1,
                            -len(i['Influence']))
        elif e['event'] == 'RedeemVoucher':
            if e['Type'] == 'bounty':
                for handin in e['Factions']:
                    # No data to distiguish betwen a FC or IF. Would have to search for factions in system to check if the Inf Counts
                    if (currentfaction == 'FleetCarrier' or not 'BrokerPercentage' in e) and handin['Faction'] != '':
                        myactions.add(
                            currentsys, handin['Faction'], e['event']+e['Type'].title())
            elif e['Type'] == 'CombatBond' and e['Faction'] != '':
                myactions.add(currentsys, e['Faction'],
                              e['event']+e['Type'].title())
        elif e['event'] == 'CommitCrime':
            myactions.add(currentsys, e['Faction'], e['event'], -1)
        elif e['event'] == 'FactionKillBond' or e['event'] == 'CapShipBond':
            myactions.add(currentsys, e['AwardingFaction'], e['event'])
        elif not e['event'] in ignore:
            myactions.add(0, '<Unprocessed>', e['event'])
        else:
            pass
            # print(e['event'])
            #

print('')

myactions = sorted(myactions, key=lambda i: systems.name(
    i['sys'])+i['faction']+i['event'])

for a in myactions:
    if a['inf'] != 0:
        print(
            f'{systems.name(a["sys"])} : {a["faction"]} : {a["event"]} x {a["count"]} Inf {a["inf"]}')
    elif a['ton'] != 0:
        print(f'{systems.name(a["sys"])} : {a["faction"]} : {a["event"]} x {a["count"]} @ {a["ton"]/a["count"]:.0f}t {a["profit"]/a["ton"]:.0f}Cr/t {a["profit"]/1000000:.1f} MCr')
    elif a['profit'] != 0:
        print(
            f'{systems.name(a["sys"])} : {a["faction"]} : {a["event"]} x {a["count"]} total {a["profit"]/1000000:.1f} MCr')
    else:
        print(
            f'{systems.name(a["sys"])} : {a["faction"]} : {a["event"]} x {a["count"]}')
print('Done')
