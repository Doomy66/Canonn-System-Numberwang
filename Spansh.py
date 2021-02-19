import json
import csv
import os
from datetime import datetime
from Bubble import Bubble


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

if __name__ == '__main__':
    JFOLDER = os.environ.get('USERPROFILE') + f'\\Saved Games\\Frontier Developments\\Elite Dangerous'
    JournaliseRingScans()
    print('Done')

