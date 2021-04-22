import json
import csv
import os
from datetime import datetime
from Bubble import Bubble

import gzip
import pickle
import bz2



def SpanshDateTime(s):
    dformat = '%Y-%m-%d %H:%M:%S'  # so much grief from this function
    # eg '2020-04-18 05:45:26+00'
    return(datetime.strptime(s[:len(dformat) + 2], dformat))

def JournalDump(myfile,myarray): # Non-JSON File, each line is a JSON
    print(f'Saving {myfile}...')
    with open(myfile,'w') as rfile:
        for i in myarray:
            json.dump(i,rfile)
            rfile.write('\n')
    return None


def JournaliseRingScans():
    cspace = Bubble().systems
    print('Extract Scans to fakejournal')

    cutoffdate = SpanshDateTime('2020-06-09 07:00:00+00') # When Tritium was implemented
    rings = list()
    ringmaster = list()
    for sys in cspace:
        for body in sys['bodies']:
            for ring in body.get('rings',[]):
                ringmaster.append([ring['name'], sys['name'],f"{ring['type']} - Pristine", body['distanceToArrival']])        
                signals = list()
                if 'signals' in ring and cutoffdate < SpanshDateTime(ring['signals']['updateTime']): ## Updated Date/Time is here to ignore pre-Trit values
                    for signal in ring['signals']['signals'].items(): # Is a Dict, convert to a list
                        signals.append({'Type':signal[0], 'Count':signal[1]})
                    print(ring['name'])
                    rings.append({'event': 'SAASignalsFound', 'BodyName': ring['name'], 'type': f"{ring['type']} - Pristine", 'Signals':signals})

    with open('data\\bubble_canonn_rings.csv','w', newline = '') as rfile:
        writer = csv.writer(rfile)
        writer.writerows(ringmaster)

    JournalDump(f'{JFOLDER}\\fakejournal.log',rings)    # Write to ED Journal Folder
    JournalDump(f'data\\fakejournal.log',rings)         # Write to Local
    return None

def ReadNewSpanch(ifile='C:\Downloads\galaxy.json.gz'):
    # Reads a full Spansh dump, extracts all systems close to Canonn Space
    radius = 1000
    centre = {}
    rebuild = True
    
    print('Deep Thought...')
    nyes = nno = nnew = 0
    answer = list()
    
    with gzip.open(ifile,"r") as bstream:
        while True:
            l = bstream.readline().decode()
            t = l.rstrip('\n').rstrip(',')
            if len(t) > 6 != '':
                t = json.loads(t)
                d = max(abs(t['coords']['x']),abs(t['coords']['z']),abs(t['coords']['z']))
                if d <= radius:
                    nyes += 1
                    nnew += 1
                    print(f"New {t['date']} {t['name']}  {nnew:,}")
                    answer.append(t)
                else:
                    nno += 1
                    if nno % 500000 == 0:
                        print(f'... {nno:,}')
            if not l :
                break
        
        # dont put it there, even 500ly = 5GB
        #with open(f'C:\\Downloads\\spansh{radius}.pickle', 'wb') as io:
        #    pickle.dump(answer,io)

        with bz2.BZ2File(f'C:\\Downloads\\spansh{radius}.spickle', 'wb') as io:
            pickle.dump(answer,io)
    
        # strip out BGS Info
        for x in answer:
            if x['bodies']:
                x['bodies'] = None
            if 'population' in x and x['population']:
                x.pop('stations')
                x.pop('factions')
                x.pop('controllingFaction')
           
                x['stations'] = None
                x['factions'] = None
                x['controllingFaction'] = None
            else:
                x['population']=0

                

        with bz2.BZ2File(f'C:\\Downloads\\spansh{radius}map.spickle', 'wb') as io:
            pickle.dump(answer,io)


    return answer

if __name__ == '__main__':
    JFOLDER = os.environ.get('USERPROFILE') + f'\\Saved Games\\Frontier Developments\\Elite Dangerous'
    #JournaliseRingScans()
    ReadNewSpanch()

    radius = 500
    if False:
        print('Load')
        with open(f'C:\\Downloads\\spansh{radius}.pickle', 'rb') as io:
            answer = pickle.load(io)

        print('Save')
        with bz2.BZ2File(f'C:\\Downloads\\spansh{radius}.spickle', 'wb') as io:
            pickle.dump(answer,io)

        print('Load S')
        with bz2.BZ2File(f'C:\\Downloads\\spansh{radius}.spickle', 'rb') as io:
            answer = pickle.load(io)

    print('Done')

