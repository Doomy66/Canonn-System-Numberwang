# Canonn-System-Numberwang
CSN will create a list of intructions for CMDRS to follow based on the current BGS State that benefit the Canonn Minor Faction.
It will report on Conflicts, Systems where we are not ye in control, Systems where we are dangerously low on Influence, Systems where the 2nd ranked faction is getting too close for comfort, and systems where data is out of date.

It does this by gathering data from EliteBGS API and comparing Inf levels and states of all factions in all systems that Canonn have a presence.
A list of Messages is generated, then output in various formats e.g:
 a) A local text file in Discord Freindly formating for manual copy/paste
 b) A Google Sheet via Google API. This sheet eventually feeds into EDMC Canonn Plugin. To disable this API, use the "/safe" argument

Lots of EliteBGS API Calls ! 260 at last count, due to EliteBGS not providing all the data required without calling an Endpoint for each foreign faction. To cut down on uncessary calls, there is an internal cache which is disabled with the "/new" argument.

CSNAnalysis.py	is the main file to run.
Overrides.py does the read/write to Google Sheets

Does not gather fresh EliteBGS API Data unless either:
 You pass "/new" as an argument
 It cannout find a Faction.json

Currently ran manually, but may be made to run automatically in the near future.

# Reports formatting and meaning
:dagger: [System]: Boost Canonn ... - indicates immediate threat, in most cases it needs the full arsenal of exploration data, Canonn bountie redeems, Missions and Trade.
:Salute2:  - indicates current BGS project, in most cases gaining a system or station for Canonn.
:chart_with_downwards_trend: [System] : Boost Canonn to crush the hopes of ...: - indicates always three systems, where Canonn could use some exploration data, bountie redeems, Missions and Trade. It's not critical, but appreciated.
:EliteEagle: and :ballot_box: - indicating a current conflict - War or Election - Canonn is fighting. Wars are mainly about Conflictzones, and Elections mainly about Missions. You'll also find a post what else can help Canonn winning.
:information_source:  and :canonn: - some kind of info Boffins deemed inportant enough to overwrite Numberwang.
:anchor: Locations of Canonns BGS fleetcarriers and those, who are currently supporting BGS work.
