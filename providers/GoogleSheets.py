# Link to Canonn's Google Sheets
import pickle
import os.path
import CSNSettings

from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Traditional
import requests
import csv
from contextlib import closing

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def GoogleSheetService():  # Authorise and Return a sheet object to work on
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

    return (build('sheets', 'v4', credentials=creds))


def CSNOverRideReadSafe():  # Read without Google API
    answer = []
    answer.append(['System', 'Priority', 'Mission', 'Emoji', 'Type'])
    if not CSNSettings.OVERRIDE_WORKBOOK:
        return (answer)
    readaction = f'export?format=csv&gid={CSNSettings.overide_sheet}'
    url = f'https://docs.google.com/spreadsheets/d/{CSNSettings.OVERRIDE_WORKBOOK}/{readaction}'
    with closing(requests.get(url, stream=True)) as r:
        reader = csv.reader(r.content.decode(
            'utf-8').splitlines(), delimiter=',')
        next(reader)
        for row in reader:
            system, priority, Description, Emoji, Type = row
            if system != '':
                answer.append(
                    [system, int(priority), Description, Emoji, Type])
    return (answer)


def CSNOverRideRead():
    answer = []
    answer.append(['System', 'Priority', 'Mission'])
    if not CSNSettings.OVERRIDE_WORKBOOK:
        return (answer)
    myrange = 'Overrides!A2:E'
    sheet = GoogleSheetService().spreadsheets()

    result = sheet.values().get(spreadsheetId=CSNSettings.OVERRIDE_WORKBOOK,
                                range=myrange).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            # print(len(row))
            system, priority, Description, Emoji, OType = row if len(
                row) == 5 else row+[''] if len(row) == 4 else row+['']+[''] if len(row) == 3 else row+['']+['']+['']
            if system != '' and system[0] != '!':
                # blank priority now has a default and not fail to cast
                answer.append(
                    [system, int(priority) if priority else 1, Description, Emoji, OType])
    return (answer)


def CSNSchedule(now=datetime.utcnow().hour):
    answer = []
    if CSNSettings.OVERRIDE_WORKBOOK:
        mysheet_id = CSNSettings.OVERRIDE_WORKBOOK
        if not mysheet_id:
            return (answer)
        myrange = 'Overrides!F2:G25'
        sheet = GoogleSheetService().spreadsheets()

        result = sheet.values().get(spreadsheetId=mysheet_id,
                                    range=myrange).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
        else:
            for row in values:
                thour, task = row if len(
                    row) == 2 else row+[''] if len(row) == 1 else row+['']+['']
                if task and int(thour[0:2]) == now:
                    return task
    return None


def CSNFleetCarrierRead():
    '''
    Load list of registered BGS FC from CSNPatrol sheet
    '''
    answer = list()
    mysheet_id = CSNSettings.OVERRIDE_WORKBOOK
    if not mysheet_id:
        return (answer)
    myrange = 'FC!A2:D'
    sheet = GoogleSheetService().spreadsheets()

    result = sheet.values().get(spreadsheetId=mysheet_id,
                                range=myrange).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            # print(row)
            id, name, owner, role = row if len(
                row) == 4 else row+[''] if len(row) == 3 else row+['']+['']
            if id != '':
                answer.append(
                    {'id': id, 'name': name, 'owner': owner, 'role': role})
    return (answer)


def CSNPatrolWrite(answer):
    """System, X, Y, Z, TI=0, Faction=Canonn, Message, Icon"""
    """Col 285 Sector KZ-C b14-1	-133.21875	79.1875	-64.84375	0	Canonn	Suggestion: Canonn Missions, Bounties, Trade and Data (gap to Nones Resistance is 27.1%)	:chart_with_downwards_trend: """

    CSNSettings.OVERRIDE_WORKBOOK
    if not CSNSettings.OVERRIDE_WORKBOOK:
        CSNSettings.CSNLog.info('No Patrol Google Sheet defined')
        return ('No API')
    CSNSettings.CSNLog.info('Update Patrol on Google Sheet')
    mysheet = 'CSNPatrol'
    sheet = GoogleSheetService().spreadsheets()

    # Datestamp my mayhem
    myrange = f'{mysheet}!H1'
    myvalue = [[datetime.now().ctime()]]
    result = sheet.values().update(spreadsheetId=CSNSettings.OVERRIDE_WORKBOOK,
                                   range=myrange,
                                   valueInputOption='USER_ENTERED',
                                   body={'values': myvalue}
                                   ).execute()

    # Clear in case the new patrol is shorted
    myrange = f'{mysheet}!A2:H'
    result = sheet.values().clear(spreadsheetId=CSNSettings.OVERRIDE_WORKBOOK,
                                  range=myrange,
                                  body={}).execute()

    # Write the new patrol
    result = sheet.values().update(spreadsheetId=CSNSettings.OVERRIDE_WORKBOOK,
                                   valueInputOption='RAW',
                                   range=myrange,
                                   body=dict(majorDimension='ROWS',
                                             values=answer)).execute()

    return (result["updatedRows"])


def CSNFactionname(faction_id, factions):
    factionmatch = list(filter(lambda x: x['id'] == faction_id, factions))
    return factionmatch[0]['name'] if len(factionmatch) > 0 else None


def Test():
    return (CSNOverRideRead())


if __name__ == '__main__':
    pass
