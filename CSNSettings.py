try:
    import Keys_Canonn as keys # This file only available to authorised CSN Developers
except:
    import Keys_Client as keys # Populate this file with your settings


#Canonn Discord
wh_id = keys.wh_id
wh_token = keys.wh_token

#Canonn Google Sheet
override_workbook = keys.override_workbook
override_sheet = keys.override_sheet

factionnames = ['Canonn','Canonn Deep Space Research']