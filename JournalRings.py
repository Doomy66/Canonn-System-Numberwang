import os
import time
import simplejson as json
import pygsheets

JFOLDER = os.environ.get('USERPROFILE') + \
    f'\\Saved Games\\Frontier Developments\\Elite Dangerous'


def isjfile(f):
    # Checks if a file is a Journal
    return os.path.isfile(JFOLDER+'\\'+f) and f.endswith('.log')

def jLoad(f): 
    global JFOLDER
    x = []
    with open(JFOLDER+'\\'+f, encoding="utf8") as io:
        for l in io:
            x.append(json.loads(l))
    return(x)

def ssrow(sheet,body): # Return the Sheet RowNumber to update
    try:
        return(2+next(i for i, n in enumerate(sheet) if n['Body'] == body))
    except:
        print(f'Unknown Body {body}')
        return(None)

if __name__ == '__main__':
    #Load Hotspot Spreadsheet
    print('.Loading Sheet')
    client = pygsheets.authorize()
    sh = client.open('Canonn Local Hotspot Survey')
    wks = sh.worksheet('title','Raw Data')
    #wks = sh.worksheet('title','TestImport')
    ss = wks.get_all_records(head=1)
    refs = []
    refs.append({'Type':'Icy - Pristine',
        'Alexandrite':'G',
        'Bromellite':'H', 
        'Grandidierite':'I', 
        'LowTemperatureDiamond':'J', 
        'Opal':'K', 
        'Tritium':'L'})
    refs.append({'Type':'Rocky - Pristine',
        'Alexandrite':'M',
        'Benitoite':'N', 
        'Monazite':'O', 
        'Musgravite':'P', 
        'Serendibite':'Q'})
    refs.append({'Type':'Metallic - Pristine',
        'Painite':'R',
        'Bertrandite':'S', 
        'Indite':'T', 
        'Gallite':'U',
        'Monazite':'V',
        'Platinum':'W', 
        'Rhodplumsite':'X', 
        'Serendibite':'Y'})
    refs.append({'Type':'Metal Rich - Pristine',
        'Monazite':'Z',
        'Painite':'AA', 
        'Platinum':'AB', 
        'Rhodplumsite':'AC', 
        'Serendibite':'AD'})


    print(f'.Scanning {JFOLDER}')
    dir = sorted(filter(lambda x: isjfile(x), os.listdir(JFOLDER)), reverse=True)
    dir = list(dir[:1])

    lastscanned = None

    try:
        while True:
            if os.path.getmtime(JFOLDER+'\\'+dir[0]) != lastscanned: # File Modify Date has changed
                lastscanned = os.path.getmtime(JFOLDER+'\\'+dir[0])
                print('.Processing')
                for f in dir:
                    j = jLoad(f)
                    for e in j:
                        if e['event'] == 'SAASignalsFound':
                            if 'Signals' in e:
                                nspots = 0
                                donetritium = False
                                #if e['BodyName'] == 'Cauan Tzu 1 A Ring':
                                #    print(e['BodyName'])
                                for signal in e['Signals']:
                                    if ('Type_Localised' not in signal) or (signal['Type_Localised'] not in {'Geological','Human'}):
                                        i = ssrow(ss,e['BodyName'])
                                        if i == None:
                                            print(f'!!! Failed {e["BodyName"]} {signal["Type"]}')
                                            # Cannot extend without knowing Ring Type - Not current available without a lot of API
                                            #ss.extend({'Body':e['BodyName'],'System':systems.name(e['SystemAddress']),'Type':'!!!!','Distance':0,'Notes':0})
                                            # Also Add Body to end of Spread Sheet
                                        else:
                                            btype = ss[i-2]['Type']
                                            if ss[i-2]['Notes'] == '': # Not already scanned
                                                mat = signal['Type']
                                                if mat == 'tritium':
                                                    mat = mat.capitalize()
                                                if mat != 'Tritium' or not donetritium:
                                                    if mat == 'Tritium':
                                                        donetritium = True 
                                                    for r in refs:
                                                        if r['Type'] == btype:
                                                            #print(f'{e["BodyName"]} : {mat} x {signal["Count"]}')
                                                            wks.update_value(f'{r[mat]}{i}',signal["Count"])
                                                            nspots += signal['Count']
                                                else:
                                                    print(f'... Tritium Clash {e["BodyName"]}')
                                if nspots != 0 and ss[i-2]['Notes'] == '' :
                                    print(f'{e["BodyName"]}')
                                    ss[i-2]['Notes'] = 'Scanned'
                                    if nspots == 1:
                                        wks.update_value(f'E{i}','.')    
                                    else:
                                        wks.update_value(f'E{i}',f'!Eyeball {nspots}')
                                    time.sleep(0.5)
                print('Scan Complete. Waiting...')
            time.sleep(1)
    except KeyboardInterrupt:
        SystemExit
    print('Done')
