#Google API
import pickle
import os.path
from typing import Type
import CSNSettings


from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# pylint: disable=no-member

#Traditional
import requests
import csv
import pygsheets
import json
from contextlib import closing

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']



def GoogleSheetService(): # Authorise and Return a sheet object to work on
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return(build('sheets', 'v4', credentials=creds))

def CSNOverRideReadSafe(): # Read without Google API
    answer = []
    answer.append(['System','Priority','Mission','Emoji','Type'])
    mysheet_id = CSNSettings.override_workbook
    if not mysheet_id:
        return(answer)
    readaction = f'export?format=csv&gid={CSNSettings.overide_sheet}'
    url = f'https://docs.google.com/spreadsheets/d/{mysheet_id}/{readaction}'
    with closing(requests.get(url, stream=True)) as r:
        reader = csv.reader(r.content.decode('utf-8').splitlines(), delimiter=',')
        next(reader)
        for row in reader:
            system, priority, Description, Emoji, Type = row
            if system != '':
                answer.append([system, int(priority), Description, Emoji, Type])
    return(answer)

def CSNOverRideRead():
    answer = []
    answer.append(['System','Priority','Mission'])
    mysheet_id = CSNSettings.override_workbook
    if not mysheet_id:
        return(answer)
    myrange = 'Overrides!A2:E'
    sheet = GoogleSheetService().spreadsheets()

    result = sheet.values().get(spreadsheetId=mysheet_id,
                                range=myrange).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            #print(row)
            system, priority, Description, Emoji, OType = row if len(row)==5 else row+[''] if len(row)==4 else row+['']+[''] if len(row)==3 else row+['']+['']+['']
            if system != '' and system[0] != '!':
                answer.append([system, int(priority), Description, Emoji, OType])
    return(answer)

def CSNSchedule(now = datetime.now().hour):
    answer = []
    if CSNSettings.override_workbook:
        mysheet_id = CSNSettings.override_workbook
        if not mysheet_id:
            return(answer)
        myrange = 'Overrides!F2:G25'
        sheet = GoogleSheetService().spreadsheets()

        result = sheet.values().get(spreadsheetId=mysheet_id,
                                    range=myrange).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
        else:
            for row in values:
                thour, task = row if len(row)==2 else row+['']  if len(row)==1 else row+['']+['']
                if task and int(thour[0:2])==now:
                    return task
    return None

def CSNFleetCarrierRead():
    '''
    Load list of registered BGS FC from CSNPatrol sheet
    '''
    answer = list()
    mysheet_id = CSNSettings.override_workbook
    if not mysheet_id:
        return(answer)
    myrange = 'FC!A2:D'
    sheet = GoogleSheetService().spreadsheets()

    result = sheet.values().get(spreadsheetId=mysheet_id,
                                range=myrange).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            #print(row)
            id, name, owner, role =  row if len(row)==4 else row+['']  if len(row)==3 else row+['']+['']
            if id != '':
                answer.append({'id':id, 'name':name, 'owner':owner, 'role':role})
    return(answer)

def CSNPatrolWrite(answer):
    mysheet_id = CSNSettings.override_workbook
    if not mysheet_id:
        return('No API')
    mysheet = 'CSNPatrol'
    sheet = GoogleSheetService().spreadsheets()


    # Datestamp my mayhem
    myrange = f'{mysheet}!H1'
    myvalue = [[datetime.now().ctime()]]
    result = sheet.values().update(spreadsheetId=mysheet_id,
                                range=myrange,
                                valueInputOption='USER_ENTERED',
                                body={'values':myvalue}                                
                                ).execute()


    #Clear in case the new patrol is shorted
    myrange = f'{mysheet}!A2:H'
    result = sheet.values().clear(spreadsheetId=mysheet_id, 
        range=myrange,
        body={}).execute()

    #Write the new patrol
    result = sheet.values().update(spreadsheetId=mysheet_id,
                                valueInputOption='RAW',
                                range=myrange,
                                body=dict(majorDimension='ROWS',
                                    values=answer)).execute()

    return(result["updatedRows"])

def CSNFactionname(faction_id,factions):
    factionmatch = list(filter(lambda x: x['id'] == faction_id, factions))
    return factionmatch[0]['name'] if len(factionmatch) > 0 else None

def CSNAttractions(cspace):
        
    print('.Loading Sheet')
    client = pygsheets.authorize()
    mysheet = 'Canonn Attractions'
    gDoc = client.open('CSNPatrol')
    gWorkSheet = gDoc.worksheet('title', mysheet)
    gSheet = gWorkSheet.get_all_records(head=1)

    print('.Load Factions ')
    url = 'https://eddb.io/archive/v6/factions.json'
    r = requests.get(url, allow_redirects=True)
    factions = json.loads(r.content)

    print('.Load Attractions')
    url = 'https://eddb.io/archive/v6/attractions.json'
    r = requests.get(url, allow_redirects=True)
    attractions = json.loads(r.content)

    # Sort
    print('.Preload')
    for attraction in attractions:
        matches = list(
            filter(lambda x: cspace[x]['eddb_id'] == attraction['system_id'], cspace))
        attraction['system_name'] = matches[0] if len(matches) > 0 else '!'
        if 'body_name' not in attraction or not attraction['body_name']:
            attraction['body_name'] = 'None'

    print('.Process')
    for attraction in attractions:
        if attraction['system_name'] != '!': # Is in a valid system 
            # Get Controlling Faction Name
            factionname = CSNFactionname(attraction['controlling_minor_faction_id'],factions) if attraction['controlling_minor_faction_id'] else None

            # Look for Attaction in Sheet
            found = False
            for ssline in gSheet:
                if ssline['System'] == attraction['system_name'] and ssline['Name'] == attraction['name']: # Update
                    if ssline['Body'] != attraction['body_name'] or ssline['Type'] != attraction['group_name'] or ssline['Inst Type'] != attraction['layout']['installation_type_name'] or ssline['Faction'] != factionname:
                        ssline['Body'] = attraction['body_name']
                        ssline['Type'] = attraction['group_name']
                        ssline['Inst Type'] = attraction['layout']['installation_type_name']
                        ssline['Faction'] = factionname
                    found = True
                    break
            if not found: # Add
                gSheet.append({'System': attraction['system_name'], 'Body': attraction['body_name'], 'Name': attraction['name'], 'Type': attraction['group_name'],
                           'Inst Type': attraction['layout']['installation_type_name'], 'Comments': '', 'Faction': factionname})

    # Add All Systems via a Nav Beacon (WAS and Stations)
    for i, x in enumerate(cspace):
        sys = cspace[x]
        navbs = list(filter(lambda x: x['System'] == sys['system_name'] and x['Name'] == 'Nav Beacon', gSheet))
        if len(navbs) == 0:
            print('Adding System')
            gSheet.append({'System': sys['system_name'], 'Body': sys['system_name'], 'Name': 'Nav Beacon', 'Type':'',
                           'Inst Type': '', 'Comments': '', 'Faction': ''})


    print('.Save Data')
    gSheet = sorted(gSheet, key=lambda x: x['System']+x['Body']+' !'+ x['Name'])
    post = list()
    for ssline in gSheet:
        post.append([ssline['System'], 
            ssline['Body'], 
            ssline['Name'], 
            ssline['Type'], 
            ssline['Inst Type'] if ssline['Inst Type'] else '', 
            ssline['Faction'] if ssline['Faction'] else '', 
            ssline['Comments']])

    gWorkSheet.update_values(f'A2:G{1+len(post)}', post)

    return None


def Test():
    return('No Test Configured')

if __name__ == '__main__':
    print(Test())
