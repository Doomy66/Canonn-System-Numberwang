# Canonn-System-Numberwang
Various Tools to assist in BGS

# Libraries
api - All API Calls made from here
Bubble - Class for gathering your factions LIVE data
Overrides - Contains all the read/writes to Canonn Sheets
EDDBFramework - Class to access data from EDDB - Its NOT live data, upto 24 hours old, but can do heavy work without API traffic

# CSN 
CSNSetting - Basic Settings for CSNAnalysis
CSNAnalysis - Very Canonn Specific - Will create a list of suggested orders, but lots of this read/writes to Canonn Sheets etc which you will not have access too. You will have to hack a lot out to get it to work, but worth it if you do

# Utilities
Routeploter - Utility to provide quick routes around a selection of systems for data collection purposes
ExpansionTarget - Utility to calculate which systems will expand to where - Currently uses a lot of EliteBGS API Calls
JournalInf - Lists all Inf related actions you have done since the last tick

# Odd Bits of R&D
JournalRings - A bit of niche project to post Ring Scans to a Canonn Sheet
Markets - Bit of a dead project to examine market prices - Never really had the correct data to do anything usefull
Spansh - Will process gigantic downloaded Spansh file for systems near your Empire. Not used it in ages.

# NB
Keys.py - Not in GIT - It has keys to Canonn Sheets and Webhooks

# Release Notes
26/02/21 EDDBFramework Added