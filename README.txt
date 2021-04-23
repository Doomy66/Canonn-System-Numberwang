# Canonn-System-Numberwang
Various Tools to assist in BGS

# Libraries
api - All API Calls made from here
Bubble - Class for gathering your factions LIVE data
Overrides - Contains all the read/writes to Canonn Sheets
EDDBFramework - Class to access data from EDDB - Its NOT live data, upto 24 hours old, but can do heavy work without API traffic

# CSN 
CSNSetting - Settings for CSNAnalysis
CSNAnalysis - Will create a list of suggested actions to perform as CSN*.txt and CSN*.csv in the data folder.

# Utilities
Routeploter - Utility to provide quick routes around a selection of systems for data collection purposes
ExpansionTarget - Utilities to calculate which systems will expand to where - Both quick and dirty EDDB and slow but accurate EliteBGS
JournalInf - Reads your local Journals and lists all Inf related actions you have done since the last tick
DDDepartment - Utilities to monitor and identify usefull actions to defend your empire from rivals

# Odd Bits of R&D
JournalRings - A bit of niche project to post Ring Scans to a Canonn Sheet
Markets - Bit of a dead project to examine market prices - Never really had the correct data to do anything usefull
Spansh - Will process gigantic downloaded Spansh file for systems near your Empire. Not used it in ages.

# NB
Keys_Canonn.py - Not in GIT - It has keys to Canonn Sheets and Webhooks, use Keys_Client.py
Have a "data" subfolder to read/write json/csv/txt

# Release Notes
23/04/21 EDDBFramework gathers historic faction data from EBGS and caches it - Very API heavy until cache is estabilished.
            ExpansionTarget uses historic fation data to identify previous retreats.
            Spansh is currently a bit of a mess. Created basic map data to use for local puzzles, but the puzzle was solved before the code/01/03/21 ExpansionTarget now has InvasionRoute to calculate managed expansion between 2 systems
26/02/21 ExpansionTarget now also has EDDBFramework Options. Quicker, but not live data
26/02/21 ExpansionTarget : New Tool InvasionAlert will alert you to systems that are predicted to invade your territory
26/02/21 EDDBFramework Added
