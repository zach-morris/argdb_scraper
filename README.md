# argdb_scraper
 **A**nother **R**etro **G**ame **D**ata**B**ase scraper for retro game metadata written in python

# ARGDB Scraper Overview

This is a generalized scraper that I've created for some seperate retro gaming projects ([IAGL](https://github.com/zach-morris/plugin.program.iagl) and ARGDB (not yet published)).

I make no claims on how good or bad this is, and it's really made for a specific purpose.  It's likely not going to be modified for an out of scope project and it's not a production piece of software.  It's not perfect, but it's mine...

There are so many retro game scrapers and retro game databases out there.  Here's a small list of just some:

File / Dump Databases:
- [No-Intro](https://datomatic.no-intro.org/)
- [Goodtools](https://emulation.gametechwiki.com/index.php/GoodTools)
- [Redump](http://redump.org/)
- [TOSEC](https://www.tosecdev.org/)
- [MAME/FBNeo/CLR Generalized Format](http://www.progettosnaps.net/dats/)

Game Metadata Databases:
- [Arcade Italia](http://adb.arcadeitalia.net/) (Arcade)
- [Hyperspin](https://hyperlist.hyperspin-fe.com/) (Multi-System)
- [Launchbox](https://gamesdb.launchbox-app.com/) (Multi-System)
- [Libretro](https://github.com/libretro-thumbnails/libretro-thumbnails) (Multi-System, Images Only)
- [MobyGames](https://www.mobygames.com/) (Multi-System)
- [OVGDB](https://github.com/OpenVGDB/OpenVGDB/releases) (Multi-System)
- [Romhacking](http://www.romhacking.net/) (Multi-System, Focusing on Hacks)
- [TheGamesDB](https://thegamesdb.net/) (Multi-System)
- [IAGL](https://github.com/zach-morris/plugin.program.iagl) (Multi-System)
- [BillyC999](https://github.com/billyc999/Game-database-info) (Multi-System)
- [ScreenScraper](https://www.screenscraper.fr/) (Multi-System)

And thats just the ones most people are familiar with.  There are a _ton_ of them (If you have another good one I'm not aware of please let me know!).  

This is a tool just to make yet **A**nother game database.  The benefit of this **ARGDB** though will be that:
- The database is contained in just straight xml/json files (no fancy, yet slow API to deal with).  Client side scraping can be done by downloading one big file and parsing that for their rom set of 5000+ games, rather than hitting an API 5000 times.
- The database contains data from all the other ones (more is better?)
- The images are hosted in multiple locations

## How does it work
The scraper uses a swiss cheese kind of model.  Using all the metadata possible, we look for matching games by a specified key, if a match is found then the metadata is populated, if not hopefully a match is found in the next source.  The more sources we use the better our chances of finding a match and the maximum amount of metadata possible (which is the goal for ARGDB, to generate a static database file for each game with a conglomerate of metadata from each source)
![ARGDB Scraper Model](https://i.imgur.com/j7m25WY.png)

As a nice side effect, I've used this scraper to generate IAGL game xml files.  Thats likely what you'll use it for too.

One key part of the main scraper is that it does *not* pull metadata from the internet at runtime (I have other scripts that do that).  Pulling data from the net for a full game set as I'm sure you're aware is painfully slow.  The data for this scraper is all available locally, and in many cases already parsed into the correct format and saved as json cache.

## Requirements:
```
Python 3.x (3.7+ is probably best)
```
See requirements.txt for other python modules required, or use:
```
pip install -r ...path_to/requirements.txt
```

In addition, to upload this to github, several of the supporting files in dat_files_raw had to be compressed to be able to upload to github.  You'll need to unzip these files in order to use them in the tool.  You'll see a handy ```Unzip_these_files.txt``` file in the folder.  The goal though is for you to add your own files to the correct folder after having scoured the internet for that sweet sweet metadata.

## Example usage

Suggestion, see the example files provided and work from those.


Import the main scraper

```
from resources.lib.argdb_scraper import *
```

Next define the parsing settings and output settings

```
parsing_settings = {'logging':'debug', #Use 'debug' or 'info' based on how much log info you want on the progress
	'log_to_file':False, #For debugging purposes, logging to a file if necessary
	'concurrent_processes':3, #Not used yet
	'overwrite_locals':False, #For efficiency, overwrite local variables when running script, or reuse available local variables in memory
	'overwrite_conversions':False, #Saving the parsed file conversions can be saved and is usually not overwritten, this will override that
	'match_response':'query', #How to respond to match decisions:  best (highest ratio=default) or query (it will ask you to choose)
	'keep_no_matches':True, #If no match is found, return same game dict with no merged data.  If false, nothing will be added to the merged dict (i.e. the game will be thrown out)
	'fuzzy_match_ratio':90.9, #only consider fuzzy matches with at least this score.  In testing, I've found anything higher than 90 is a prety close match
	'fuzzy_scoring_type':'token_set_ratio', #scoring ratio to use, see fuzzywuzzy manual for the scoring methods
	'max_fuzzy_matches':5, #Max number of matches for a fuzzy match.  For query matching it will give you this many choices to look at
	'use_converted_files':True, #Use the converted version of the file if it already exists
	'common_platforms':['Nintendo Entertainment System'], #A common name for the platform your scraping
	}
output_settings = {'type':'IAGL', #Dat type to output.  This is currently the only option.  ARGDB will be added later
	'output_filename':'NES_Example', #Filename to output
	'header_name': 'Nintendo Entertainment System', #IAGL header will be populated with this
	'save_output':True, #Simple trigger to turn on and of file saving after parsing
	'author':'Zach Morris', #Author for the IAGL header
	'base_url':'https://archive.org/download/', #Base URL for the IAGL header
	}
```

Create your parsing utility class object

```
argdb_scraper = argdb_scraper(parsing_settings=parsing_settings,output_settings=output_settings)
```

Now we'll  define all the dats to pull from to gather the metadata with a dat info dict
```
dat_info = [{'type': xyz, #See list of types of dat files that are parsable above
	'filename': myfilename.xyz, #filename of the dat file 
	'platform':['all'], #Auto filter to a specific plaform or platforms from the dat file
	'save_conversion':True, #The parser will convert these dat files into a common format, if the conversion is saved then it can be reused without rescraping
	}]
```

Available dat_info Types:
```['1g1r_no_intro','CLR','IAGL','launchbox','MAME','OVGDB','arcade_italia','archive_org','billyc999','goodtools','hyperspin','image_json','libretro','maybe_intro','mobygames','no_intro','pickle_saves','progretto_snaps','romhacking_net','thegamesdb']```

Filenames for dat_info are provided by you, and define the source file for scraping.  The source files are located in their respecitve type folder:

```
...resources/dat_files_raw/type_folder_name/myfilename.xyz
```
e.g.

```
...resources/dat_files_raw/archive_org/NES_archive.xml
```

The platform filter in dat_info can be used to filter down the returned data to a particular platform or list of platforms.  Depending on the dat_info type, the platforms may be named differently:

```
# launchbox_possible_platforms
#['3DO Interactive Multiplayer','Commodore Amiga','Amstrad CPC','Android','Arcade','Atari 2600','Atari 5200','Atari 7800','Atari Jaguar','Atari Jaguar CD','Atari Lynx','Atari XEGS','ColecoVision','Commodore 64','Mattel Intellivision','Apple iOS','Apple Mac OS','Microsoft Xbox','Microsoft Xbox 360','Microsoft Xbox One','SNK Neo Geo Pocket','SNK Neo Geo Pocket Color','SNK Neo Geo AES','Nintendo 3DS','Nintendo 64','Nintendo DS','Nintendo Entertainment System','Nintendo Game Boy','Nintendo Game Boy Advance','Nintendo Game Boy Color','Nintendo GameCube','Nintendo Virtual Boy','Nintendo Wii','Nintendo Wii U','Ouya','Philips CD-i','Sega 32X','Sega CD','Sega Dreamcast','Sega Game Gear','Sega Genesis','Sega Master System','Sega Saturn','Sinclair ZX Spectrum','Sony Playstation','Sony Playstation 2','Sony Playstation 3','Sony Playstation 4','Sony Playstation Vita','Sony PSP','Super Nintendo Entertainment System','NEC TurboGrafx-16','WonderSwan','WonderSwan Color','Magnavox Odyssey 2','Fairchild Channel F','BBC Microcomputer System','Memotech MTX512','Camputers Lynx','Tiger Game.com','Oric Atmos','Acorn Electron','Dragon 32/64','Entex Adventure Vision','APF Imagination Machine','Mattel Aquarius','Jupiter Ace','SAM Coupé','Enterprise','EACA EG2000 Colour Genie','Acorn Archimedes','Tapwave Zodiac','Atari ST','Bally Astrocade','Magnavox Odyssey','Emerson Arcadia 2001','Sega SG-1000','Epoch Super Cassette Vision','Microsoft MSX','MS-DOS','Windows','Web Browser','Sega Model 2','Namco System 22','Sega Model 3','Sega System 32','Sega System 16','Sammy Atomiswave','Sega Naomi','Sega Naomi 2','Atari 800','Sega Model 1','Sega Pico','Acorn Atom','Amstrad GX4000','Apple II','Apple IIGS','Casio Loopy','Casio PV-1000','Coleco ADAM','Commodore 128','Commodore Amiga CD32','Commodore CDTV','Commodore Plus 4','Commodore VIC-20','Fujitsu FM Towns Marty','GCE Vectrex','Nuon','Mega Duck','Sharp X68000','Tandy TRS-80','Elektronika BK','Epoch Game Pocket Computer','Funtech Super Acan','GamePark GP32','Hartung Game Master','Interton VC 4000','MUGEN','OpenBOR','Philips VG 5000','Philips Videopac+','RCA Studio II','ScummVM','Sega Dreamcast VMU','Sega SC-3000','Sega ST-V','Sinclair ZX-81','Sord M5','Texas Instruments TI 99/4A','Touhou Project','Pinball','VTech CreatiVision','Watara Supervision','WoW Action Max','ZiNc','Nintendo Famicom Disk System','NEC PC-FX','PC Engine SuperGrafx','NEC TurboGrafx-CD','TRS-80 Color Computer','Nintendo Game & Watch','SNK Neo Geo CD','Nintendo Satellaview','Taito Type X','XaviXPORT','Mattel HyperScan','Game Wave Family Entertainment System','Sega CD 32X','Aamber Pegasus','Apogee BK-01','Commodore MAX Machine','Commodore PET','Exelvision EXL 100','Exidy Sorcerer','Fujitsu FM-7','Hector HRX','Lviv PC-01','Matra and Hachette Alice','Microsoft MSX2','Microsoft MSX2+','NEC PC-8801','NEC PC-9801','Nintendo 64DD','Nintendo Pokemon Mini','Othello Multivision','VTech Socrates','Vector-06C','Tomy Tutor','Spectravideo','Sony PSP Minis','Sony PocketStation','Sharp X1','Sharp MZ-2500','Sega Triforce','Sega Hikaru','Radio-86RK Mikrosha','SNK Neo Geo MVS','Nintendo Switch','Windows 3.X','Nokia N-Gage','XaviXPORT','Mattel HyperScan','GameWave','Taito Type X','Linux']
#Mobygames possible_platforms
#['Linux','DOS','Windows','PC Booter','Windows 3.x','PlayStation','PlayStation 2','Dreamcast','Nintendo 64','Game Boy','Game Boy Color','Game Boy Advance','Xbox','GameCube','SNES','Genesis','Jaguar','Lynx','Amiga','SEGA CD','SEGA 32X','NES','SEGA Saturn','Atari ST','Game Gear','SEGA Master System','Commodore 64','Atari 2600','ColecoVision','Intellivision','Apple II','N-Gage','Atari 5200','Atari 7800','3DO','Neo Geo','Vectrex','Virtual Boy','Atari 8-bit','TurboGrafx-16','ZX Spectrum','V.Smile','VIC-20','Nintendo DS','TurboGrafx CD','PSP','TI-99/4A','WonderSwan','WonderSwan Color','Game.Com','Apple IIgs','Neo Geo Pocket','Neo Geo Pocket Color','Neo Geo CD','Gizmondo','Amiga CD32','MSX','TRS-80','PC-FX','Amstrad CPC','Commodore 128','TRS-80 CoCo','BREW','J2ME','Palm OS','Windows Mobile','Symbian','Zodiac','Xbox 360','ExEn','Mophun','DoJa','CD-i','Macintosh','Odyssey','Channel F','Commodore PET/CBM','Odyssey 2','Dragon 32/64','iPod Classic','PlayStation 3','Wii','CDTV','Browser','Spectravideo','iPhone','Nintendo DSi','Zeebo','N-Gage (service)','BlackBerry','Android','BBC Micro','Electron','PC-88','PC-98','iPad','Microvision','Windows Phone','bada','webOS','Nintendo 3DS','FM Towns','SEGA Pico','Game Wave','PS Vita','Sharp X68000','Playdia','GP32','Supervision',"Super A'can",'Oric','Pippin','RCA Studio II','SG-1000','Commodore 16, Plus/4','Nuon','Acorn 32-bit','ZX80','ZX81','SAM Coupé','Sharp X1','GP2X','GP2X Wiz','Casio Loopy','Casio PV-1000','FM-7','SuperGrafx','Videopac+ G7400','Atom','Thomson TO','Sinclair QL','Wii U','Philips VG 5000','Sord M5','Mattel Aquarius','Amstrad PCW','Epoch Cassette Vision','Epoch Super Cassette Vision','Epoch Game Pocket Computer','Windows Apps','PlayStation 4','Xbox One','Arcade','Ouya','Kindle Classic','OS/2','Thomson MO','Memotech MTX','PC-6001','Tatung Einstein','Tomy Tutor','Pokémon Mini','Jupiter Ace','Camputers Lynx','GameStick','Coleco Adam','Maemo','MeeGo','Fire OS','Bally Astrocade','Enterprise','Arcadia 2001','LaserActive','VIS','BeOS','DVD Player','HD DVD Player','Blu-ray Disc Player','Z-machine','Hugo','TADS','Glulx','Timex Sinclair 2068','New Nintendo 3DS','Nascom','Exidy Sorcerer','NewBrain','Ohio Scientific','tvOS','watchOS','Sharp MZ-80K/700/800/1500','Sharp MZ-80B/2000/2500','Leapster','Didj','LeapFrog Explorer','LeapTV','digiBlast','ClickStart','V.Flash','Socrates','XaviXPORT','HyperScan','TRS-80 MC-10','Alice 32/90','Exelvision','Roku','Colour Genie','Compucolor II','Sol-20','Microbee','PC-8000','Sharp Zaurus','Nintendo Switch','Dedicated console','Dedicated handheld','Tizen','Newton','Mainframe','Terminal','Adventure Vision','Zune','CreatiVision','APF MP1000/Imagination Machine','VideoBrain','Arduboy','FRED/COSMAC','Wang 2200','Oculus Go','HP 9800','Tele-Spiel ES-2201','Interton Video 2000','Altair 8800','Tektronix 4050','Intel 8008','Intel 8080','KIM-1','Zilog Z80','SWTPC 6800','MRE','Pokitto','Bubble','Microtan 65','Telstar Arcade','HP Programmable Calculator','Motorola 6800','Galaksija','Amazon Alexa','Compucorp Programmable Calculator','TI Programmable Calculator','MOS Technology 6502','Astral 2000','SRI-500/1000','Compucolor I','Noval 760','Apple I','TIM','Jolt','Heathkit H11','Poly-88','IBM 5100','GIMINI','Ideal-Computer','1292 Advanced Programmable Video System','Xerox Alto','SC/MP','Tomahawk F1','GVM','GNEX','SK-VM','WIPI','CP/M','Heath/Zenith H8/H89','Tiki 100','Laser 200','Altair 680','North Star','SD-200/270/290','Freebox','ECD Micromind','Orao','Oculus Quest','Photo CD','SMC-777','Hitachi S1','Motorola 68k','Zilog Z8000','Compal 80','Signetics 2650']
#OVGDB possible_platforms
#['3DO Interactive Multiplayer','Arcade','Atari 2600','Atari 5200','Atari 7800','Atari Lynx','Atari Jaguar','Atari Jaguar CD','Bandai WonderSwan','Bandai WonderSwan Color','Coleco ColecoVision','GCE Vectrex','Intellivision','NEC PC Engine/TurboGrafx-16','NEC PC Engine CD/TurboGrafx-CD','NEC PC-FX','NEC SuperGrafx','Nintendo Famicom Disk System','Nintendo Game Boy','Nintendo Game Boy Advance','Nintendo Game Boy Color','Nintendo GameCube','Nintendo 64','Nintendo DS','Nintendo Entertainment System','Nintendo Super Nintendo Entertainment System','Nintendo Virtual Boy','Nintendo Wii','Sega 32X','Sega Game Gear','Sega Master System','Sega CD/Mega-CD','Sega Genesis/Mega Drive','Sega Saturn','Sega SG-1000','SNK Neo Geo Pocket','SNK Neo Geo Pocket Color','Sony PlayStation','Sony PlayStation Portable','Magnavox Odyssey2','Commodore 64','Microsoft MSX','Microsoft MSX2']
#thegamesdb possible_platforms
#['Neo Geo','3DO','Atari 5200','Atari 7800','Sega Game Gear','Sega CD','Atari 2600','Arcade','Atari Jaguar','Atari Jaguar CD','Nintendo Game Boy','Nintendo DS','Sony Playstation 2','Nintendo Entertainment System (NES)','Sony Playstation','Sony Playstation Portable','Sony Playstation 3','Microsoft Xbox 360','Microsoft Xbox','Famicom Disk System','Sega Dreamcast','SAM Coupé','Vectrex','Entex Adventure Vision','Pioneer LaserActive','Action Max','Sharp X1','Nintendo Switch','Nintendo 64','APF MP-1000','Bally Astrocade','RCA Studio II','Epoch Super Cassette Vision','Epoch Cassette Vision','Casio PV-1000','Emerson Arcadia 2001','Magnavox Odyssey 1','Tomy Tutor','Sony Playstation Vita','Nintendo Wii U','Sega 32X','Intellivision','Colecovision','Atari XE','Mac OS','Sega Mega Drive','Sega Master System','TurboGrafx 16','Sega Pico','Watara Supervision','Dragon 32/64','Texas Instruments TI-99/4A','Game &amp; Watch','Handheld Electronic Games (LCD)','Neo Geo CD','Nintendo Pokémon Mini','Acorn Electron','TurboGrafx CD','Commodore VIC-20','Acorn Archimedes','Amiga CD32','Commodore 128','TRS-80 Color Computer','Game.com','Atari 800','Apple II','SEGA SG-1000','Mega Duck','Nintendo GameCube','Super Nintendo (SNES)','PC-FX','Sharp X68000','FM Towns Marty','PC-88','PC-98','Nuon','Sega Saturn','Atari ST','N-Gage','Sega Genesis','Neo Geo Pocket Color','Neo Geo Pocket','Ouya','Microsoft Xbox One','Magnavox Odyssey 2','WonderSwan Color','WonderSwan','Atari Lynx','MSX','Fairchild Channel F','Commodore 64','Nintendo Game Boy Color','PC','Nintendo Game Boy Advance','Nintendo Wii','Nintendo Virtual Boy','Sony Playstation 4','Android','Philips CD-i','Amstrad CPC','iOS','Nintendo 3DS','Sinclair ZX Spectrum','Amiga']
```

Here's an example of a completed dat_info dict with 1 source file (that contains our game file URLS) and 12 metadata sources (that we'll try and find our game files in and then populate the metadata)

```
dat_info = [
	{'type': 'archive_org','filename':'MyGame_files.xml','platform':['all'],'save_conversion':True}, #0
	{'type': 'billyc999','filename':'Nintendo GameCube.xml','platform':['all'],'save_conversion':True}, #1
	{'type': 'goodtools','filename':'Atari - 2600.dat','platform':['all'],'save_conversion':True}, #2
	{'type': 'hyperspin','filename':'Commodore Amiga.xml','platform':['all'],'save_conversion':True}, #3
	{'type': 'IAGL','filename':'Sega_Saturn_ZachMorris.xml','platform':['all'],'save_conversion':True}, #4
	{'type': 'launchbox','filename':'Metadata.xml','platform':['all'],'save_conversion':True}, #5
	{'type': 'libretro','filename':'Nintendo - GameCube.xml','platform':['all'],'save_conversion':True}, #6
	{'type': 'MAME','filename':'MAME 0.217.dat','platform':['all'],'save_conversion':True}, #7
	{'type': 'progretto_snaps','filename':'MAME_217','platform':['all'],'save_conversion':True}, #8
	{'type': 'maybe_intro','filename':'Nintendo Super Famicom [T-En] (20121007).dat','platform':['all'],'save_conversion':True}, #9
	{'type': 'mobygames','filename':'mobygames_012020.json','platform':['all'],'save_conversion':True}, #10
	{'type': 'no_intro','filename':'Nintendo - Nintendo Entertainment System (20180911-151940).dat','platform':['all'],'save_conversion':True}, #11
	{'type': 'OVGDB','filename':'OpenVGDB 28.0.sqlite','platform':['all'],'save_conversion':True}, #12
	{'type': 'thegamesdb','filename':'dump_102419','platform':['all'],'save_conversion':True}, #13
	]
```

You can parse the dat files defined in dat_info, without any post processing using ```parse_input_file()```

Example of parsing all the files with one simple command:

```
raw_dat_files = [argdb_scraper.parse_input_file(x) for x in dat_info]
```

This command is helpful if you're just interested in seeing what is available in the source metadata files.

The raw dat file is not converted into a common format, it just spits out what the source data provides.  To merge the dat files together, we need to convert them into a common format for easier searching.  Convert the dat files using ```convert_input_file()```. 

```
converted_dat_files = [argdb_scraper.convert_input_file(x) for x in dat_info]
```

The converted_dat_files are the raw_dat_files with all the metadata moved into a common key/value combination based on the output_settings format (currently IAGL is the only format, different formats will eventually be added).

Now that our data is converted, we can merge our files using ```merge_dat_files()```.  The function takes the following arguments:

```
dat_file_merge_from=converted_dat_files[0],  #Which converted dat file should be used to merge data from
dat_file_merge_into=converted_dat_files[1],  #Which converted dat file should be used to merge data into i.e. converted_dat_files[0] -> converted_dat_files[1]
merge_indices=None, #Used to filter which game indices should be merged.  Typically used if you've already found an exact match and have moved onto fuzzy matches, see examples below
merge_settings={'match_type':['exact'], #Can be exact or fuzzy_automatic (i.e. no input required) or fuzzy_manual (ask you which match is best)
	'match_keys':['key1|key2'],  #the keys in the dat file to use for matching  dat_file_from_key|dat_file_into_key
	'keys_to_populate':['key1','key2','key3'],  #Which keys in the dat_file_from should be populated into the dat_file_into if they are not yet populated
	'keys_to_overwrite':None, #Which keys in the dat_file_from should be populated into the dat_file_into regardless if they are already populated or not, even if the dat_file_from data is None
	'keys_to_overwrite_if_populated':None,  #Only overwrite if the dat_file_from is not None
	'keys_to_append':None, #Will append data to make the metadata a list.  Typically you only want to do this for fields that can be lists (like genre or similar)
	}
```

Examples:
This command will merge converted_dat_files[0] into converted_dat_files[1] by exact matching converted_dat_files[0]['datafile']['game']['description'] with converted_dat_files[1]['datafile']['game']['@name'] and then populate boxart1,snapshot1 and snapshot2

```
my_new_dat_file = argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[0],dat_file_merge_into=converted_dat_files[1],merge_indices=None,merge_settings={'match_type':['exact'],'match_keys':['description|@name'],'keys_to_populate':['boxart1','snapshot1','snapshot2'],'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
```

This command will merge converted_dat_files[2] into my_new_dat_file (created above) by fuzzy_automatic matching converted_dat_files[2]['datafile']['game']['bookkeeping']['description_clean'] with my_new_dat_file1['datafile']['game']['bookkeeping']['description_clean'] and will skip any games that already had an exact match in my_new_dat_file and then populate boxart1,snapshot1 and snapshot2

```
my_new_dat_file2 = argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[2],dat_file_merge_into=my_new_dat_file,merge_indices=[ii for ii,x in enumerate(my_new_dat_file['datafile']['game']) if not x['bookkeeping']['exact_match']],merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['bookkeeping/description_clean|bookkeeping/description_clean'],'keys_to_populate':['boxart1','snapshot1','snapshot2'],'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
```

This command will merge converted_dat_files[3] into my_new_dat_file2 by fuzzy_manual matching converted_dat_files[3]['datafile']['game']['bookkeeping']['description_clean'] with my_new_dat_file2['datafile']['game']['bookkeeping']['description_clean'] and will skip any games that already had an exact or fuzzy match in my_new_dat_file2 and then populate boxart1,snapshot1 and snapshot2

```
my_new_dat_file3 = argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[3],dat_file_merge_into=my_new_dat_file2,merge_indices=[ii for ii,x in enumerate(my_new_dat_file2['datafile']['game']) if (not x['bookkeeping']['fuzzy_match'] and not x['bookkeeping']['exact_match'])],merge_settings={'match_type':['fuzzy_manual'],'match_keys':['bookkeeping/description_clean|bookkeeping/description_clean'],'keys_to_populate':['boxart1','snapshot1','snapshot2'],'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
```

Now save your work to a dat file:
```
success = argdb_scraper.output_dat_file(my_new_dat_file3,filename_in='My_Awesome_Game_List.xml',pop_these_keys_in=['bookkeeping','completed']) #Will generate an IAGL dat file and remove the bookkeeping stuff in my_new_dat_file3

```

Other commands of interest:

... to be added

## Examples

### 1.  Simplest example.  A list of three games with no metadata

Running the script [simple_example1.py](https://github.com/zach-morris/argdb_scraper/blob/main/simple_example1.py) will result in the xml output [NES_PD_GAMES.xml](https://github.com/zach-morris/argdb_scraper/blob/main/resources/output/NES_PD_GAMES.xml)

### 2.  Simple list of games, made up of only the URL you have for the source, then scrape against one metadata source for exact filename matches (OVGDB for example)

Running the script [simple_example2.py](https://github.com/zach-morris/argdb_scraper/blob/main/simple_example2.py) will result in the xml output [Arcade_3_Game_Example.xml](https://github.com/zach-morris/argdb_scraper/blob/main/resources/output/Arcade_3_Game_Example.xml)

### 3.  Same as #2 but iterate over several other sources of metadata

Running the script [simple_example3.py](https://github.com/zach-morris/argdb_scraper/blob/main/simple_example3.py) will result in the xml output [Arcade_3_Game_Example_2.xml](https://github.com/zach-morris/argdb_scraper/blob/main/resources/output/Arcade_3_Game_Example_2.xml)

### 4.  More complex list based on an archive.org source htm file, then scrape against multiple metadata sources for matches with various keys

Running the script [simple_example4.py](https://github.com/zach-morris/argdb_scraper/blob/main/simple_example4.py) will result in the xml output [Gen_Game_Example.xml](https://github.com/zach-morris/argdb_scraper/blob/main/resources/output/Gen_Game_Example.xml)


### Issues

This script is far from perfect.  You may run into some case where the tool gets hung up based on formatting of the data your working with.  Just track the bug down and squash it.  As I said at the top of the readme, this thing isn't perfect.