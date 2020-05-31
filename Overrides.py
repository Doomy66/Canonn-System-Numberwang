#Google API
import pickle
import os.path
import CSNSettings
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# pylint: disable=no-member

#Traditional
import requests
import csv
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
    answer.append(['System','Priority','Mission'])
    mysheet_id = CSNSettings.override_workbook
    if mysheet_id == '':
        return(answer)
    readaction = f'export?format=csv&gid={CSNSettings.overide_sheet}'
    url = f'https://docs.google.com/spreadsheets/d/{mysheet_id}/{readaction}'
    with closing(requests.get(url, stream=True)) as r:
        reader = csv.reader(r.content.decode('utf-8').splitlines(), delimiter=',')
        next(reader)
        for row in reader:
            system, priority, Description = row
            if system != '':
                answer.append([system, int(priority), Description])
    return(answer)

def CSNOverRideRead():
    answer = []
    answer.append(['System','Priority','Mission'])
    mysheet_id = CSNSettings.override_workbook
    if mysheet_id == '':
        return(answer)
    myrange = 'Overrides!A2:C'
    sheet = GoogleSheetService().spreadsheets()

    result = sheet.values().get(spreadsheetId=mysheet_id,
                                range=myrange).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        for row in values:
            #print(row)
            system, priority, Description = row if len(row)==3 else row+['']
            if system != '':
                answer.append([system, int(priority), Description])
    return(answer)

def CSNPatrolWrite(answer):
    mysheet_id = CSNSettings.override_workbook
    mysheet = 'CSNPatrol'
    sheet = GoogleSheetService().spreadsheets()

    if mysheet_id == '':
        return('No API')

    # Datestamp my mayhem
    myrange = f'{mysheet}!H1'
    myvalue = [[datetime.now().ctime()]]
    result = sheet.values().update(spreadsheetId=mysheet_id,
                                range=myrange,
                                valueInputOption='USER_ENTERED',
                                body={'values':myvalue}                                
                                ).execute()


    #Clear in case the new patrol is shorted
    myrange = f'{mysheet}!A2:G'
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

def Test():
    return('No Test Configured')

if __name__ == '__main__':
    print(Test())
