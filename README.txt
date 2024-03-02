# Canonn-System-Numberwang
Various Tools to assist in BGS

# Root
    CSN.py : Generates all the Missions and send the results to providers
    CSNSchedule.py : Called on a Timed Event, looks at the schedule defined in a GoogleSheet, and performs the requested CSN task
    CSNSettings.py : Holds all the global variables and other settings read from your .env file
    .env.example : Rename to .env. Contains all your settings
    ExpandTest.py : Somewhere to play with the functions. Lots of tests/examples commented out to use.

#classes : Dataclasses used throughout
    BubbleExpansion.py is the interesting one. Will automatically calculate all expansions for all systems.

#data : CSN will save into a "data" folder. You may have to create this.

#providers: Interface modules to read from and write to external sources

#resources : some usefull resources consumed
    DiscordIcons : json file containing the Discord Icon tags to be used my Messages
    EDDBFactions.pickle and zip : An archive of Faction Information from EDDB before it died. Its is the most reliable source for Player Faction and Home System Information


# Release Notes
02/03/24 Totally Rewritten now I am not a total noob Python Wrangler. 
            Uses EDSM data as the main structure as it is much smaller than Spansh.
            Only uses live EBGS when the data is stale and is required.
            Recalculates Invasion/Expansion every time rather than on demand as it is now much quicker and uses fewer EBGS requests.
            Market type Missions not reimplemented, nobody seemed interested.
11/04/23 SpanchBGS replaces EDDBFramework which closed down. 
            Created archive of EDDBFactions.pickle as it is the only source of Native and home_system. Its in the root to avoid gitignore
            Happiness no longer available
            Thargoid Invaded systems now excluded from explansions
            For some unknown reason its a lot faster
23/04/21 EDDBFramework gathers historic faction data from EBGS and caches it - Very API heavy until cache is estabilished.
            ExpansionTarget uses historic fation data to identify previous retreats.
            Spansh is currently a bit of a mess. Created basic map data to use for local puzzles, but the puzzle was solved before the code
01/03/21 ExpansionTarget now has InvasionRoute to calculate managed expansion between 2 systems
26/02/21 ExpansionTarget now also has EDDBFramework Options. Quicker, but not live data
26/02/21 ExpansionTarget : New Tool InvasionAlert will alert you to systems that are predicted to invade your territory
26/02/21 EDDBFramework Added
