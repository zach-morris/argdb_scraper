#Zach Morris
#Utilities for parsing dat files
import os, re, json, logging, time, itertools, six, zlib, io, html2text, sqlite3, glob
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections import OrderedDict
from unidecode import unidecode
from decimal import Decimal as round_dec
import concurrent.futures
import dateutil.parser as date_parser
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fuzzp
from urllib.parse import quote as url_quote
from urllib.parse import unquote as url_unquote
from lxml import etree as lxml_etree

try:
	basestring
except NameError:  # python3
	basestring = str

class argdb_scraper(object):
	def __init__(self,parsing_settings=None,output_settings=None):
		self.resources_path = os.path.join(os.getcwd(),'resources/')
		self.database_path = os.path.join(self.resources_path,'databases')
		self.dat_path_raw = os.path.join(self.database_path,'dat_files_raw')
		self.dat_path_converted = os.path.join(self.database_path,'dat_files_converted')
		self.log_path = os.path.join(self.resources_path,'logs')
		self.output_path = os.path.join(self.resources_path,'output')
		self.temp_path = os.path.join(self.resources_path,'temp')
		#Dat paths
		self.dat_paths = dict()
		self.dat_paths['type'] = ['1g1r_no_intro','CLR','IAGL','launchbox','MAME','OVGDB','arcade_italia','archive_org','billyc999','goodtools','hyperspin','image_json','libretro','maybe_intro','mobygames','no_intro','pickle_saves','progretto_snaps','romhacking_net','thegamesdb']
		self.dat_paths['parse_file_type'] = ['etree','clr','etree','etree','etree','sqlite','json','variable','etree','clr','etree','json','etree','etree','json','etree','json','custom_1','json','folder_json']
		self.dat_paths['raw_path'] = [os.path.join(self.dat_path_raw,x) for x in self.dat_paths['type']]
		self.dat_paths['converted_path'] = [os.path.join(self.dat_path_converted,x) for x in self.dat_paths['type']]
		self.clean_game_tags = re.compile(r'\([^)]*\)')
		self.clean_game_codes = re.compile(r'\[[^)]*\]')
		self.clean_alphanumeric = re.compile(r'([^\s\w]|_)+')
		self.archive_org_re1 = re.compile(r'<a href="(.*?)">(.*?)</a></td><td></td><td>(.*?)</td><td id="size">(.*?)</td></tr>') #url, #name, #time, #size
		self.archive_org_re2 = re.compile(r'<td><a href="(.*?)">(.*?)</a>(.*?)<a href="(.*?)">View Contents</a>(.*?)</td>\s+<td>(.*?)</td>\s+<td>(.*?)</td>')
		self.archive_org_re3 = re.compile(r'<a href="(.*?)">(.*?)</a><td><td>(.*?)<td id="size">(.*?)</tr>')
		self.ini_groups_re = re.compile('\[(.*?)\](.*?)\n\n',re.DOTALL)
		self.progretto_files_to_parse = ['history.dat','nplayers.ini','pS_AllProject_.*?.dat','series.ini','catver.ini','cabinets.ini','Players.ini','bestgames.ini','Working Arcade Clean.ini','Originals Arcade.ini','Clones Arcade.ini','freeplay.ini']
		self.progretto_media_types = ['artpreview','bosses','cabinets','covers','cpanel','devices','ends','flyers','gameover','howto','icons','logo','manuals','marquees','pcb','scores','select','snap','soundtrack','titles','versus','videosnaps','warning']
		self.progretto_media_urls = ['http://adb.arcadeitalia.net/media/mame.current/artworks_previews/','http://adb.arcadeitalia.net/media/mame.current/bosses/','http://adb.arcadeitalia.net/media/mame.current/cabinets/',None,'http://adb.arcadeitalia.net/media/mame.current/cpanels/','http://adb.arcadeitalia.net/media/mame.current/cabinets/','http://adb.arcadeitalia.net/media/mame.current/ends/','http://adb.arcadeitalia.net/media/mame.current/flyers/','http://adb.arcadeitalia.net/media/mame.current/gameovers/','http://adb.arcadeitalia.net/media/mame.current/howtos/','http://adb.arcadeitalia.net/media/mame.current/icons/','http://adb.arcadeitalia.net/media/mame.current/decals/','http://adb.arcadeitalia.net/download_file.php?tipo=mame_current&codice=XXXX&entity=manual&oper=view&filler=','http://adb.arcadeitalia.net/media/mame.current/marquees/','http://adb.arcadeitalia.net/media/mame.current/pcbs/','http://adb.arcadeitalia.net/media/mame.current/scores/','http://adb.arcadeitalia.net/media/mame.current/selects/','http://adb.arcadeitalia.net/media/mame.current/ingames/',None,'http://adb.arcadeitalia.net/media/mame.current/titles/','http://adb.arcadeitalia.net/media/mame.current/versus/','https://archive.org/download/MAME_0.185_VideoSnaps/MAME_0.185_VideoSnaps.zip/MAME%200.185%20VideoSnaps%2Fvideosnaps%2F','http://adb.arcadeitalia.net/media/mame.current/warnings/']
		self.flatten_list = lambda l: [item for sublist in l for item in sublist]
		self.clean_rom_tags = lambda l: str(l).upper() if l is not None and len(str(l))>0 else None
		self.IAGL_image_keys = self.flatten_list([['%(image_key)s%(ints)s'%{'ints':x,'image_key':y} for x in range(1,11)] for y in ['boxart','snapshot','fanart','banner','clearlogo']])
		self.IAGL_video_keys = ['videoid']
		self.mobygames_possible_platforms = ['Linux','DOS','Windows','PC Booter','Windows 3.x','PlayStation','PlayStation 2','Dreamcast','Nintendo 64','Game Boy','Game Boy Color','Game Boy Advance','Xbox','GameCube','SNES','Genesis','Jaguar','Lynx','Amiga','SEGA CD','SEGA 32X','NES','SEGA Saturn','Atari ST','Game Gear','SEGA Master System','Commodore 64','Atari 2600','ColecoVision','Intellivision','Apple II','N-Gage','Atari 5200','Atari 7800','3DO','Neo Geo','Vectrex','Virtual Boy','Atari 8-bit','TurboGrafx-16','ZX Spectrum','V.Smile','VIC-20','Nintendo DS','TurboGrafx CD','PSP','TI-99/4A','WonderSwan','WonderSwan Color','Game.Com','Apple IIgs','Neo Geo Pocket','Neo Geo Pocket Color','Neo Geo CD','Gizmondo','Amiga CD32','MSX','TRS-80','PC-FX','Amstrad CPC','Commodore 128','TRS-80 CoCo','BREW','J2ME','Palm OS','Windows Mobile','Symbian','Zodiac','Xbox 360','ExEn','Mophun','DoJa','CD-i','Macintosh','Odyssey','Channel F','Commodore PET/CBM','Odyssey 2','Dragon 32/64','iPod Classic','PlayStation 3','Wii','CDTV','Browser','Spectravideo','iPhone','Nintendo DSi','Zeebo','N-Gage (service)','BlackBerry','Android','BBC Micro','Electron','PC-88','PC-98','iPad','Microvision','Windows Phone','bada','webOS','Nintendo 3DS','FM Towns','SEGA Pico','Game Wave','PS Vita','Sharp X68000','Playdia','GP32','Supervision',"Super A'can",'Oric','Pippin','RCA Studio II','SG-1000','Commodore 16, Plus/4','Nuon','Acorn 32-bit','ZX80','ZX81','SAM Coupé','Sharp X1','GP2X','GP2X Wiz','Casio Loopy','Casio PV-1000','FM-7','SuperGrafx','Videopac+ G7400','Atom','Thomson TO','Sinclair QL','Wii U','Philips VG 5000','Sord M5','Mattel Aquarius','Amstrad PCW','Epoch Cassette Vision','Epoch Super Cassette Vision','Epoch Game Pocket Computer','Windows Apps','PlayStation 4','Xbox One','Arcade','Ouya','Kindle Classic','OS/2','Thomson MO','Memotech MTX','PC-6001','Tatung Einstein','Tomy Tutor','Pokémon Mini','Jupiter Ace','Camputers Lynx','GameStick','Coleco Adam','Maemo','MeeGo','Fire OS','Bally Astrocade','Enterprise','Arcadia 2001','LaserActive','VIS','BeOS','DVD Player','HD DVD Player','Blu-ray Disc Player','Z-machine','Hugo','TADS','Glulx','Timex Sinclair 2068','New Nintendo 3DS','Nascom','Exidy Sorcerer','NewBrain','Ohio Scientific','tvOS','watchOS','Sharp MZ-80K/700/800/1500','Sharp MZ-80B/2000/2500','Leapster','Didj','LeapFrog Explorer','LeapTV','digiBlast','ClickStart','V.Flash','Socrates','XaviXPORT','HyperScan','TRS-80 MC-10','Alice 32/90','Exelvision','Roku','Colour Genie','Compucolor II','Sol-20','Microbee','PC-8000','Sharp Zaurus','Nintendo Switch','Dedicated console','Dedicated handheld','Tizen','Newton','Mainframe','Terminal','Adventure Vision','Zune','CreatiVision','APF MP1000/Imagination Machine','VideoBrain','Arduboy','FRED/COSMAC','Wang 2200','Oculus Go','HP 9800','Tele-Spiel ES-2201','Interton Video 2000','Altair 8800','Tektronix 4050','Intel 8008','Intel 8080','KIM-1','Zilog Z80','SWTPC 6800','MRE','Pokitto','Bubble','Microtan 65','Telstar Arcade','HP Programmable Calculator','Motorola 6800','Galaksija','Amazon Alexa','Compucorp Programmable Calculator','TI Programmable Calculator','MOS Technology 6502','Astral 2000','SRI-500/1000','Compucolor I','Noval 760','Apple I','TIM','Jolt','Heathkit H11','Poly-88','IBM 5100','GIMINI','Ideal-Computer','1292 Advanced Programmable Video System','Xerox Alto','SC/MP','Tomahawk F1','GVM','GNEX','SK-VM','WIPI','CP/M','Heath/Zenith H8/H89','Tiki 100','Laser 200','Altair 680','North Star','SD-200/270/290','Freebox','ECD Micromind','Orao','Oculus Quest','Photo CD','SMC-777','Hitachi S1','Motorola 68k','Zilog Z8000','Compal 80','Signetics 2650']
		self.mobygames_possible_platforms_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278]
		self.thegamesdb_possible_platforms = ['Neo Geo','3DO','Atari 5200','Atari 7800','Sega Game Gear','Sega CD','Atari 2600','Arcade','Atari Jaguar','Atari Jaguar CD','Nintendo Game Boy','Nintendo DS','Sony Playstation 2','Nintendo Entertainment System (NES)','Sony Playstation','Sony Playstation Portable','Sony Playstation 3','Microsoft Xbox 360','Microsoft Xbox','Famicom Disk System','Sega Dreamcast','SAM Coupé','Vectrex','Entex Adventure Vision','Pioneer LaserActive','Action Max','Sharp X1','Nintendo Switch','Nintendo 64','APF MP-1000','Bally Astrocade','RCA Studio II','Epoch Super Cassette Vision','Epoch Cassette Vision','Casio PV-1000','Emerson Arcadia 2001','Magnavox Odyssey 1','Tomy Tutor','Sony Playstation Vita','Nintendo Wii U','Sega 32X','Intellivision','Colecovision','Atari XE','Mac OS','Sega Mega Drive','Sega Master System','TurboGrafx 16','Sega Pico','Watara Supervision','Dragon 32/64','Texas Instruments TI-99/4A','Game &amp; Watch','Handheld Electronic Games (LCD)','Neo Geo CD','Nintendo Pokémon Mini','Acorn Electron','TurboGrafx CD','Commodore VIC-20','Acorn Archimedes','Amiga CD32','Commodore 128','TRS-80 Color Computer','Game.com','Atari 800','Apple II','SEGA SG-1000','Mega Duck','Nintendo GameCube','Super Nintendo (SNES)','PC-FX','Sharp X68000','FM Towns Marty','PC-88','PC-98','Nuon','Sega Saturn','Atari ST','N-Gage','Sega Genesis','Neo Geo Pocket Color','Neo Geo Pocket','Ouya','Microsoft Xbox One','Magnavox Odyssey 2','WonderSwan Color','WonderSwan','Atari Lynx','MSX','Fairchild Channel F','Commodore 64','Nintendo Game Boy Color','PC','Nintendo Game Boy Advance','Nintendo Wii','Nintendo Virtual Boy','Sony Playstation 4','Android','Philips CD-i','Amstrad CPC','iOS','Nintendo 3DS','Sinclair ZX Spectrum','Amiga']
		self.thegamesdb_possible_platforms_ids = [24, 25, 26, 27, 20, 21, 22, 23, 28, 29, 4, 8, 11, 7, 10, 13, 12, 15, 14, 4936, 16, 4979, 4939, 4974, 4975, 4976, 4977, 4971, 3, 4969, 4968, 4967, 4966, 4965, 4964, 4963, 4961, 4960, 39, 38, 33, 32, 31, 30, 37, 36, 35, 34, 4958, 4959, 4952, 4953, 4950, 4951, 4956, 4957, 4954, 4955, 4945, 4944, 4947, 4946, 4941, 4940, 4943, 4942, 4949, 4948, 2, 6, 4930, 4931, 4932, 4933, 4934, 4935, 17, 4937, 4938, 18, 4923, 4922, 4921, 4920, 4927, 4926, 4925, 4924, 4929, 4928, 40, 41, 1, 5, 9, 4918, 4919, 4916, 4917, 4914, 4915, 4912, 4913, 4911]
		self.launchbox_possible_platforms = ['3DO Interactive Multiplayer','Commodore Amiga','Amstrad CPC','Android','Arcade','Atari 2600','Atari 5200','Atari 7800','Atari Jaguar','Atari Jaguar CD','Atari Lynx','Atari XEGS','ColecoVision','Commodore 64','Mattel Intellivision','Apple iOS','Apple Mac OS','Microsoft Xbox','Microsoft Xbox 360','Microsoft Xbox One','SNK Neo Geo Pocket','SNK Neo Geo Pocket Color','SNK Neo Geo AES','Nintendo 3DS','Nintendo 64','Nintendo DS','Nintendo Entertainment System','Nintendo Game Boy','Nintendo Game Boy Advance','Nintendo Game Boy Color','Nintendo GameCube','Nintendo Virtual Boy','Nintendo Wii','Nintendo Wii U','Ouya','Philips CD-i','Sega 32X','Sega CD','Sega Dreamcast','Sega Game Gear','Sega Genesis','Sega Master System','Sega Saturn','Sinclair ZX Spectrum','Sony Playstation','Sony Playstation 2','Sony Playstation 3','Sony Playstation 4','Sony Playstation Vita','Sony PSP','Super Nintendo Entertainment System','NEC TurboGrafx-16','WonderSwan','WonderSwan Color','Magnavox Odyssey 2','Fairchild Channel F','BBC Microcomputer System','Memotech MTX512','Camputers Lynx','Tiger Game.com','Oric Atmos','Acorn Electron','Dragon 32/64','Entex Adventure Vision','APF Imagination Machine','Mattel Aquarius','Jupiter Ace','SAM Coupé','Enterprise','EACA EG2000 Colour Genie','Acorn Archimedes','Tapwave Zodiac','Atari ST','Bally Astrocade','Magnavox Odyssey','Emerson Arcadia 2001','Sega SG-1000','Epoch Super Cassette Vision','Microsoft MSX','MS-DOS','Windows','Web Browser','Sega Model 2','Namco System 22','Sega Model 3','Sega System 32','Sega System 16','Sammy Atomiswave','Sega Naomi','Sega Naomi 2','Atari 800','Sega Model 1','Sega Pico','Acorn Atom','Amstrad GX4000','Apple II','Apple IIGS','Casio Loopy','Casio PV-1000','Coleco ADAM','Commodore 128','Commodore Amiga CD32','Commodore CDTV','Commodore Plus 4','Commodore VIC-20','Fujitsu FM Towns Marty','GCE Vectrex','Nuon','Mega Duck','Sharp X68000','Tandy TRS-80','Elektronika BK','Epoch Game Pocket Computer','Funtech Super Acan','GamePark GP32','Hartung Game Master','Interton VC 4000','MUGEN','OpenBOR','Philips VG 5000','Philips Videopac+','RCA Studio II','ScummVM','Sega Dreamcast VMU','Sega SC-3000','Sega ST-V','Sinclair ZX-81','Sord M5','Texas Instruments TI 99/4A','Touhou Project','Pinball','VTech CreatiVision','Watara Supervision','WoW Action Max','ZiNc','Nintendo Famicom Disk System','NEC PC-FX','PC Engine SuperGrafx','NEC TurboGrafx-CD','TRS-80 Color Computer','Nintendo Game & Watch','SNK Neo Geo CD','Nintendo Satellaview','Taito Type X','XaviXPORT','Mattel HyperScan','Game Wave Family Entertainment System','Sega CD 32X','Aamber Pegasus','Apogee BK-01','Commodore MAX Machine','Commodore PET','Exelvision EXL 100','Exidy Sorcerer','Fujitsu FM-7','Hector HRX','Lviv PC-01','Matra and Hachette Alice','Microsoft MSX2','Microsoft MSX2+','NEC PC-8801','NEC PC-9801','Nintendo 64DD','Nintendo Pokemon Mini','Othello Multivision','VTech Socrates','Vector-06C','Tomy Tutor','Spectravideo','Sony PSP Minis','Sony PocketStation','Sharp X1','Sharp MZ-2500','Sega Triforce','Sega Hikaru','Radio-86RK Mikrosha','SNK Neo Geo MVS','Nintendo Switch','Windows 3.X','Nokia N-Gage','XaviXPORT','Mattel HyperScan','GameWave','Taito Type X','Linux']
		self.OVGDB_possible_platforms = ['3DO Interactive Multiplayer','Arcade','Atari 2600','Atari 5200','Atari 7800','Atari Lynx','Atari Jaguar','Atari Jaguar CD','Bandai WonderSwan','Bandai WonderSwan Color','Coleco ColecoVision','GCE Vectrex','Intellivision','NEC PC Engine/TurboGrafx-16','NEC PC Engine CD/TurboGrafx-CD','NEC PC-FX','NEC SuperGrafx','Nintendo Famicom Disk System','Nintendo Game Boy','Nintendo Game Boy Advance','Nintendo Game Boy Color','Nintendo GameCube','Nintendo 64','Nintendo DS','Nintendo Entertainment System','Nintendo Super Nintendo Entertainment System','Nintendo Virtual Boy','Nintendo Wii','Sega 32X','Sega Game Gear','Sega Master System','Sega CD/Mega-CD','Sega Genesis/Mega Drive','Sega Saturn','Sega SG-1000','SNK Neo Geo Pocket','SNK Neo Geo Pocket Color','Sony PlayStation','Sony PlayStation Portable','Magnavox Odyssey2','Commodore 64','Microsoft MSX','Microsoft MSX2']
		self.OVGDB_image_keys = ['releaseCoverBack','releaseCoverCart','releaseCoverDisc','releaseCoverFront']
		self.ignore_releasedate_values = ['Canceled','TBA','Unknown','TBA 2013','Q4 2005','????','19??','197?','198?','199?','200?','20??','201?']+[str(x)+'?' for x in range(1970,2026)]
		self.merge_setting_keys = ['match_type','match_keys','keys_to_populate','keys_to_overwrite','keys_to_overwrite_if_populated','keys_to_append']
		self.fuzzy_scoring_type = {'WRatio':fuzz.WRatio, 'QRatio':fuzz.QRatio, 'token_set_ratio':fuzz.token_set_ratio, 'token_sort_ratio':fuzz.token_sort_ratio, 'partial_token_set_ratio':fuzz.partial_token_set_ratio, 'partial_token_sort_ratio':fuzz.partial_token_sort_ratio,'UWRatio':fuzz.UWRatio, 'UQRatio':fuzz.UQRatio} 
		self.list_to_string_keys = ['genre','groups']
		#Define parsing settings, set defaults if necessary
		if parsing_settings is not None:
			self.parsing_settings = parsing_settings
		else:
			self.parsing_settings = {'logging':'debug', #For debugging purposes, loglevel
									'log_to_file':False, #For debugging purposes, logging to a file
									'concurrent_processes':3, #Not used yet
									'overwrite_locals':False, #For efficiency, overwrite local variables when running script, or reuse available locals
									'overwrite_conversions':False, #If save conversion is true, but same file seems to already exist
									'match_response':'best', #How to respond to match decisions:  best (highest ratio=default) or query
									'keep_no_matches':True, #If not match is found, return same game dict with no merged data.  If false, nothing will be added to the merged dict
									'fuzzy_match_ratio':91.1, #only consider matches with at least this score.  In testing anything higher than 90 is a prety close match
									'fuzzy_scoring_type':'token_set_ratio', #scoring ratio to use
									'max_fuzzy_matches':5, #Max number of matches for a fuzzy match
									'use_converted_files':True, #Use the converted version of the file if it already exists
									'common_platforms':None,
									}
		#Define output settings, set defaults if necessary
		if output_settings is not None:
			self.output_settings = output_settings
		else:
			self.output_settings = {'type':'IAGL', #Dat type to output
									'output_filename':'IAGL_output', #Filename to output
									'header_name': 'IAGL',
									'save_output':True,
									'author':'Zach Morris', #Output options
									'base_url':'https://archive.org/download/', #Output options
									}
		#Setup logging
		logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
		self.rootLogger = logging.getLogger()
		if self.parsing_settings['logging'] == 'debug':
			self.rootLogger.setLevel(logging.DEBUG)
		else:
			self.rootLogger.setLevel(logging.INFO)
		consoleHandler = logging.StreamHandler()
		consoleHandler.setFormatter(logFormatter)
		if self.rootLogger.hasHandlers():
			self.rootLogger.handlers.clear()
		if self.parsing_settings['log_to_file']:
			fileHandler = logging.FileHandler("{0}/{1}.log".format(self.log_path, 'log'))
			fileHandler.setFormatter(logFormatter)
			self.rootLogger.addHandler(fileHandler)
		self.rootLogger.addHandler(consoleHandler)
		
		self.current_timestr = str(time.strftime('%d_%m_%Y',time.localtime()))
		self.xml_timestr = str(time.strftime('%d%m%Y',time.localtime()))
		self.lb_image_base = 'https://images.launchbox-app.com/'
		self.archive_org_url_base = 'https://archive.org/download/'
		self.html_escape_table = {"&": "&amp;",'"': "&quot;","'": "&apos;",">": "&gt;","<": "&lt;"}
		self.html_unescape_table = {"&amp;":"&","&quot;":'"',"&apos;":"'","&gt;":">","&lt;":"<"}
		self.unidecode_these_keys_in_xml = ['@name','description','groups','studio']
		self.html2text = html2text.HTML2Text()
		self.html2text.body_width=0
		self.html2text.ignore_links = True

	def get_new_datafile_bookkeeping_dict(self,parse_from=None,dat_info_in=None):
		dict_out = dict()
		if parse_from is not None and dat_info_in is not None:
			dict_out['filename'] = os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'])
			if os.path.isdir(dict_out['filename']):
				dict_out['file_crc'] = os.path.split(dict_out['filename'])[-1] #just use foldername for folders rather than crc of file
			else:
				dict_out['file_crc'] = get_crc32(dict_out['filename'])
			dict_out['type_from'] = dat_info_in['type']
			dict_out['type_to'] = self.output_settings['type']
			dict_out['conversion_date'] = self.current_timestr
		return dict_out

	def get_empty_datafile_bookkeeping_dict(self):
		dict_out = dict()
		dict_out['filename'] = ''
		dict_out['file_crc'] = ''
		dict_out['type_from'] = ''
		dict_out['type_to'] = ''
		dict_out['conversion_date'] = self.current_timestr
		return dict_out

	def get_new_merge_datafile_bookkeeping_dict(self,merge_from=None,merge_into=None,merge_settings=None):
		dict_out = dict()
		if merge_from is not None and merge_into is not None:
			dict_out['from_filename'] = merge_from['filename']
			dict_out['from_crc'] = merge_from['file_crc']
			dict_out['from_type'] = merge_from['type_to']
			dict_out['to_filename'] = merge_into['filename']
			dict_out['to_crc'] = merge_into['file_crc']
			dict_out['to_type'] = merge_into['type_to']
			#Copy these for future merges of merges
			dict_out['filename']= merge_into['filename']
			dict_out['file_crc'] = merge_into['file_crc']
			dict_out['type_to'] = merge_into['type_to']
			#Copy current merge settings
			dict_out['merge_setings'] = merge_settings
			dict_out['merge_date'] = self.current_timestr
		return dict_out

	def get_new_game_bookkeeping_dict(self,dict_in=None,database_id=None,wiki_url=None,database_platform=None,alt_name=None,alt_name_regions=None):
		dict_out = dict()
		if dict_out is not None:
			if dict_in['rom'] is not None and all([x.get('@name') is not None for x in dict_in['rom']]):
				dict_out['rom_ext'] = [self.get_rom_ext(url_unquote(x['@name'].split('/')[-1])) for x in dict_in['rom']]
				# dict_out['rom_ext'] = [x['@name'].split('.')[-1] if ('@name' in x.keys() and x['@name'] is not None and x['@name'][-4] == '.') else '' for x in dict_in['rom']]
				dict_out['rom_name_no_ext'] = [url_unquote(x['@name']).split('/')[-1].replace('.'+dict_out['rom_ext'][ii],'') for ii,x in enumerate(dict_in['rom']) if '@name' in x.keys() and x['@name'] is not None]
				dict_out['rom_ext'] = [x.lower() for x in dict_out['rom_ext']]
				if len(dict_out['rom_name_no_ext'])==1:
					dict_out['rom_tags'] = self.create_tags(dict_out['rom_name_no_ext'][0])
					dict_out['rom_codes'] = self.create_codes(dict_out['rom_name_no_ext'][0])
				elif len(dict_out['rom_name_no_ext'])>1:
					try:
						dict_out['rom_tags'] = self.flatten_list([self.create_tags(x) for x in dict_out['rom_name_no_ext']])
					except:
						dict_out['rom_tags'] = None
					try:
						dict_out['rom_codes'] = self.flatten_list([self.create_codes(x) for x in dict_out['rom_name_no_ext']])
					except:
						dict_out['rom_codes'] = None
				else:
					dict_out['rom_tags'] = None
					dict_out['rom_codes'] = None
				if len(dict_out['rom_name_no_ext']) == 0:
					dict_out['rom_name_no_ext'] = None
					dict_out['rom_ext'] = None
			else:
				dict_out['rom_name_no_ext'] = None
				dict_out['rom_ext'] = None
			if dict_in['description'] is not None:
				dict_out['description_clean'] = self.create_title_clean(dict_in['description'].replace('roms/','').replace('roms/',''))
				dict_out['description_search'] = self.create_title_search(dict_in['description'].replace('roms/',''))
				dict_out['description_tags'] = self.create_tags(dict_in['description'].replace('roms/',''))
				dict_out['description_codes'] = self.create_codes(dict_in['description'].replace('roms/',''))
			else:
				dict_out['description_clean'] = None
				dict_out['description_search'] = None
				dict_out['description_tags'] = None
				dict_out['description_codes'] = None	
		dict_out['alt_name'] = alt_name
		if alt_name is not None and type(alt_name) is list:
			dict_out['alt_name_clean'] = [self.create_title_clean(x) for x in alt_name]
			dict_out['alt_name_search'] = [self.create_title_search(x) for x in alt_name]
		else:
			dict_out['alt_name_clean'] = None
			dict_out['alt_name_search'] = None
		dict_out['alt_name_regions'] = alt_name_regions
		dict_out['matching_game_index'] = list()
		dict_out['exact_match'] = False
		dict_out['fuzzy_match'] = False
		dict_out['database_id'] = database_id
		dict_out['wiki_url'] = wiki_url
		dict_out['database_platform'] = database_platform
		return dict_out

	def get_new_IAGL_header_dict(self,emu_name=None,emu_description=None,emu_category=None,emu_version=None,emu_date=None,emu_author=None,emu_homepage=None,emu_baseurl=None):
		dict_out = dict()
		if emu_name is None:
			emu_name = self.output_settings['header_name']
		if emu_description is None:
			emu_description = self.output_settings['header_name']
		if emu_date is None:
			emu_date = self.xml_timestr
		if emu_author is None:
			emu_author = self.output_settings['author']
		if emu_baseurl is None:
			emu_baseurl = self.output_settings['base_url']
		if emu_category is None:
			emu_category = 'TBD'
		dict_out = {'emu_name': emu_name,
					'emu_description': emu_description,
					'emu_category': emu_category,
					'emu_version': emu_version,
					'emu_date': emu_date,
					'emu_author': emu_author,
					'emu_visibility': 'visible',
					'emu_homepage': emu_homepage,
					'emu_baseurl': emu_baseurl,
					'emu_launcher': 'retroplayer',
					'emu_default_addon': 'none',
					'emu_ext_launch_cmd': 'none',
					'emu_downloadpath': 'default',
					'emu_postdlaction': 'none',
					'emu_comment': 'TBD',
					'emu_thumb': 'TBD',
					'emu_banner': 'TBD',
					'emu_fanart': 'TBD',
					'emu_logo': 'TBD',
					'emu_trailer': 'TBD',}
		return dict_out

	def get_new_IAGL_rom_dict(self,rom_in=None,name=None,size=None,crc=None,md5=None,sha1=None):
		list_out = list()
		if rom_in is not None:
			if type(rom_in) is dict:
				if '@name' in rom_in.keys():
					list_out = [{'@name': rom_in['@name'],'@size': None,'@crc':None,'@md5':None,'@sha1':None}]
				else:
					list_out = [{'@name': None,'@size': None,'@crc':None,'@md5':None,'@sha1':None}]
				if '@size' in rom_in.keys():
					list_out[0]['@size'] = self.clean_rom_tags(rom_in['@size'])
				if 'size' in rom_in.keys():
					list_out[0]['@size'] = self.clean_rom_tags(rom_in['size'])
				if '@crc' in rom_in.keys():
					list_out[0]['@crc'] = self.clean_rom_tags(rom_in['@crc'])
				if '@md5' in rom_in.keys():
					list_out[0]['@md5'] = self.clean_rom_tags(rom_in['@md5'])
				if '@sha1' in rom_in.keys():
					list_out[0]['@sha1'] = self.clean_rom_tags(rom_in['@sha1'])
			elif type(rom_in) is list:
				for ii,rr in enumerate(rom_in):
					if '@name' in rr.keys():
						list_out.append({'@name': rr['@name'],'@size': None,'@crc':None,'@md5':None,'@sha1':None})
					else:
						list_out.append({'@name': None,'@size': None,'@crc':None,'@md5':None,'@sha1':None})
					if '@size' in rr.keys():
						list_out[ii]['@size'] = self.clean_rom_tags(rr['@size'])
					if 'size' in rr.keys():
						list_out[ii]['@size'] = self.clean_rom_tags(rr['size'])
					if '@crc' in rr.keys():
						list_out[ii]['@crc'] = self.clean_rom_tags(rr['@crc'])
					if '@md5' in rr.keys():
						list_out[ii]['@md5'] = self.clean_rom_tags(rr['@md5'])
					if '@sha1' in rr.keys():
						list_out[ii]['@sha1'] = self.clean_rom_tags(rr['@sha1'])
			else:
				list_out = [None]
		else:
			if name is not None:
				if type(name) is list:
					for nn in name:
						list_out.append([{'@name': nn,'@size': None,'@crc':None,'@md5':None,'@sha1':None}])
				else:
					list_out = [{'@name': name,'@size': None,'@crc':None,'@md5':None,'@sha1':None}]
			else:
				list_out = [{'@name': None,'@size': None,'@crc':None,'@md5':None,'@sha1':None}]
			if size is not None:
				if type(size) is list:
					for ii,ss in enumerate(size):
						list_out[ii]['@size'] = self.clean_rom_tags(ss)
				else:
					list_out[0]['@size'] = self.clean_rom_tags(ss)
			else:
				list_out[0]['@size'] = None
			if crc is not None:
				if type(crc) is list:
					for ii,ss in enumerate(crc):
						list_out[ii]['@crc'] = self.clean_rom_tags(ss)
				else:
					list_out[0]['@crc'] = self.clean_rom_tags(ss)
			else:
				list_out[0]['@crc'] = None
			if md5 is not None:
				if type(md5) is list:
					for ii,ss in enumerate(md5):
						list_out[ii]['@md5'] = self.clean_rom_tags(ss)
				else:
					list_out[0]['@md5'] = self.clean_rom_tags(ss)
			else:
				list_out[0]['@md5'] = None
			if sha1 is not None:
				if type(sha1) is list:
					for ii,ss in enumerate(sha1):
						list_out[ii]['@sha1'] = self.clean_rom_tags(ss)
				else:
					list_out[0]['@sha1'] = self.clean_rom_tags(ss)
			else:
				list_out[0]['@sha1'] = None

		return list_out

	def get_new_IAGL_game_dict(self,game_in=None,rom_in=None,name=None,description=None,nplayers=None,studio=None,releasedate=None,plot=None,genre=None,groups=None,videoid=None,year=None,rating=None,ESRB=None,perspective=None,emu_command=None,rom_override_postdl=None,rom_override_downloadpath=None,boxart1=None,boxart2=None,boxart3=None,boxart4=None,boxart5=None,boxart6=None,boxart7=None,boxart8=None,boxart9=None,boxart10=None,snapshot1=None,snapshot2=None,snapshot3=None,snapshot4=None,snapshot5=None,snapshot6=None,snapshot7=None,snapshot8=None,snapshot9=None,snapshot10=None,banner1=None,banner2=None,banner3=None,banner4=None,banner5=None,banner6=None,banner7=None,banner8=None,banner9=None,banner10=None,fanart1=None,fanart2=None,fanart3=None,fanart4=None,fanart5=None,fanart6=None,fanart7=None,fanart8=None,fanart9=None,fanart10=None,clearlogo1=None,clearlogo2=None,clearlogo3=None,clearlogo4=None,clearlogo5=None,clearlogo6=None,clearlogo7=None,clearlogo8=None,clearlogo9=None,clearlogo10=None,database_id=None,wiki_url=None,database_platform=None,alt_name=None,alt_name_regions=None):
		dict_out = dict()
		if rom_in is None:
			try:
				rom_in = game_in.get('rom')
			except:
				rom_in = None
		if name is None:
			try:
				name = game_in.get('@name')
			except:
				name = None
		if description is None:
			try:
				description = game_in.get('description')
			except:
				description = None
		if nplayers is None:
			try:
				nplayers = game_in.get('nplayers')
			except:
				nplayers = None
		if studio is None:
			try:
				studio = game_in.get('studio')
			except:
				studio = None
		if releasedate is None:
			try:
				releasedate = game_in.get('releasedate')
			except:
				releasedate = None
		if plot is None:
			try:
				plot = game_in.get('plot')
			except:
				plot = None
		if genre is None:
			try:
				genre = game_in.get('genre')
			except:
				genre = None
		if groups is None:
			try:
				groups = game_in.get('groups')
			except:
				groups = None
		if videoid is None:
			try:
				videoid = game_in.get('videoid')
			except:
				videoid = None
		if year is None:
			try:
				year = game_in.get('year')
			except:
				year = None
		if rating is None:
			try:
				rating = game_in.get('rating')
			except:
				rating = None
		if ESRB is None:
			try:
				ESRB = game_in.get('ESRB')
			except:
				ESRB = None
		if perspective is None:
			try:
				perspective = game_in.get('perspective')
			except:
				perspective = None
		if emu_command is None:
			try:
				emu_command = game_in.get('emu_command')
			except:
				emu_command = None
		if rom_override_postdl is None:
			try:
				rom_override_postdl = game_in.get('rom_override_postdl')
			except:
				rom_override_postdl = None
		if rom_override_downloadpath is None:
			try:
				rom_override_downloadpath = game_in.get('rom_override_downloadpath')
			except:
				rom_override_downloadpath = None
		if boxart1 is None:
			try:
				boxart1 = game_in.get('boxart1')
			except:
				boxart1 = None
		if boxart2 is None:
			try:
				boxart2 = game_in.get('boxart2')
			except:
				boxart2 = None
		if boxart3 is None:
			try:
				boxart3 = game_in.get('boxart3')
			except:
				boxart3 = None
		if boxart4 is None:
			try:
				boxart4 = game_in.get('boxart4')
			except:
				boxart4 = None
		if boxart5 is None:
			try:
				boxart5 = game_in.get('boxart5')
			except:
				boxart5 = None
		if boxart6 is None:
			try:
				boxart6 = game_in.get('boxart6')
			except:
				boxart6 = None
		if boxart7 is None:
			try:
				boxart7 = game_in.get('boxart7')
			except:
				boxart7 = None
		if boxart8 is None:
			try:
				boxart8 = game_in.get('boxart8')
			except:
				boxart8 = None				
		if boxart9 is None:
			try:
				boxart9 = game_in.get('boxart9')
			except:
				boxart9 = None
		if boxart10 is None:
			try:
				boxart10 = game_in.get('boxart10')
			except:
				boxart10 = None
		if snapshot1 is None:
			try:
				snapshot1 = game_in.get('snapshot1')
			except:
				snapshot1 = None
		if snapshot2 is None:
			try:
				snapshot2 = game_in.get('snapshot2')
			except:
				snapshot2 = None
		if snapshot3 is None:
			try:
				snapshot3 = game_in.get('snapshot3')
			except:
				snapshot3 = None
		if snapshot4 is None:
			try:
				snapshot4 = game_in.get('snapshot4')
			except:
				snapshot4 = None
		if snapshot5 is None:
			try:
				snapshot5 = game_in.get('snapshot5')
			except:
				snapshot5 = None
		if snapshot6 is None:
			try:
				snapshot6 = game_in.get('snapshot6')
			except:
				snapshot6 = None
		if snapshot7 is None:
			try:
				snapshot7 = game_in.get('snapshot7')
			except:
				snapshot7 = None
		if snapshot8 is None:
			try:
				snapshot8 = game_in.get('snapshot8')
			except:
				snapshot8 = None				
		if snapshot9 is None:
			try:
				snapshot9 = game_in.get('snapshot9')
			except:
				snapshot9 = None
		if snapshot10 is None:
			try:
				snapshot10 = game_in.get('snapshot10')
			except:
				snapshot10 = None
		if banner1 is None:
			try:
				banner1 = game_in.get('banner1')
			except:
				banner1 = None
		if banner2 is None:
			try:
				banner2 = game_in.get('banner2')
			except:
				banner2 = None
		if banner3 is None:
			try:
				banner3 = game_in.get('banner3')
			except:
				banner3 = None
		if banner4 is None:
			try:
				banner4 = game_in.get('banner4')
			except:
				banner4 = None
		if banner5 is None:
			try:
				banner5 = game_in.get('banner5')
			except:
				banner5 = None
		if banner6 is None:
			try:
				banner6 = game_in.get('banner6')
			except:
				banner6 = None
		if banner7 is None:
			try:
				banner7 = game_in.get('banner7')
			except:
				banner7 = None
		if banner8 is None:
			try:
				banner8 = game_in.get('banner8')
			except:
				banner8 = None				
		if banner9 is None:
			try:
				banner9 = game_in.get('banner9')
			except:
				banner9 = None
		if banner10 is None:
			try:
				banner10 = game_in.get('banner10')
			except:
				banner10 = None
		if fanart1 is None:
			try:
				fanart1 = game_in.get('fanart1')
			except:
				fanart1 = None
		if fanart2 is None:
			try:
				fanart2 = game_in.get('fanart2')
			except:
				fanart2 = None
		if fanart3 is None:
			try:
				fanart3 = game_in.get('fanart3')
			except:
				fanart3 = None
		if fanart4 is None:
			try:
				fanart4 = game_in.get('fanart4')
			except:
				fanart4 = None
		if fanart5 is None:
			try:
				fanart5 = game_in.get('fanart5')
			except:
				fanart5 = None
		if fanart6 is None:
			try:
				fanart6 = game_in.get('fanart6')
			except:
				fanart6 = None
		if fanart7 is None:
			try:
				fanart7 = game_in.get('fanart7')
			except:
				fanart7 = None
		if fanart8 is None:
			try:
				fanart8 = game_in.get('fanart8')
			except:
				fanart8 = None				
		if fanart9 is None:
			try:
				fanart9 = game_in.get('fanart9')
			except:
				fanart9 = None
		if fanart10 is None:
			try:
				fanart10 = game_in.get('fanart10')
			except:
				fanart10 = None
		if clearlogo1 is None:
			try:
				clearlogo1 = game_in.get('clearlogo1')
			except:
				clearlogo1 = None
		if clearlogo2 is None:
			try:
				clearlogo2 = game_in.get('clearlogo2')
			except:
				clearlogo2 = None
		if clearlogo3 is None:
			try:
				clearlogo3 = game_in.get('clearlogo3')
			except:
				clearlogo3 = None
		if clearlogo4 is None:
			try:
				clearlogo4 = game_in.get('clearlogo4')
			except:
				clearlogo4 = None
		if clearlogo5 is None:
			try:
				clearlogo5 = game_in.get('clearlogo5')
			except:
				clearlogo5 = None
		if clearlogo6 is None:
			try:
				clearlogo6 = game_in.get('clearlogo6')
			except:
				clearlogo6 = None
		if clearlogo7 is None:
			try:
				clearlogo7 = game_in.get('clearlogo7')
			except:
				clearlogo7 = None
		if clearlogo8 is None:
			try:
				clearlogo8 = game_in.get('clearlogo8')
			except:
				clearlogo8 = None				
		if clearlogo9 is None:
			try:
				clearlogo9 = game_in.get('clearlogo9')
			except:
				clearlogo9 = None
		if clearlogo10 is None:
			try:
				clearlogo10 = game_in.get('clearlogo10')
			except:
				clearlogo10 = None

		dict_out = {'@name': name,
					'description': description,
					'rom': self.get_new_IAGL_rom_dict(rom_in=rom_in),
					'rating': rating,
					'ESRB': self.clean_esrb(ESRB),
					'perspective':perspective,
					'studio': self.clean_company(studio),
					'releasedate': self.clean_releasedate(releasedate),
					'year': self.clean_releaseyear(year_in=year,releasedate_in=releasedate),
					'plot': self.clean_plot(plot),
					'genre': self.clean_genres(genre),
					'groups': groups,
					'nplayers':self.clean_nplayers(nplayers),
					'boxart1': boxart1,'boxart2': boxart2,'boxart3': boxart3,'boxart4': boxart4,'boxart5': boxart5,'boxart6': boxart6,'boxart7': boxart7,'boxart8': boxart8,'boxart9': boxart9,'boxart10': boxart10,
					'snapshot1': snapshot1,'snapshot2': snapshot2,'snapshot3': snapshot3,'snapshot4': snapshot4,'snapshot5': snapshot5,'snapshot6': snapshot6,'snapshot7': snapshot7,'snapshot8': snapshot8,'snapshot9': snapshot9,'snapshot10': snapshot10,
					'banner1': banner1,'banner2': banner2,'banner3': banner3,'banner4': banner4,'banner5': banner5,'banner6': banner6,'banner7': banner7,'banner8': banner8,'banner9': banner9,'banner10': banner10,
					'fanart1': fanart1,'fanart2': fanart2,'fanart3': fanart3,'fanart4': fanart4,'fanart5': fanart5,'fanart6': fanart6,'fanart7': fanart7,'fanart8': fanart8,'fanart9': fanart9,'fanart10': fanart10,
					'clearlogo1': clearlogo1,'clearlogo2': clearlogo2,'clearlogo3': clearlogo3,'clearlogo4': clearlogo4,'clearlogo5': clearlogo5,'clearlogo6': clearlogo6,'clearlogo7': clearlogo7,'clearlogo8': clearlogo8,'clearlogo9': clearlogo9,'clearlogo10': clearlogo10,
					'videoid':self.clean_videoid(videoid),
					'emu_command':emu_command,
					'rom_override_postdl':rom_override_postdl,
					'rom_override_downloadpath':rom_override_downloadpath,
					}
		dict_out['bookkeeping'] = self.get_new_game_bookkeeping_dict(dict_in=dict_out,database_id=database_id,wiki_url=wiki_url,database_platform=database_platform,alt_name=alt_name,alt_name_regions=alt_name_regions)
		return dict_out

	def get_save_conversion_filename(self,dat_info_in=None):
		filename_out = None
		if dat_info_in is not None:
			try:
				parse_from = self.dat_paths['type'][self.dat_paths['type'].index(dat_info_in['type'])] #Parse from type needs to be in class
			except:
				parse_from = None
			current_bookkeeping_dict = self.get_new_datafile_bookkeeping_dict(parse_from=parse_from,dat_info_in=dat_info_in)
			#Filename = outputtype_crc_platforms
			if current_bookkeeping_dict.get('file_crc') is not None:
				filename_out = self.output_settings['type']+'_'+current_bookkeeping_dict.get('file_crc')+'_'+'_'.join(dat_info_in['platform'])
				filename_out = filename_out.replace('__','_')+'.json'
			self.rootLogger.debug('Save conversion filename is %(filename_out)s for the file %(current_filename)s of type %(current_type)s'%{'filename_out': filename_out,'current_filename':os.path.split(dat_info_in['filename'])[-1],'current_type':dat_info_in['type']})
		return filename_out

	#Convert the dat file to a common type
	def convert_input_file(self,dat_info_in):
		current_save_filename = self.get_save_conversion_filename(dat_info_in=dat_info_in)
		self.rootLogger.info('Converting file %(filename)s of type %(type)s for platforms %(platform)s '%{'filename': os.path.split(dat_info_in['filename'])[-1],'type': dat_info_in['type'],'platform':','.join(dat_info_in['platform'])})
		
		if current_save_filename is None or not os.path.exists(os.path.join(self.dat_path_converted,current_save_filename)) or not self.parsing_settings['use_converted_files']:
			dat_file_parsed = self.parse_input_file(dat_info_in)

			if dat_file_parsed is not None:
				try:
					parse_from = self.dat_paths['type'][self.dat_paths['type'].index(dat_info_in['type'])] #Parse from type needs to be in class
					self.rootLogger.debug('DAT type to convert from %(parse_from)s'%{'parse_from': parse_from})
				except:
					parse_from = None
				if parse_from is not None:
					if self.output_settings['type'] == 'IAGL':
						dat_file_out = dict()
						dat_file_out['datafile'] = dict()
						dat_file_out['datafile']['bookkeeping'] = self.get_new_datafile_bookkeeping_dict(parse_from=parse_from,dat_info_in=dat_info_in)
						
						self.rootLogger.debug('DAT type to convert to %(type_in)s'%{'type_in': self.output_settings['type']})
						##Start here
						# ['','CLR','','launchbox','MAME','OVGDB','arcade_italia','archive_org','billyc999','goodtools','hyperspin','image_json','libretro','maybe_intro','mobygames','','pickle_saves','progretto_snaps','romhacking_net','thegamesdb']
						if parse_from == 'archive_org':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							if 'datafile' in dat_file_parsed.keys():
								for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name = gg.get('game').get('@name'),description=gg.get('description'),rom_in=gg.get('rom')))
							else:
								for ii,gg in enumerate(dat_file_parsed['files']['file']):
									if '@name2' in gg.keys(): #quote name if necessary
										current_rom_name = gg.get('@name2')
									else:
										current_rom_name = gg.get('@name')
									if gg.get('@name')[-4] == '.': #Ensure you're splitting the extension only
										current_description = gg.get('@name')[:-4]
									elif gg.get('@name') is not None and ('.7z' in gg.get('@name') or '.nkit' in gg.get('@name')):
										current_description = gg.get('@name').replace('.7z','').replace('.nkit','')
									else:
										current_description = gg.get('@name')
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name = current_description.split('/')[-1],description=current_description.split('/')[-1],rom_in={'@name': current_rom_name,'@size': gg.get('size'), '@md5': gg.get('md5'), '@crc': gg.get('crc32'), '@sha1': gg.get('sha1')}))
						elif parse_from == 'IAGL':
							dat_file_out['datafile']['header'] = dat_file_parsed['datafile']['header'] #Just straight copy the header
							dat_file_out['datafile']['game']=list()
							self.rootLogger.info('Found a total of %(num_items)s items in the IAGL dat file'%{'num_items': len(dat_file_parsed['datafile']['game'])})
							for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(game_in = gg))					
						elif parse_from == '1g1r_no_intro' or parse_from == 'no_intro' or parse_from == 'maybe_intro':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict(emu_version=dat_file_parsed['datafile']['header']['version'],emu_homepage='https://www.no-intro.org/')
							dat_file_out['datafile']['game']=list()
							if 'machine' in dat_file_parsed['datafile'].keys():
								self.rootLogger.info('Found a total of %(num_items)s items in the nointro dat file'%{'num_items': len(dat_file_parsed['datafile']['machine'])})
								for ii,gg in enumerate(dat_file_parsed['datafile']['machine']):
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(game_in = gg))
							else:
								self.rootLogger.info('Found a total of %(num_items)s items in the nointro dat file'%{'num_items': len(dat_file_parsed['datafile']['game'])})
								for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(game_in = gg))
						elif parse_from == 'libretro':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							self.rootLogger.info('Found a total of %(num_items)s items in the libretro dat file'%{'num_items': len(dat_file_parsed['datafile']['game'])})
							for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
								if 'image' in gg.keys():
									if type(gg['image']) is list:
										current_boxart1 = [x.get('@source')+x.get('@id')+'.'+x.get('@ext') for x in gg['image'] if x.get('@type') == 'Box - Front']
										current_snapshot1 = [x['@source']+x['@id']+'.'+x['@ext'] for x in gg['image'] if x['@type'] == 'Screenshot - Game Title']
										current_snapshot2 = [x['@source']+x['@id']+'.'+x['@ext'] for x in gg['image'] if x['@type'] == 'Screenshot - Gameplay']
										if len(current_boxart1) == 0:
											current_boxart1 = None
										if current_snapshot1 is None or len(current_snapshot1) == 0 and len(current_snapshot2)>0:
											current_snapshot1 = current_snapshot2
											current_snapshot2 = None
										elif len(current_snapshot1) == 0 and len(current_snapshot2) == 0:
											current_snapshot1 = None
										if current_snapshot2 is not None and len(current_snapshot2) == 0:
											current_snapshot2 = None
										if current_boxart1 is not None and len(current_boxart1)>0:
											current_boxart1 = current_boxart1[0]
										if current_snapshot1 is not None and len(current_snapshot1)>0:
											current_snapshot1 = current_snapshot1[0]
										if current_snapshot2 is not None and len(current_snapshot2)>0:
											current_snapshot2 = current_snapshot2[0]
									else:
										current_boxart1 = None
										current_snapshot1 = None
										current_snapshot2 = None
										if gg.get('image').get('@type') == 'Box - Front':
											current_boxart1 = gg.get('image').get('@source')+gg.get('image').get('@id')+'.'+gg.get('image').get('@ext')
										if gg.get('image').get('@type') == 'Screenshot - Game Title':
											current_snapshot1 = gg.get('image').get('@source')+gg.get('image').get('@id')+'.'+gg.get('image').get('@ext')
										if gg.get('image').get('@type') == 'Screenshot - Gameplay':
											current_snapshot2 = gg.get('image').get('@source')+gg.get('image').get('@id')+'.'+gg.get('image').get('@ext')
								else:
									current_boxart1 = None
									current_snapshot1 = None
									current_snapshot2 = None
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name = gg.get('@name'),description=gg.get('description'),boxart1=current_boxart1,snapshot1=current_snapshot1,snapshot2=current_snapshot2))
						elif parse_from == 'billyc999':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict(emu_name=dat_file_parsed['menu']['header']['listname'],emu_description=dat_file_parsed['menu']['header']['listname'])
							dat_file_out['datafile']['game']=list()
							self.rootLogger.info('Found a total of %(num_items)s items in the billyc999 dat file'%{'num_items': len(dat_file_parsed['menu']['game'])})
							for ii,gg in enumerate(dat_file_parsed['menu']['game']):
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name=gg.get('@name'),description=gg.get('description'),nplayers=gg.get('player'),studio=gg.get('manufacturer'),releasedate=None,plot=gg.get('story'),genre=gg.get('genre'),year=gg.get('year'),rating=gg.get('score'),ESRB=gg.get('rating')))
						elif parse_from == 'goodtools':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict(emu_name=dat_file_parsed['datafile']['header']['emu_name'],emu_description=dat_file_parsed['datafile']['header']['emu_description'],emu_version=dat_file_parsed['datafile']['header']['emu_version'],emu_author=dat_file_parsed['datafile']['header']['emu_author'],emu_homepage=dat_file_parsed['datafile']['header']['emu_homepage'])
							dat_file_out['datafile']['game']=list()
							self.rootLogger.info('Found a total of %(num_items)s items in the goodtools dat file'%{'num_items': len(dat_file_parsed['datafile']['game'])})
							for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(game_in = gg))
						elif parse_from == 'hyperspin':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict(emu_name=dat_file_parsed['menu'].get('header').get('listname'),emu_description=dat_file_parsed['menu'].get('header').get('listname'),emu_version=dat_file_parsed['menu'].get('header').get('listversion'),emu_date=dat_file_parsed['menu'].get('header').get('lastlistupdate'))
							dat_file_out['datafile']['game']=list()
							self.rootLogger.info('Found a total of %(num_items)s items in the hyperspin dat file'%{'num_items': len(dat_file_parsed['menu']['game'])})
							for ii,gg in enumerate(dat_file_parsed['menu']['game']):
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(rom_in={'@name':gg.get('@name'),'@crc':gg.get('crc')},name=gg.get('@name'),description=gg.get('description'),studio=gg.get('manufacturer'),genre=gg.get('genre'),year=gg.get('year'),ESRB=gg.get('rating')))
						elif parse_from == 'MAME':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict(emu_name=dat_file_parsed['datafile'].get('header').get('name'),emu_description=dat_file_parsed['datafile'].get('header').get('description'),emu_version=dat_file_parsed['datafile'].get('header').get('version'),emu_date=dat_file_parsed['datafile'].get('header').get('date'),emu_homepage=dat_file_parsed['datafile'].get('header').get('homepage'))
							dat_file_out['datafile']['game']=list()
							if 'machine' in dat_file_parsed['datafile'].keys():
								game_machine_key = 'machine'
							else:
								game_machine_key = 'game'
							self.rootLogger.info('Found a total of %(num_items)s items in the MAME dat file'%{'num_items': len(dat_file_parsed['datafile'][game_machine_key])})
							perc_len = [x for x in range(0,len(dat_file_parsed['datafile'][game_machine_key]),int(len(dat_file_parsed['datafile'][game_machine_key])/10))]
							for ii,gg in enumerate(dat_file_parsed['datafile'][game_machine_key]):
								if ii in perc_len:
									self.rootLogger.debug('MAME Parse: Percent Complete %(perc_comp)s'%{'perc_comp':int((100*ii)/perc_len[-1])})
								#Only list runnable games in list (bios files are added to required rom list per game if necessary)
								if gg.get('@runnable') != 'no' and gg.get('@isbios') != 'yes':
									roms_to_get = list(OrderedDict.fromkeys([gg.get(x) for x in ['@name','@cloneof','@romof'] if gg.get(x) is not None]))
									others_to_get = list(OrderedDict.fromkeys(self.flatten_list([[dat_file_parsed['datafile'][game_machine_key][z].get(x) for x in ['@name','@cloneof','@romof'] if dat_file_parsed['datafile'][game_machine_key][z].get(x) is not None] for z in [[a.get('@name') for a in dat_file_parsed['datafile'][game_machine_key]].index(y) for y in roms_to_get if y != '@name']])))
									all_roms_to_get = [{'@name':x+'.zip'} for x in list(OrderedDict.fromkeys(roms_to_get+others_to_get))]
									if gg.get('disk') is not None:
										if type(gg.get('disk')) is dict and gg.get('disk').get('@status') != 'nodump':
											all_roms_to_get.append({'@name':gg.get('disk').get('@name')+'.chd','@sha1':gg.get('disk').get('@sha1')})
										if type(gg.get('disk')) is list:
											for ggd in gg.get('disk'):
												all_roms_to_get.append({'@name':ggd.get('@name')+'.chd','@sha1':ggd.get('@sha1')})
										# else:
										# 	self.rootLogger.debug('Unknown type or no dump available for for MAME disk')
										# 	print(gg.get('disk'))
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(rom_in=all_roms_to_get,name=gg.get('@name'),description=gg.get('description'),studio=gg.get('manufacturer'),year=gg.get('year')))
						elif parse_from == 'OVGDB':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							#Filter game list
							full_list_len = len(dat_file_parsed['datafile']['game'])
							if dat_info_in['platform'] == ['all']:
								platforms_to_filter = self.OVGDB_possible_platforms
							else:
								platforms_to_filter = dat_info_in['platform']
							dat_file_parsed['datafile']['game'] = [x for x in dat_file_parsed['datafile']['game'] if x.get('rom').get('systemName') in platforms_to_filter]
							filtered_list_len = len(dat_file_parsed['datafile']['game'])
							self.rootLogger.info('OVGDB Parse:  List filtered from %(full_list)s games down to %(partial_list)s games'%{'full_list':full_list_len,'partial_list':filtered_list_len})
							for ii,gg in enumerate(dat_file_parsed['datafile']['game']):
								current_images = dict()
								current_images['boxart1'] = None
								current_images['boxart2'] = None
								current_images['boxart3'] = None
								current_images['boxart4'] = None
								ct=0
								for kk in self.OVGDB_image_keys:
									if gg.get(kk) is not None:
										ct=ct+1
										current_images['boxart'+str(ct)] = gg.get(kk)
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(rom_in={'@name':gg.get('rom').get('romFileName'),'@size':gg.get('rom').get('romSize'),'@crc':gg.get('rom').get('romHashCRC'),'@md5':gg.get('rom').get('romHashMD5'),'@sha1':gg.get('rom').get('romHashSHA1')},name=gg.get('rom').get('romExtensionlessFileName'),description=gg.get('releaseTitleName'),studio=gg.get('releaseDeveloper'),releasedate=gg.get('releaseDate'),plot=gg.get('releaseDescription'),genre=gg.get('releaseGenre'),year=gg.get('releaseDate'),database_id=gg.get('releaseID'),wiki_url=gg.get('releaseReferenceURL'),database_platform=gg.get('rom').get('systemName'),alt_name_regions=gg.get('rom').get('regionName'),boxart1=current_images['boxart1'],boxart2=current_images['boxart2'],boxart3=current_images['boxart3'],boxart4=current_images['boxart4']))
						elif parse_from == 'launchbox':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							#Filter game list
							full_list_len = len(dat_file_parsed['LaunchBox']['Game'])
							if dat_info_in['platform'] == ['all']:
								platforms_to_filter = self.launchbox_possible_platforms
							else:
								platforms_to_filter = dat_info_in['platform']
							dat_file_parsed['LaunchBox']['Game'] = [x for x in dat_file_parsed['LaunchBox']['Game'] if x.get('Platform') in platforms_to_filter]
							filtered_list_len = len(dat_file_parsed['LaunchBox']['Game'])
							self.rootLogger.info('Launchbox Parse:  List filtered from %(full_list)s games down to %(partial_list)s games'%{'full_list':full_list_len,'partial_list':filtered_list_len})
							perc_len = [x for x in range(0,len(dat_file_parsed['LaunchBox']['Game']),int(len(dat_file_parsed['LaunchBox']['Game'])/10))]
							for ii,gg in enumerate(dat_file_parsed['LaunchBox']['Game']):
								if ii in perc_len:
									self.rootLogger.debug('Launchbox Parse: Percent Complete %(perc_comp)s'%{'perc_comp':int((100*ii)/perc_len[-1])})
								if gg.get('DatabaseID') is not None:
									current_alternate_names = self.get_launchbox_alt_name_dict([x for x in dat_file_parsed['LaunchBox']['GameAlternateName'] if x['DatabaseID'] == gg.get('DatabaseID')])
									current_images =  self.get_launchbox_images_dict([x for x in dat_file_parsed['LaunchBox']['GameImage'] if x['DatabaseID'] == gg.get('DatabaseID')])
								if gg.get('MaxPlayers') is not None and gg.get('Cooperative') == 'true':
									 current_nplayers = gg.get('MaxPlayers')+' Co-Op'
								else:
									current_nplayers = gg.get('MaxPlayers')
								if gg.get('Genres') is not None and ';' in gg.get('Genres'):
									 current_genre = ','.join([x.strip() for x in gg.get('Genres').split(';')])
								else:
									current_genre = gg.get('Genres')
								if gg.get('CommunityRating') is not None:
									 current_rating = str(round_dec(gg.get('CommunityRating')).quantize(round_dec('.01')))
								else:
									current_rating = gg.get('CommunityRating')
								if gg.get('VideoURL') is not None:
									 current_videoid = gg.get('VideoURL').split('v=')[-1]
								else:
									current_videoid = gg.get('VideoURL')
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name=gg.get('Name'),description=gg.get('Name'),nplayers=current_nplayers,studio=gg.get('Publisher'),releasedate=gg.get('ReleaseDate'),plot=gg.get('Overview'),genre=current_genre,videoid=current_videoid,year=gg.get('ReleaseYear'),rating=current_rating,ESRB=gg.get('ESRB'),database_id=gg.get('DatabaseID'),wiki_url=gg.get('WikipediaURL'),database_platform=gg.get('Platform'),boxart1=current_images['boxart1'],boxart2=current_images['boxart2'],boxart3=current_images['boxart3'],boxart4=current_images['boxart4'],boxart5=current_images['boxart5'],boxart6=current_images['boxart6'],boxart7=current_images['boxart7'],boxart8=current_images['boxart8'],boxart9=current_images['boxart9'],boxart10=current_images['boxart10'],snapshot1=current_images['snapshot1'],snapshot2=current_images['snapshot2'],snapshot3=current_images['snapshot3'],snapshot4=current_images['snapshot4'],snapshot5=current_images['snapshot5'],snapshot6=current_images['snapshot6'],snapshot7=current_images['snapshot7'],snapshot8=current_images['snapshot8'],snapshot9=current_images['snapshot9'],snapshot10=current_images['snapshot10'],banner1=current_images['banner1'],banner2=current_images['banner2'],banner3=current_images['banner3'],banner4=current_images['banner4'],banner5=current_images['banner5'],banner6=current_images['banner6'],banner7=current_images['banner7'],banner8=current_images['banner8'],banner9=current_images['banner9'],banner10=current_images['banner10'],fanart1=current_images['fanart1'],fanart2=current_images['fanart2'],fanart3=current_images['fanart3'],fanart4=current_images['fanart4'],fanart5=current_images['fanart5'],fanart6=current_images['fanart6'],fanart7=current_images['fanart7'],fanart8=current_images['fanart8'],fanart9=current_images['fanart9'],fanart10=current_images['fanart10'],clearlogo1=current_images['clearlogo1'],clearlogo2=current_images['clearlogo2'],clearlogo3=current_images['clearlogo3'],clearlogo4=current_images['clearlogo4'],clearlogo5=current_images['clearlogo5'],clearlogo6=current_images['clearlogo6'],clearlogo7=current_images['clearlogo7'],clearlogo8=current_images['clearlogo8'],clearlogo9=current_images['clearlogo9'],clearlogo10=current_images['clearlogo10'],alt_name=current_alternate_names['alt_name'],alt_name_regions=current_alternate_names['alt_name_regions']))
						elif parse_from == 'mobygames':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							full_list_len = len(dat_file_parsed['games'])
							if dat_info_in['platform'] == ['all']:
								platforms_to_filter = self.mobygames_possible_platforms_ids
							else:
								platforms_to_filter = [self.mobygames_possible_platforms_ids[self.mobygames_possible_platforms.index(x)] for x in dat_info_in['platform']]
							dat_file_parsed['games'] = [x for x in dat_file_parsed['games'] if any([y.get('platform_id') in platforms_to_filter for y in x.get('platforms')])]
							filtered_list_len = len(dat_file_parsed['games'])
							self.rootLogger.info('Mobygames Parse:  List filtered from %(full_list)s games down to %(partial_list)s games'%{'full_list':full_list_len,'partial_list':filtered_list_len})
							perc_len = [x for x in range(0,len(dat_file_parsed['games']),int(len(dat_file_parsed['games'])/10))]
							for ii,gg in enumerate(dat_file_parsed['games']):
								if ii in perc_len:
									self.rootLogger.debug('Mobygames Parse: Percent Complete %(perc_comp)s'%{'perc_comp':int((100*ii)/perc_len[-1])})
								if gg.get('game_id') is not None:
									current_groups = ','.join([x['group_name'].replace(', The','').replace(', the','').replace('Botany, farming, gardening','Botany/Farming/Gardening').replace(', ',' ').replace(',','') for x in dat_file_parsed['groups'] if gg.get('game_id') in x['game_ids']])
								else:
									current_groups = None
								if gg.get('genres') is not None:
									current_genres = ','.join(x.get('genre_name').replace(', ',' ').replace(',','').strip() for x in gg.get('genres'))
								else:
									current_genres = None
								if gg.get('moby_score') is not None:
									current_score = str(gg.get('moby_score'))
								else:
									current_score = None
								if gg.get('platforms') is not None and len(gg.get('platforms'))>0:
									current_platform = [x.get('platform_name') for x in gg.get('platforms')]
								else:
									current_platform = None
								if gg.get('sample_cover') is not None or gg.get('sample_screenshots') is not None:
									current_images =  self.get_mobygames_images_dict(covers_in=gg.get('sample_cover'),screenshots_in=gg.get('sample_screenshots'))

								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name=gg.get('title'),description=gg.get('title'),plot=gg.get('description'),genre=current_genres,groups=current_groups,rating=current_score,wiki_url=gg.get('moby_url'),database_id=str(gg.get('game_id')),database_platform=current_platform,boxart1=current_images['boxart1'],boxart2=current_images['boxart2'],boxart3=current_images['boxart3'],boxart4=current_images['boxart4'],boxart5=current_images['boxart5'],boxart6=current_images['boxart6'],boxart7=current_images['boxart7'],boxart8=current_images['boxart8'],boxart9=current_images['boxart9'],boxart10=current_images['boxart10'],snapshot1=current_images['snapshot1'],snapshot2=current_images['snapshot2'],snapshot3=current_images['snapshot3'],snapshot4=current_images['snapshot4'],snapshot5=current_images['snapshot5'],snapshot6=current_images['snapshot6'],snapshot7=current_images['snapshot7'],snapshot8=current_images['snapshot8'],snapshot9=current_images['snapshot9'],snapshot10=current_images['snapshot10'],banner1=current_images['banner1'],banner2=current_images['banner2'],banner3=current_images['banner3'],banner4=current_images['banner4'],banner5=current_images['banner5'],banner6=current_images['banner6'],banner7=current_images['banner7'],banner8=current_images['banner8'],banner9=current_images['banner9'],banner10=current_images['banner10'],fanart1=current_images['fanart1'],fanart2=current_images['fanart2'],fanart3=current_images['fanart3'],fanart4=current_images['fanart4'],fanart5=current_images['fanart5'],fanart6=current_images['fanart6'],fanart7=current_images['fanart7'],fanart8=current_images['fanart8'],fanart9=current_images['fanart9'],fanart10=current_images['fanart10'],clearlogo1=current_images['clearlogo1'],clearlogo2=current_images['clearlogo2'],clearlogo3=current_images['clearlogo3'],clearlogo4=current_images['clearlogo4'],clearlogo5=current_images['clearlogo5'],clearlogo6=current_images['clearlogo6'],clearlogo7=current_images['clearlogo7'],clearlogo8=current_images['clearlogo8'],clearlogo9=current_images['clearlogo9'],clearlogo10=current_images['clearlogo10']))

						elif parse_from == 'thegamesdb':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							dat_file_parsed2 = dict()
							dat_file_parsed2['data'] = dict()
							dat_file_parsed2['data']['games'] = dat_file_parsed['data'][[ii for ii,x in enumerate(dat_file_parsed['filename']) if 'thegamesdb_all_games' in x][0]]['data']['games']
							dat_file_parsed2['data']['studios'] = dat_file_parsed['data'][[ii for ii,x in enumerate(dat_file_parsed['filename']) if 'thegamesdb_all_devs' in x][0]]['data']['developers']
							dat_file_parsed2['data']['genres'] = dat_file_parsed['data'][[ii for ii,x in enumerate(dat_file_parsed['filename']) if 'thegamesdb_all_genres' in x][0]]['data']['genres']
							dat_file_parsed2['data']['platforms'] = dat_file_parsed['data'][[ii for ii,x in enumerate(dat_file_parsed['filename']) if 'thegamesdb_all_platforms' in x][0]]['data']['platforms']
							image_base_url = dat_file_parsed['data'][[ii for ii,x in enumerate(dat_file_parsed['filename']) if 'thegamesdb_all_games' in x][0]]['include']['boxart']['base_url']['original']
							full_list_len = len(dat_file_parsed2['data']['games'])
							if dat_info_in['platform'] == ['all']:
								platforms_to_filter = self.thegamesdb_possible_platforms_ids
							else:
								platforms_to_filter = [self.thegamesdb_possible_platforms_ids[self.thegamesdb_possible_platforms.index(x)] for x in dat_info_in['platform']]
							dat_file_parsed2['data']['games'] = [x for x in dat_file_parsed2['data']['games'] if x.get('platform') in platforms_to_filter]
							filtered_list_len = len(dat_file_parsed2['data']['games'])
							self.rootLogger.info('GAMESDB Parse:  List filtered from %(full_list)s games down to %(partial_list)s games'%{'full_list':full_list_len,'partial_list':filtered_list_len})
							perc_len = [x for x in range(0,len(dat_file_parsed2['data']['games']),int(len(dat_file_parsed2['data']['games'])/10))]
							for ii,gg in enumerate(dat_file_parsed2['data']['games']):
								if ii in perc_len:
									self.rootLogger.debug('GAMESDB Parse: Percent Complete %(perc_comp)s'%{'perc_comp':int((100*ii)/perc_len[-1])})
								if gg.get('players') is not None:
									if gg.get('coop'):
										 current_nplayers = str(gg.get('players'))+' Co-Op'
									else:
										current_nplayers = str(gg.get('players'))
								else:
									current_nplayers = None
								if gg.get('developers') is not None:
									current_studio = ','.join(dat_file_parsed2['data']['studios'][str(x)]['name'] for x in gg.get('developers'))
								if gg.get('genres') is not None:
									current_genres = ','.join(dat_file_parsed2['data']['genres'][str(x)]['name'] for x in gg.get('genres'))
								if gg.get('platform') is not None:
									current_platform = dat_file_parsed2['data']['platforms'][str(gg.get('platform'))]['name']
								if gg.get('images') is not None:
									current_images =  self.get_thegamesdb_images_dict(image_list_in=gg.get('images'),base_url=image_base_url)
							# ['publishers','hashes','uids','developers','players','genres','game_title','coop','platform','alternates','id','overview','images','rating','release_date','youtube']
								dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name=gg.get('game_title'),description=gg.get('game_title'),nplayers=current_nplayers,studio=gg.get('Publisher'),releasedate=gg.get('release_date'),plot=gg.get('overview'),genre=current_genres,videoid=gg.get('youtube'),year=gg.get('release_date'),ESRB=gg.get('rating'),database_id=str(gg.get('id')),database_platform=current_platform,alt_name=gg.get('alternates'),boxart1=current_images['boxart1'],boxart2=current_images['boxart2'],boxart3=current_images['boxart3'],boxart4=current_images['boxart4'],boxart5=current_images['boxart5'],boxart6=current_images['boxart6'],boxart7=current_images['boxart7'],boxart8=current_images['boxart8'],boxart9=current_images['boxart9'],boxart10=current_images['boxart10'],snapshot1=current_images['snapshot1'],snapshot2=current_images['snapshot2'],snapshot3=current_images['snapshot3'],snapshot4=current_images['snapshot4'],snapshot5=current_images['snapshot5'],snapshot6=current_images['snapshot6'],snapshot7=current_images['snapshot7'],snapshot8=current_images['snapshot8'],snapshot9=current_images['snapshot9'],snapshot10=current_images['snapshot10'],banner1=current_images['banner1'],banner2=current_images['banner2'],banner3=current_images['banner3'],banner4=current_images['banner4'],banner5=current_images['banner5'],banner6=current_images['banner6'],banner7=current_images['banner7'],banner8=current_images['banner8'],banner9=current_images['banner9'],banner10=current_images['banner10'],fanart1=current_images['fanart1'],fanart2=current_images['fanart2'],fanart3=current_images['fanart3'],fanart4=current_images['fanart4'],fanart5=current_images['fanart5'],fanart6=current_images['fanart6'],fanart7=current_images['fanart7'],fanart8=current_images['fanart8'],fanart9=current_images['fanart9'],fanart10=current_images['fanart10'],clearlogo1=current_images['clearlogo1'],clearlogo2=current_images['clearlogo2'],clearlogo3=current_images['clearlogo3'],clearlogo4=current_images['clearlogo4'],clearlogo5=current_images['clearlogo5'],clearlogo6=current_images['clearlogo6'],clearlogo7=current_images['clearlogo7'],clearlogo8=current_images['clearlogo8'],clearlogo9=current_images['clearlogo9'],clearlogo10=current_images['clearlogo10']))
								# dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(name=gg.get('game_title'),description=gg.get('game_title'),studio=gg.get('manufacturer'),year=gg.get('release_date')))
						
						elif parse_from == 'progretto_snaps':
							dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
							dat_file_out['datafile']['game']=list()
							if type(dat_file_parsed['filename']) is list and len(dat_file_parsed['filename'])>0:
								for ii,progretto_files in enumerate(dat_file_parsed['filename']):
									if os.path.split(progretto_files)[-1].startswith('pS_AllProject'):
										self.rootLogger.debug('Progretto Parse:  Converting file pS_AllProject')
										dat_file_out['datafile']['header']['emu_version'] = dat_file_parsed['data'][ii]['datafile']['header']['version']
										dat_file_out['datafile']['header']['emu_date'] = dat_file_parsed['data'][ii]['datafile']['header']['date']
										dat_file_out['datafile']['header']['emu_homepage'] = dat_file_parsed['data'][ii]['datafile']['header']['homepage']
										dat_file_out['datafile']['header']['emu_author'] = dat_file_parsed['data'][ii]['datafile']['header']['author']
										current_game_names = sorted(list(set(self.flatten_list([[os.path.splitext(x['@name'].split('\\')[-1])[0] for x in dat_file_parsed['data'][ii]['datafile']['machine'][jj]['rom']] for jj,names in enumerate(self.progretto_media_types) if self.progretto_media_urls[jj] is not None]))))
										self.rootLogger.debug('Progretto Parse:  Total Games found %(total_games)s'%{'total_games':len(current_game_names)})
										# current_game_names = current_game_names[0:2000] #For testing
										current_images = dict()
										for jj,kk in enumerate(self.progretto_media_types):
											if self.progretto_media_urls[jj] is not None:
												current_images[kk] = [None for x in current_game_names] #Init all images to None
										perc_len = [x for x in range(0,len(current_game_names),int(len(current_game_names)/10))]
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  pS_AllProject Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											for jj2,kk in enumerate(self.progretto_media_types):
												if self.progretto_media_urls[jj2] is not None:
													try:
														current_images[kk][jj1] = [self.progretto_media_urls[jj2]+x['@name'].split('\\')[-1] for x in dat_file_parsed['data'][ii]['datafile']['machine'][jj2]['rom'] if '\\'+cgn+'.' in x['@name']][0]
													except:
														pass
									elif os.path.split(progretto_files)[-1].startswith('history'):
										self.rootLogger.debug('Progretto Parse:  Converting file history')
										history_dat_plot_re = re.compile('\$info=(.*?),(.*?)\$end',re.DOTALL)
										all_plots = history_dat_plot_re.findall(dat_file_parsed['data'][ii])
										current_plots = [None for x in current_game_names] #Init all plots to None
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  history.dat Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											try:
												current_plots[jj1] = all_plots[[jj2 for jj2,x in enumerate(all_plots) if x[0]==cgn][0]][1].split('$bio')[-1].split('- CONTRIBUTE -')[0]
											except:
												pass
									elif os.path.split(progretto_files)[-1].startswith('nplayers'):
										self.rootLogger.debug('Progretto Parse:  Converting file nplayers')
										all_nplayers = [x.split('=') for x in dat_file_parsed['data'][ii].split('[NPlayers]')[-1].split('\n')]
										current_nplayers = [None for x in current_game_names] #Init all plots to None
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  nplayers.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											try:
												current_nplayers[jj1] = all_nplayers[[jj2 for jj2,x in enumerate(all_nplayers) if x[0]==cgn][0]][1]
											except:
												pass
									elif os.path.split(progretto_files)[-1].startswith('series'):
										self.rootLogger.debug('Progretto Parse:  Converting file series')
										all_series = self.ini_groups_re.findall(dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1])
										current_groups = [None for x in current_game_names] #Init all groups to None
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  series.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											for jj2,cs in enumerate(all_series):
												if any([cgn==css for css in cs[1].split('\n')]):
													current_groups[jj1] = 'Game Series - '+cs[0]
									elif os.path.split(progretto_files)[-1].startswith('catver'):
										self.rootLogger.debug('Progretto Parse:  Converting file catver')
										all_genres = [x.split('=') for x in dat_file_parsed['data'][ii].split('[Category]')[-1].split('\n')]
										current_genres = [None for x in current_game_names] #Init all plots to None
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  catver.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											try:
												current_genres[jj1] = all_genres[[jj2 for jj2,x in enumerate(all_genres) if x[0]==cgn][0]][1]
											except:
												pass
									elif os.path.split(progretto_files)[-1].startswith('cabinets'):
										self.rootLogger.debug('Progretto Parse:  Converting file cabinets')
										all_cabinets = self.ini_groups_re.findall(dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1])
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  cabinets.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											for jj2,cs in enumerate(all_cabinets):
												if any([cgn==css for css in cs[1].split('\n')]):
													if current_groups[jj1] is None:
														current_groups[jj1] = cs[0]
													else:
														current_groups[jj1] = current_groups[jj1]+','+cs[0]
									elif os.path.split(progretto_files)[-1].startswith('Players'):
										self.rootLogger.debug('Progretto Parse:  Converting file Players')
									elif os.path.split(progretto_files)[-1].startswith('bestgames'):
										self.rootLogger.debug('Progretto Parse:  Converting file bestgames')
										all_bestgames = self.ini_groups_re.findall(dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1])
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  bestgames.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											for jj2,cs in enumerate(all_bestgames):
												if any([cgn==css for css in cs[1].split('\n')]):
													if current_groups[jj1] is None:
														current_groups[jj1] = cs[0]
													else:
														current_groups[jj1] = current_groups[jj1]+','+cs[0]
									elif os.path.split(progretto_files)[-1].startswith('Working Arcade Clean'):
										self.rootLogger.debug('Progretto Parse:  Converting file Working Arcade Clean')
										all_clean = dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1].split('\n')
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  Working Arcade Clean.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											if cgn in all_clean:
												if current_groups[jj1] is None:
													current_groups[jj1] = 'Working Arcade Clean'
												else:
													current_groups[jj1] = current_groups[jj1]+',Working Arcade Clean'
									elif os.path.split(progretto_files)[-1].startswith('Originals Arcade'):
										self.rootLogger.debug('Progretto Parse:  Converting file Originals Arcade')
										all_clean = dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1].split('\n')
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  Originals Arcade.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											if cgn in all_clean:
												if current_groups[jj1] is None:
													current_groups[jj1] = 'Parent'
												else:
													current_groups[jj1] = current_groups[jj1]+',Parent'
									elif os.path.split(progretto_files)[-1].startswith('Clones Arcade'):
										self.rootLogger.debug('Progretto Parse:  Converting file Clones Arcade')
										all_clean = dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1].split('\n')
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  Clones Arcade.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											if cgn in all_clean:
												if current_groups[jj1] is None:
													current_groups[jj1] = 'Clone'
												else:
													current_groups[jj1] = current_groups[jj1]+',Clone'
									elif os.path.split(progretto_files)[-1].startswith('freeplay'):
										self.rootLogger.debug('Progretto Parse:  Converting file freeplay')
										all_clean = dat_file_parsed['data'][ii].split('[ROOT_FOLDER]')[-1].split('\n')
										for jj1,cgn in enumerate(current_game_names):
											if jj1 in perc_len:
												self.rootLogger.debug('Progretto Parse:  freeplay.ini Percent Complete %(perc_comp)s'%{'perc_comp':int((100*jj1)/perc_len[-1])})
											if cgn in all_clean:
												if current_groups[jj1] is None:
													current_groups[jj1] = 'Freeplay'
												else:
													current_groups[jj1] = current_groups[jj1]+',Freeplay'
									else:
										self.rootLogger.error('Unknown progretto file %(progretto_files)s'%{'progretto_files': progretto_files})
								for ii,cgn in enumerate(current_game_names):
									current_images_converted = self.get_progretto_images_dict({kk:current_images[kk][ii] for jj1,kk in enumerate(self.progretto_media_types) if self.progretto_media_urls[jj1] is not None})
									dat_file_out['datafile']['game'].append(self.get_new_IAGL_game_dict(rom_in={'@name':cgn},name=cgn,description=cgn,nplayers=current_nplayers[ii],plot=current_plots[ii],genre=current_genres[ii],groups=current_groups[ii],boxart1=current_images_converted['boxart1'],boxart2=current_images_converted['boxart2'],boxart3=current_images_converted['boxart3'],boxart4=current_images_converted['boxart4'],boxart5=current_images_converted['boxart5'],boxart6=current_images_converted['boxart6'],boxart7=current_images_converted['boxart7'],boxart8=current_images_converted['boxart8'],boxart9=current_images_converted['boxart9'],boxart10=current_images_converted['boxart10'],snapshot1=current_images_converted['snapshot1'],snapshot2=current_images_converted['snapshot2'],snapshot3=current_images_converted['snapshot3'],snapshot4=current_images_converted['snapshot4'],snapshot5=current_images_converted['snapshot5'],snapshot6=current_images_converted['snapshot6'],snapshot7=current_images_converted['snapshot7'],snapshot8=current_images_converted['snapshot8'],snapshot9=current_images_converted['snapshot9'],snapshot10=current_images_converted['snapshot10'],banner1=current_images_converted['banner1'],banner2=current_images_converted['banner2'],banner3=current_images_converted['banner3'],banner4=current_images_converted['banner4'],banner5=current_images_converted['banner5'],banner6=current_images_converted['banner6'],banner7=current_images_converted['banner7'],banner8=current_images_converted['banner8'],banner9=current_images_converted['banner9'],banner10=current_images_converted['banner10'],fanart1=current_images_converted['fanart1'],fanart2=current_images_converted['fanart2'],fanart3=current_images_converted['fanart3'],fanart4=current_images_converted['fanart4'],fanart5=current_images_converted['fanart5'],fanart6=current_images_converted['fanart6'],fanart7=current_images_converted['fanart7'],fanart8=current_images_converted['fanart8'],fanart9=current_images_converted['fanart9'],fanart10=current_images_converted['fanart10'],clearlogo1=current_images_converted['clearlogo1'],clearlogo2=current_images_converted['clearlogo2'],clearlogo3=current_images_converted['clearlogo3'],clearlogo4=current_images_converted['clearlogo4'],clearlogo5=current_images_converted['clearlogo5'],clearlogo6=current_images_converted['clearlogo6'],clearlogo7=current_images_converted['clearlogo7'],clearlogo8=current_images_converted['clearlogo8'],clearlogo9=current_images_converted['clearlogo9'],clearlogo10=current_images_converted['clearlogo10']))
						else:
							self.rootLogger.debug('No conversion algorithm found, returning same data')
							dat_file_out = dat_file_parsed

					elif self.output_settings['type'] == 'ARGDB':
						self.rootLogger.debug('DAT type to convert to %(type_in)s'%{'type_in': self.output_settings['type']})
						self.rootLogger.debug('***NOT YET IMPLEMENTED***')

					else:
						self.rootLogger.error('Conversion type in %(type_in)s is not known, so this will not be parsed'%{'type_in': self.output_settings['type']})
						dat_file_out = dat_file_parsed
				else:
					self.rootLogger.error('DAT type to convert from %(type_in)s is not known, so this will not be converted'%{'type_in': dat_info['type']})
					dat_file_out = dat_file_parsed
			else:
				self.rootLogger.error('DAT file was not parsed, nothing to return')
				dat_file_out = None
		else:
			self.rootLogger.debug('Loading pre-existing converted DAT file %(save_name)s'%{'save_name': current_save_filename})
			dat_file_out=self.load_json_save(filename_in=current_save_filename)
			# with open(os.path.join(self.dat_path_converted,current_save_filename), 'r') as fn:
			# 	dat_file_out = json.load(fn)

		if dat_info_in['save_conversion']:
			if current_save_filename is not None and dat_file_out is not None:
				success = self.create_json_save(dat_file_in=dat_file_out,filename_in=current_save_filename,overwrite_save=self.parsing_settings['overwrite_conversions'])
				# if not os.path.exists(os.path.join(self.dat_path_converted,current_save_filename)) or self.parsing_settings['overwrite_conversions']:
				# 	with open(os.path.join(self.dat_path_converted,current_save_filename), 'w') as fn:
				# 		json.dump(dat_file_out,fn)
				# 	self.rootLogger.debug('DAT conversion was saved as %(save_name)s'%{'save_name': current_save_filename})
			else:
				self.rootLogger.debug('Naming error for file conversion or DAT file was Nonetype'%{'type_in': self.output_settings['type']})

		return dat_file_out

	#Parse the dat file in
	def parse_input_file(self,dat_info_in):
		dat_file_out = None
		try:
			parse_from = self.dat_paths['type'][self.dat_paths['type'].index(dat_info_in['type'])] #Parse from type needs to be in class
			self.rootLogger.debug('DAT type to parse set to %(parse_from)s'%{'parse_from': parse_from})
		except:
			parse_from = None
			self.rootLogger.debug('DAT type in %(type_in)s is not known, so this will not be parsed'%{'type_in': dat_info['type']})
		if parse_from is not None and dat_info_in['filename'] is not None:
			file_to_parse = os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'])
			parse_type = self.dat_paths['parse_file_type'][self.dat_paths['type'].index(parse_from)]
			self.rootLogger.info('File to parse set to %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			self.rootLogger.debug('Filetype to parse set to %(parse_type)s'%{'parse_type': parse_type})
			if parse_type == 'json':
				with open(file_to_parse, 'r') as fn:
					dat_file_out = json.load(fn)
				self.rootLogger.info('JSON file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'folder_json':
				files_to_parse = glob.glob(os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'],'*.json'))
				dat_file_out = dict()
				dat_file_out['filename'] = list()
				dat_file_out['data'] = list()
				for file_to_parse in files_to_parse:
					dat_file_out['filename'].append(file_to_parse)
					with open(file_to_parse, 'r') as fn:
						dat_file_out['data'].append(json.load(fn))
					self.rootLogger.info('JSON file in folder parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'custom_1':
				files_to_parse = glob.glob(os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'],'*.dat'))+glob.glob(os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'],'*.ini'))+glob.glob(os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'],'*','*','*.ini'))+glob.glob(os.path.join(self.dat_paths['raw_path'][self.dat_paths['type'].index(parse_from)],dat_info_in['filename'],'*','*','*.dat'))
				dat_file_out = dict()
				dat_file_out['filename'] = list()
				dat_file_out['data'] = list()
				for file_to_parse in files_to_parse:
					if any([re.findall(x,file_to_parse) for x in self.progretto_files_to_parse]):
						dat_file_out['filename'].append(file_to_parse)
						if file_to_parse.endswith('(cm).dat'):
							dat_file_out['data'].append(etree_to_dict(ET.parse(file_to_parse).getroot()))
						# if file_to_parse.endswith('.ini'):
						else:
							with open(file_to_parse) as current_file:
								file_data = current_file.read()
							dat_file_out['data'].append(file_data)
						self.rootLogger.info('Custom Progretto directory file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'etree':
				dat_file_out=etree_to_dict(ET.parse(file_to_parse).getroot())
				self.rootLogger.info('etree file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'clr':
				dat_file_out=self.parse_clrmamepro_dat(file_to_parse)
				self.rootLogger.info('clr file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'sqlite':
				dat_file_out=self.parse_sqlite_dat(file_to_parse)
				self.rootLogger.info('sqlite file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			elif parse_type == 'variable': #Depends on input
				if parse_from == 'archive_org':
					dat_file_out=self.parse_archive_org_file(file_to_parse)
					self.rootLogger.info('archive_org file parsed %(file_to_parse)s'%{'file_to_parse': os.path.split(file_to_parse)[-1]})
			else:
				self.rootLogger.error('Parse type %(parse_from)s is not known, so this will not be parsed'%{'parse_from': parse_from})
		return dat_file_out


	def parse_sqlite_dat(self,file_in):
		con = sqlite3.connect(file_in)
		c = con.cursor()
		c.execute("SELECT name FROM sqlite_master WHERE type='table';")
		c.execute('select * from RELEASES')
		release_data = c.fetchall()
		self.rootLogger.debug('SQLITE Parse: total releases found %(total_releases)s'%{'total_releases':len(release_data)})
		release_keys = [description[0] for description in c.description]
		release_dict = [dict(zip(release_keys, row)) for row in release_data]
		c.execute('select * from ROMs')
		rom_data = c.fetchall()
		self.rootLogger.debug('SQLITE Parse: total roms found %(total_releases)s'%{'total_releases':len(rom_data)})
		rom_keys = [description[0] for description in c.description]
		rom_dict = [dict(zip(rom_keys, row)) for row in rom_data]
		rom_dict_rom_ids = [x['romID'] for x in rom_dict]
		c.execute('select * from SYSTEMS')
		system_data = c.fetchall()
		system_keys = [description[0] for description in c.description]
		system_dict = [dict(zip(system_keys, row)) for row in system_data]
		system_dict_sys_ids = [x['systemID'] for x in system_dict]
		c.execute('select * from REGIONS')
		region_data = c.fetchall()
		region_keys = [description[0] for description in c.description]
		region_dict = [dict(zip(region_keys, row)) for row in region_data]
		region_dict_reg_ids = [x['regionID'] for x in region_dict]
		dat_file_out = dict()
		dat_file_out['datafile'] = dict()
		dat_file_out['datafile']['game'] = release_dict
		perc_len = [x for x in range(0,len(dat_file_out['datafile']['game']),int(len(dat_file_out['datafile']['game'])/10))]
		for ii, game in enumerate(dat_file_out['datafile']['game']):
			dat_file_out['datafile']['game'][ii]['rom'] = rom_dict[rom_dict_rom_ids.index(game['romID'])]
			if dat_file_out['datafile']['game'][ii]['rom']['systemID'] is not None:
				dat_file_out['datafile']['game'][ii]['rom']['systemName'] = system_dict[system_dict_sys_ids.index(dat_file_out['datafile']['game'][ii]['rom']['systemID'])]['systemName']
			if dat_file_out['datafile']['game'][ii]['rom']['regionID'] is not None:
				dat_file_out['datafile']['game'][ii]['rom']['regionName'] = region_dict[region_dict_reg_ids.index(dat_file_out['datafile']['game'][ii]['rom']['regionID'])]['regionName']
			if ii in perc_len:
				self.rootLogger.debug('SQLITE Parse: Percent Complete %(perc_comp)s'%{'perc_comp':int((100*ii)/perc_len[-1])})
		return dat_file_out

	def parse_clrmamepro_dat(self,file_in):
		dat_file_out = None
		header_name_re = re.compile('name(.*?)\n')
		header_description_re = re.compile('description(.*?)\n')
		header_version_re = re.compile('version(.*?)\n')
		header_homepage_re = re.compile('homepage(.*?)\n')
		header_author_re = re.compile('author(.*?)\n')
		rom_re = re.compile('name(.*?)size(.*?)crc(.*?)md5(.*?)sha1(.*?)\)')
		with open(file_in) as current_file:
			file_data = current_file.read()
		if '\ngame (' in file_data:
			self.rootLogger.info('Found a total of %(num_items)s items in the CLR dat file'%{'num_items': len(file_data.split('\ngame ('))})
			dat_file_out = dict()
			dat_file_out['datafile'] = dict()
			dat_file_out['datafile']['game'] = list()
			for text_data in file_data.split('\ngame ('):
				if 'clrmamepro (' not in text_data:
					current_game = dict()
					current_game['game'] = dict()
					for td in [x.replace('\t','') for x in text_data.split('\n') if x != '' and x !='(' and x != ')']:
						if td.startswith('name '):
							current_game['game']['@name'] = td.replace('name ','')
							if current_game['game']['@name'].startswith('"'):
								current_game['game']['@name'] = current_game['game']['@name'][1:]
							if current_game['game']['@name'].endswith('"'):
								current_game['game']['@name'] = current_game['game']['@name'][:-1]
						if td.startswith('description '):
							current_game['game']['description'] = td.replace('description ','')
							if current_game['game']['description'].startswith('"'):
								current_game['game']['description'] = current_game['game']['description'][1:]
							if current_game['game']['description'].endswith('"'):
								current_game['game']['description'] = current_game['game']['description'][:-1]
						if td.startswith('rom '):
							rom_data = rom_re.findall(td)[0]
							current_game['rom'] = dict()
							current_game['rom']['@name'] = rom_data[0].strip()
							if current_game['rom']['@name'].startswith('"'):
								current_game['rom']['@name'] = current_game['rom']['@name'][1:]
							if current_game['rom']['@name'].endswith('"'):
								current_game['rom']['@name'] = current_game['rom']['@name'][:-1]
							current_game['rom']['size'] = rom_data[1].strip()
							current_game['rom']['@crc'] = rom_data[2].strip()
							current_game['rom']['@md5'] = rom_data[3].strip()
							current_game['rom']['@sha1'] = rom_data[4].strip()
					dat_file_out['datafile']['game'].append(current_game)
				else:
					dat_file_out['datafile']['header'] = dict()
					try:
						dat_file_out['datafile']['header']['emu_name'] = header_name_re.findall(text_data)[0].strip().replace('"','')
					except:
						dat_file_out['datafile']['header']['emu_name'] = None
					try:
						dat_file_out['datafile']['header']['emu_description'] = header_description_re.findall(text_data)[0].strip().replace('"','')
					except:
						dat_file_out['datafile']['header']['emu_description'] = None
					try:
						dat_file_out['datafile']['header']['emu_version'] = header_version_re.findall(text_data)[0].strip().replace('"','')
					except:
						dat_file_out['datafile']['header']['emu_version'] = None
					try:
						dat_file_out['datafile']['header']['emu_homepage'] = header_homepage_re.findall(text_data)[0].strip().replace('"','')
					except:
						dat_file_out['datafile']['header']['emu_homepage'] = None
					try:
						dat_file_out['datafile']['header']['emu_author'] = header_author_re.findall(text_data)[0].strip().replace('"','')
					except:
						dat_file_out['datafile']['header']['emu_author'] = None

		return dat_file_out

	def parse_archive_org_file(self,file_in):
		dat_file_out = None
		xml_base_url = None

		if file_in.lower().endswith('.xml'):
			dat_file_out=etree_to_dict(ET.parse(file_in).getroot())
			self.rootLogger.debug('archive_org xml file parsed %(file_in)s'%{'file_in': os.path.split(file_in)[-1]})
			xml_base_url = self.archive_org_url_base+os.path.split(file_in)[-1].replace('_files.xml','')+'/'
			self.rootLogger.debug('archive_org xml base url is defined as %(base_url)s'%{'base_url': xml_base_url})
			#Generate the archive.org url for the xml file (which doesnt contain the base of the url and is quoted)
			if 'files' in dat_file_out.keys():
				for ii,ffiles in enumerate(dat_file_out['files']['file']):
					dat_file_out['files']['file'][ii]['@name2'] = xml_base_url+dat_file_out['files']['file'][ii]['@name']
					for kk in self.html_unescape_table.keys():
						dat_file_out['files']['file'][ii]['@name2'] = dat_file_out['files']['file'][ii]['@name2'].replace(kk,self.html_unescape_table[kk])
					dat_file_out['files']['file'][ii]['@name2'] = url_quote(dat_file_out['files']['file'][ii]['@name2'].split('archive.org/download/')[-1].strip())
					if '.nkit' in dat_file_out['files']['file'][ii]['@name']:
						dat_file_out['files']['file'][ii]['@name'] = dat_file_out['files']['file'][ii]['@name'].replace('.nkit','')
		elif file_in.lower().endswith('.htm') or file_in.lower().endswith('.html'):
			self.rootLogger.debug('archive_org html file parsed %(file_in)s'%{'file_in': os.path.split(file_in)[-1]})
			current_archive_type = 0
			with open(file_in) as current_file:
				file_data = current_file.read()
			items = self.archive_org_re1.findall(file_data)
			if len(items)==0:
				items = self.archive_org_re2.findall(file_data)
				if len(items)==0:
					items = self.archive_org_re3.findall(file_data)
					if len(items)==0:
						current_archive_type = 0
					else:
						current_archive_type = 3
				else:
					current_archive_type = 2
			else:
				current_archive_type = 1
			self.rootLogger.info('Found a total of %(num_items)s items in the archive_org html file of type %(archive_type)s'%{'num_items': len(items),'archive_type':current_archive_type})
			if current_archive_type>0:
				dat_file_out = dict()
				dat_file_out['datafile'] = dict()
				dat_file_out['datafile']['game'] = list()
				for ii,iitems in enumerate(items):
					current_game = dict()
					current_game['game'] = dict()
					if current_archive_type == 1:
						current_url = iitems[0].split('archive.org/download/')[-1].strip()
						current_filename = iitems[1].strip()
						current_size = iitems[-1].strip()
						# print(current_url)
						# print(current_filename)
						# print(current_size)
					elif current_archive_type == 2:
						current_url = iitems[0].split('archive.org/download/')[-1].strip()
						current_filename = iitems[1].strip()
						current_size = iitems[-1].strip()
					else: #current_archive_type == 3
						current_url = iitems[0].split('archive.org/download/')[-1].strip()
						current_filename = iitems[1].strip()
						current_size = iitems[-1].strip()
					if current_size.isdigit():
						current_size = current_size
					else:
						current_size = string_to_bytes(current_size)
					if current_filename[-4] == '.':
						current_description = current_filename[:-4]
					elif '.7z' in current_filename:
						current_description = current_filename.replace('.7z','')
					else:
						current_description = current_filename
					current_game['game']['@name'] = current_filename
					current_game['description'] = current_description
					current_game['rom'] = dict()
					current_game['rom']['size'] = current_size
					current_game['rom']['@name'] = current_url
					dat_file_out['datafile']['game'].append(current_game)
		else:
			self.rootLogger.error('Unknown archive_org file %(file_in)s, so this will not be parsed'%{'file_in': os.path.split(file_in)[-1]})

		return dat_file_out

	def get_launchbox_alt_name_dict(self,alt_list_in=None):
		dict_out = dict()
		dict_out['alt_name'] = None
		dict_out['alt_name_regions'] = None
		if alt_list_in is not None and len(alt_list_in)>0:
			dict_out['alt_name'] = [x.get('AlternateName') for x in alt_list_in]
			dict_out['alt_name_regions'] = [x.get('Region') for x in alt_list_in]
		return dict_out

	def get_mobygames_images_dict(self,covers_in=None,screenshots_in=None):
		dict_out = dict()
		for kk in self.IAGL_image_keys:
			dict_out[kk] = None
		if covers_in is not None:
			dict_out['boxart1'] = covers_in['image']
		if screenshots_in is not None:
			for ii,iimage in enumerate(screenshots_in):
				dict_out['snapshot'+str(ii+1)] = iimage['image']
		return dict_out

	def get_launchbox_images_dict(self,image_list_in=None,region_in=None):
		dict_out = dict()
		for kk in self.IAGL_image_keys:
			dict_out[kk] = None
		if image_list_in is not None and len(image_list_in)>0:
			boxart_types = ['Box - Front - Reconstructed','Box - Front','Advertisement Flyer - Front','Fanart - Box - Front','Box - Back - Reconstructed','Box - Back','Fanart - Box - Back','Box - 3D','Cart - Front','Fanart - Cart - Front','Disc','Cart - Back','Disc']
			banner_types = ['Banner']
			logo_types = ['Clear Logo']
			screenshot_types = ['Screenshot - Game Title', 'Screenshot - Gameplay','Screenshot - Game Select']
			fanart_types = ['Fanart - Background']
			boxart_list = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in boxart_types]
			banner_list = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in banner_types]
			logo_list = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in logo_types]
			screenshot_list = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in screenshot_types]
			fanart_list = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in fanart_types]
			if region_in is not None: #Use region specific boxart
				boxart_list_region = [(x['Type'],x['FileName']) for x in image_list_in if x['Type'] in boxart_types and x['Region'] in region_in]
				if len(boxart_list_region)>0:
					boxart_list=boxart_list_region
			if len(boxart_list)>0:
				boxart_list.sort(key=lambda x: boxart_types.index(x[0]))
				for ii,iimage in enumerate(boxart_list):
					dict_out['boxart'+str(ii+1)] = self.lb_image_base+iimage[1]
			if len(screenshot_list)>0:
				screenshot_list.sort(key=lambda x: screenshot_types.index(x[0]))
				for ii,iimage in enumerate(screenshot_list):
					dict_out['snapshot'+str(ii+1)] = self.lb_image_base+iimage[1]
			if len(banner_list)>0:
				banner_list.sort(key=lambda x: banner_types.index(x[0]))
				for ii,iimage in enumerate(banner_list):
					dict_out['banner'+str(ii+1)] = self.lb_image_base+iimage[1]
			if len(logo_list)>0:
				logo_list.sort(key=lambda x: logo_types.index(x[0]))
				for ii,iimage in enumerate(logo_list):
					dict_out['clearlogo'+str(ii+1)] = self.lb_image_base+iimage[1]
			if len(fanart_list)>0:
				fanart_list.sort(key=lambda x: fanart_types.index(x[0]))
				for ii,iimage in enumerate(fanart_list):
					dict_out['fanart'+str(ii+1)] = self.lb_image_base+iimage[1]
		return dict_out

	def get_progretto_images_dict(self,image_list_in=None):
			dict_out = dict()
			for kk in self.IAGL_image_keys:
				dict_out[kk] = None
			if image_list_in is not None:
				boxart_types = ['flyers','artpreview','cabinets']
				banner_types = ['marquees','cpanel']
				logo_types = ['logo','icons']
				screenshot_types = ['titles','howto','snap','select','versus','bosses','ends','gameover','warning','scores']
				boxart_list = [image_list_in[x] for x in boxart_types if image_list_in[x] is not None]
				banner_list = [image_list_in[x] for x in banner_types if image_list_in[x] is not None]
				logo_list = [image_list_in[x] for x in logo_types if image_list_in[x] is not None]
				screenshot_list = [image_list_in[x] for x in screenshot_types if image_list_in[x] is not None]
				if len(boxart_list)>0:
					for ii,iimage in enumerate(boxart_list):
						dict_out['boxart'+str(ii+1)] = iimage
				if len(screenshot_list)>0:
					for ii,iimage in enumerate(screenshot_list):
						dict_out['snapshot'+str(ii+1)] = iimage
				if len(banner_list)>0:
					for ii,iimage in enumerate(banner_list):
						dict_out['banner'+str(ii+1)] = iimage
				if len(logo_list)>0:
					for ii,iimage in enumerate(logo_list):
						dict_out['clearlogo'+str(ii+1)] = iimage
			return dict_out

	def get_thegamesdb_images_dict(self,image_list_in=None,base_url=None):
		dict_out = dict()
		for kk in self.IAGL_image_keys:
			dict_out[kk] = None
		if image_list_in is not None and base_url is not None and len(image_list_in)>0:
			boxart_types = ['boxart']
			boxart_orders = ['front','back']
			screenshot_types = ['screenshot']
			clearlogo_types = ['clearlogo']
			banner_types = ['banner']
			fanart_types = ['fanart']
			boxart_list = [(x['filename'].split('boxart/')[-1].split('/')[0],x['filename']) for x in image_list_in if x['type'] in boxart_types]
			banner_list = [x['filename'] for x in image_list_in if x['type'] in banner_types]
			logo_list = [x['filename'] for x in image_list_in if x['type'] in clearlogo_types]
			screenshot_list = [x['filename'] for x in image_list_in if x['type'] in screenshot_types]
			fanart_list = [x['filename'] for x in image_list_in if x['type'] in fanart_types]
			if len(boxart_list)>0:
				boxart_list.sort(key=lambda x: boxart_orders.index(x[0]))
				for ii,iimage in enumerate(boxart_list):
					dict_out['boxart'+str(ii+1)] = base_url+iimage[1]
			if len(screenshot_list)>0:
				# screenshot_list.sort(key=lambda x: screenshot_types.index(x[0]))
				for ii,iimage in enumerate(screenshot_list):
					dict_out['snapshot'+str(ii+1)] = base_url+iimage
			if len(banner_list)>0:
				# banner_list.sort(key=lambda x: banner_types.index(x[0]))
				for ii,iimage in enumerate(banner_list):
					dict_out['banner'+str(ii+1)] = base_url+iimage
			if len(logo_list)>0:
				# logo_list.sort(key=lambda x: logo_types.index(x[0]))
				for ii,iimage in enumerate(logo_list):
					dict_out['clearlogo'+str(ii+1)] = base_url+iimage
			if len(fanart_list)>0:
				# fanart_list.sort(key=lambda x: fanart_types.index(x[0]))
				for ii,iimage in enumerate(fanart_list):
					dict_out['fanart'+str(ii+1)] = base_url+iimage
		return dict_out
	
	#Start of MERGE functions
	def merge_dat_files(self,dat_file_merge_from=None,dat_file_merge_into=None,merge_indices=None,merge_settings=None):
		dat_file_out = None
		if dat_file_merge_from is not None and dat_file_merge_into is not None and merge_settings is not None and self.check_merge_settings(merge_settings):
			dat_file_out = dict()
			dat_file_out['datafile'] = dict()
			dat_file_out['datafile']['bookkeeping'] = self.get_new_merge_datafile_bookkeeping_dict(merge_from=dat_file_merge_from['datafile']['bookkeeping'],merge_into=dat_file_merge_into['datafile']['bookkeeping'],merge_settings=merge_settings)
			dat_file_out['datafile']['header'] = self.get_new_IAGL_header_dict()
			dat_file_out['datafile']['game']=list()
			self.rootLogger.info('Merging data file %(current_dat_file_from)s of type %(current_dat_file_from_type)s into data file %(current_dat_file_to)s of type %(current_dat_file_to_type)s'%{'current_dat_file_from':os.path.split(dat_file_merge_from['datafile']['bookkeeping']['filename'])[-1],'current_dat_file_from_type':dat_file_merge_from['datafile']['bookkeeping']['type_to'],'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1],'current_dat_file_to_type':dat_file_merge_into['datafile']['bookkeeping']['type_to']})
			current_match_keys_to_populate = merge_settings['keys_to_populate']
			current_match_keys_to_overwrite = merge_settings['keys_to_overwrite']
			current_match_keys_to_overwrite_if_populated = merge_settings['keys_to_overwrite_if_populated']
			current_match_keys_to_append = merge_settings['keys_to_append']
			for ii,current_match_type in enumerate(merge_settings['match_type']):
				current_match_keys = merge_settings['match_keys'][ii]
				current_match_keys_from,current_match_keys_to = current_match_keys.split('|')
				if current_match_type == 'exact':
					self.rootLogger.debug('Merge type for data file %(current_dat_file_to)s selected is exact'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1]})
					self.rootLogger.debug('Matching from keys %(current_match_keys_from)s to keys %(current_match_keys_to)s'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1],'current_match_keys_from':current_match_keys_from,'current_match_keys_to':current_match_keys_to})
					for jj1,current_game in enumerate(dat_file_merge_into['datafile']['game']):
						if merge_indices is None or jj1 in merge_indices: #Only merge those indices defined, or all if None are defined
							idx,match_found = self.find_exact_match(current_game_in=current_game,current_from_games=dat_file_merge_from['datafile']['game'],current_match_keys_from=current_match_keys_from,current_match_keys_to=current_match_keys_to)
							if match_found:
								self.rootLogger.debug('Exact match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								current_merged_game = self.merge_game_dict(current_game_from=dat_file_merge_from['datafile']['game'][idx],current_game_to=current_game,keys_to_populate=current_match_keys_to_populate,keys_to_overwrite=current_match_keys_to_overwrite,keys_to_overwrite_if_populated=current_match_keys_to_overwrite_if_populated,keys_to_append=current_match_keys_to_append)
								current_merged_game['bookkeeping']['matching_game_index'] = current_merged_game['bookkeeping']['matching_game_index']+[idx]
								current_merged_game['bookkeeping']['exact_match'] = True
								if current_merged_game is not None or self.parsing_settings['keep_no_matches']:
									dat_file_out['datafile']['game'].append(current_game)
							else:
								self.rootLogger.debug('No Exact match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								if self.parsing_settings['keep_no_matches']:
									current_game['bookkeeping']['exact_match'] = False
									dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
						else:
							if self.parsing_settings['keep_no_matches']:
								# current_game['bookkeeping']['exact_match'] = current_game['bookkeeping']['exact_match'] #Pass previous match info on
								dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
					self.rootLogger.info('Total Exact matches found %(total_matches)s out of %(total_games)s returned'%{'total_matches':len([x for x in dat_file_out['datafile']['game'] if x['bookkeeping']['exact_match']]),'total_games':len(dat_file_out['datafile']['game'])})
				#Fuzzy automatic = any matches above the criteria, then choose the highest score
				elif current_match_type == 'fuzzy_automatic':
					self.rootLogger.debug('Merge type for data file %(current_dat_file_to)s selected is fuzzy automatic'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1]})
					self.rootLogger.debug('Matching keys from keys %(current_match_keys_from)s to keys %(current_match_keys_to)s'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1],'current_match_keys_from':current_match_keys_from,'current_match_keys_to':current_match_keys_to})
					for jj1,current_game in enumerate(dat_file_merge_into['datafile']['game']):
						if merge_indices is None or jj1 in merge_indices: #Only merge those indices defined, or all if None are defined
							idx,match_found = self.find_fuzzy_automatic_match(current_game_in=current_game,current_from_games=dat_file_merge_from['datafile']['game'],current_match_keys_from=current_match_keys_from,current_match_keys_to=current_match_keys_to)
							if match_found:
								self.rootLogger.debug('Fuzzy automatic match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								current_merged_game = self.merge_game_dict(current_game_from=dat_file_merge_from['datafile']['game'][idx],current_game_to=current_game,keys_to_populate=current_match_keys_to_populate,keys_to_overwrite=current_match_keys_to_overwrite,keys_to_overwrite_if_populated=current_match_keys_to_overwrite_if_populated,keys_to_append=current_match_keys_to_append)
								current_merged_game['bookkeeping']['matching_game_index'] = current_merged_game['bookkeeping']['matching_game_index']+[idx]
								current_merged_game['bookkeeping']['fuzzy_match'] = True
								if current_merged_game is not None or self.parsing_settings['keep_no_matches']:
									dat_file_out['datafile']['game'].append(current_game)
							else:
								self.rootLogger.debug('No Fuzzy automatic match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								if self.parsing_settings['keep_no_matches']:
									current_game['bookkeeping']['fuzzy_match'] = False
									dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
						else:
							if self.parsing_settings['keep_no_matches']:
								# current_game['bookkeeping']['fuzzy_match'] = current_game['bookkeeping']['fuzzy_match'] #Pass previous match info on
								dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
					self.rootLogger.info('Total Fuzzy Automatic matches found %(total_matches)s out of %(total_games)s returned'%{'total_matches':len([x for x in dat_file_out['datafile']['game'] if x['bookkeeping']['fuzzy_match']]),'total_games':len(dat_file_out['datafile']['game'])})
				elif current_match_type == 'fuzzy_manual':
					self.rootLogger.debug('Merge type for data file %(current_dat_file_to)s selected is fuzzy manual'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1]})
					self.rootLogger.debug('Matching keys from keys %(current_match_keys_from)s to keys %(current_match_keys_to)s'%{'current_dat_file_to':os.path.split(dat_file_merge_into['datafile']['bookkeeping']['filename'])[-1],'current_match_keys_from':current_match_keys_from,'current_match_keys_to':current_match_keys_to})
					if merge_indices is not None:
						self.rootLogger.debug('Total games to match %(total)s'%{'total':len([x for ii,x in enumerate(dat_file_merge_into['datafile']['game']) if ii in merge_indices])})
					else:
						self.rootLogger.debug('Total games to match %(total)s'%{'total':len(dat_file_merge_into['datafile']['game'])})
					for jj1,current_game in enumerate(dat_file_merge_into['datafile']['game']):
						if merge_indices is None or jj1 in merge_indices: #Only merge those indices defined, or all if None are defined
							idx,match_found = self.find_fuzzy_manual_match(current_game_in=current_game,current_from_games=dat_file_merge_from['datafile']['game'],current_match_keys_from=current_match_keys_from,current_match_keys_to=current_match_keys_to)
							if match_found:
								self.rootLogger.debug('Fuzzy manual match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								current_merged_game = self.merge_game_dict(current_game_from=dat_file_merge_from['datafile']['game'][idx],current_game_to=current_game,keys_to_populate=current_match_keys_to_populate,keys_to_overwrite=current_match_keys_to_overwrite,keys_to_overwrite_if_populated=current_match_keys_to_overwrite_if_populated,keys_to_append=current_match_keys_to_append)
								current_merged_game['bookkeeping']['matching_game_index'] = current_merged_game['bookkeeping']['matching_game_index']+[idx]
								current_merged_game['bookkeeping']['fuzzy_match'] = True
								if current_merged_game is not None or self.parsing_settings['keep_no_matches']:
									dat_file_out['datafile']['game'].append(current_game)
							else:
								self.rootLogger.debug('No Fuzzy manual match found for %(game_name)s / %(game_description)s / %(rom_name)s'%{'game_name':current_game['@name'],'game_description':current_game['description'],'rom_name':current_game['rom'][0]['@name']})
								if self.parsing_settings['keep_no_matches']:
									current_game['bookkeeping']['fuzzy_match'] = False
									dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
						else:
							if self.parsing_settings['keep_no_matches']:
								# current_game['bookkeeping']['fuzzy_match'] = current_game['bookkeeping']['fuzzy_match'] #Pass previous match info on
								dat_file_out['datafile']['game'].append(current_game) #Return same game with nothing merged
					self.rootLogger.info('Total Fuzzy Automatic matches found %(total_matches)s out of %(total_games)s returned'%{'total_matches':len([x for x in dat_file_out['datafile']['game'] if x['bookkeeping']['fuzzy_match']]),'total_games':len(dat_file_out['datafile']['game'])})
				else:
					self.rootLogger.error('Merge Error:  Merge type is not recognized %(current_mt)s'%{'current_mt':current_match_type})
		return dat_file_out

	def merge_game_dict(self,current_game_from=None,current_game_to=None,keys_to_populate=None,keys_to_overwrite=None,keys_to_overwrite_if_populated=None,keys_to_append=None):
		merged_game_out = None
		if current_game_from is not None and current_game_to is not None:
			merged_game_out = current_game_to
			if keys_to_populate is not None: #Populate if current key is None
				for kk in keys_to_populate:
					if '/' in kk:
						kk1,kk2 = kk.split('/')
						if kk1 in current_game_to.keys():
							if kk2 in current_game_to[kk1].keys():
								if current_game_to[kk1][kk2] is None: #It's currently not populated, so try and populate it
									if kk1 in current_game_from.keys():
										if kk2 in current_game_from[kk1].keys():
											merged_game_out[kk1][kk2] = current_game_from[kk1][kk2] #If it's None, thats OK, it was already None
										else:
											self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
									else:
										self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
								else:
									self.rootLogger.debug('The requested key %(current_key)s is already populated for game_from %(game_name)s / %(game_description)s / %(rom_name)s so it will not be merged'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
					else:
						if kk in current_game_to.keys():
							if current_game_to[kk] is None: #It's currently not populated, so try and populate it
								if kk in current_game_from.keys():
									merged_game_out[kk] = current_game_from[kk] #If it's None, thats OK, it was already None
								else:
									self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								self.rootLogger.debug('The requested key %(current_key)s is already populated for game_from %(game_name)s / %(game_description)s / %(rom_name)s so it will not be merged'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
			if keys_to_overwrite is not None:  #Populated regardless of what the current key value is
				for kk in keys_to_overwrite:
					if '/' in kk:
						kk1,kk2 = kk.split('/')
						if kk1 in current_game_to.keys():
							if kk2 in current_game_to[kk1].keys():
								if kk1 in current_game_from.keys():
									if kk2 in current_game_from[k1].keys():
										merged_game_out[kk1][kk2] = current_game_from[kk1][kk2]
								else:
									self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
					else:
						if kk in current_game_to.keys():
							if kk in current_game_from.keys():
								merged_game_out[kk] = current_game_from[kk]
							else:
								self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
			if keys_to_overwrite_if_populated is not None:  #Populate only if the new key/value is not None
				for kk in keys_to_overwrite_if_populated:
					if '/' in kk:
						kk1,kk2 = kk.split('/')
						if kk1 in current_game_to.keys():
							if kk2 in current_game_to[kk1].keys():
								if kk1 in current_game_from.keys():
									if kk2 in current_game_from[k1].keys():
										if current_game_from[kk1][kk2] is not None:
											merged_game_out[kk1][kk2] = current_game_from[kk1][kk2]
										else:
											self.rootLogger.debug('The requested key %(current_key)s is None in game_from and will be skipped %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
								else:
									self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
					else:
						if kk in current_game_to.keys():
							if kk in current_game_from.keys():
								if current_game_from[kk] is not None:
									merged_game_out[kk] = current_game_from[kk]
								else:
									self.rootLogger.debug('The requested key %(current_key)s is None in game_from and will be skipped %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
			if keys_to_append is not None: #Append the value to the list, if it's not yet a list, make it a list
				for kk in keys_to_append:
					if '/' in kk:
						kk1,kk2 = kk.split('/')
						if kk1 in current_game_to.keys():
							if kk2 in current_game_to[kk1].keys():
								if type(current_game_to[kk1][kk2]) is list:
									if kk1 in current_game_from.keys():
										if kk2 in current_game_from[kk1].keys():
											if type(current_game_from[kk1][kk2]) is list:
												merged_game_out[kk1][kk2]=[x for x in merged_game_out[kk1][kk2]+current_game_from[kk1][kk2] if x is not None]
											else:
												if current_game_from[kk1][kk2] is not None:
													merged_game_out[kk1][kk2]=[x for x in merged_game_out[kk1][kk2]+[current_game_from[kk1][kk2]] if x is not None]
										else:
											self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
									else:
										self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
								else:
									if kk1 in current_game_from.keys():
										if kk2 in current_game_from[kk1].keys():
											if type(current_game_from[kk1][kk2]) is list:
												merged_game_out[kk1][kk2]=[x for x in [merged_game_out[kk1][kk2]]+current_game_from[kk1][kk2] if x is not None]
											else:
												if current_game_from[kk1][kk2] is not None:
													merged_game_out[kk1][kk2]=[x for x in [merged_game_out[kk1][kk2]]+[current_game_from[kk1][kk2]] if x is not None]
										else:
											self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
									else:
										self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
					else:
						if kk in current_game_to.keys():
							if type(current_game_to[kk]) is list:
								if kk in current_game_from.keys():
									if type(current_game_from[kk]) is list:
										merged_game_out[kk]=[x for x in merged_game_out[kk]+current_game_from[kk] if x is not None]
									else:
										if current_game_from[kk] is not None:
											merged_game_out[kk]=[x for x in merged_game_out[kk]+[current_game_from[kk]] if x is not None]
								else:
									self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
							else:
								if kk in current_game_from.keys():
									if type(current_game_from[kk]) is list:
										merged_game_out[kk]=[x for x in [merged_game_out[kk]]+current_game_from[kk] if x is not None]
									else:
										if current_game_from[kk] is not None:
											merged_game_out[kk]=[x for x in [merged_game_out[kk]]+[current_game_from[kk]] if x is not None]
								else:
									self.rootLogger.debug('The requested key %(current_key)s does not exist in game_from %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_from['@name'],'game_description':current_game_from['description'],'rom_name':current_game_from['rom'][0]['@name']})
						else:
							self.rootLogger.debug('The requested key %(current_key)s does not exist in game_to %(game_name)s / %(game_description)s / %(rom_name)s'%{'current_key':kk,'game_name':current_game_to['@name'],'game_description':current_game_to['description'],'rom_name':current_game_to['rom'][0]['@name']})
		return merged_game_out

	def find_exact_match(self,current_game_in=None,current_from_games=None,current_match_keys_from=None,current_match_keys_to=None):
		#Returns only the first exact match
		idx_out = None
		match_found = False
		if current_game_in is not None and current_from_games is not None and current_match_keys_from is not None and current_match_keys_to is not None:
			if '/' in current_match_keys_to and '/' in current_match_keys_from:
				try:
					idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]])
				except:
					pass
			elif '/' in current_match_keys_to and '/' not in current_match_keys_from:
				try:
					idx_out = [x[current_match_keys_from] for x in current_from_games].index(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]])
				except:
					pass
			elif '/' not in current_match_keys_to and '/' in current_match_keys_from:
				try:
					idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(current_game_in[current_match_keys_to])
				except:
					pass
			elif '/' not in current_match_keys_to and '/' not in current_match_keys_from:
				try:
					idx_out = [x[current_match_keys_from] for x in current_from_games].index(current_game_in[current_match_keys_to])
				except:
					pass
			else:
				self.rootLogger.error('Merge Error:  Merge key combination is not recognized %(current_match_keys_to)s / %(current_match_keys_from)s'%{'current_match_keys_to':current_match_keys_to,'current_match_keys_from':current_match_keys_from})
			if idx_out is not None:
				match_found = True
		return idx_out,match_found

	def find_fuzzy_automatic_match(self,current_game_in=None,current_from_games=None,current_match_keys_from=None,current_match_keys_to=None):
		#Returns only the first exact match
		idx_out = None
		match_found = False
		if current_game_in is not None and current_from_games is not None and current_match_keys_from is not None and current_match_keys_to is not None:
			if '/' in current_match_keys_to and '/' in current_match_keys_from:
				try:
					best_match = fuzzp.extractOne(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']])
					if best_match[1]>self.parsing_settings['fuzzy_match_ratio']:
						self.rootLogger.debug('Best Match %(best_match)s'%{'best_match':best_match})
						idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(best_match[0])
					else:
						self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_match)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_match':best_match})
				except:
					pass
			elif '/' in current_match_keys_to and '/' not in current_match_keys_from:
				try:
					best_match = fuzzp.extractOne(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']])
					if best_match[1]>self.parsing_settings['fuzzy_match_ratio']:
						self.rootLogger.debug('Best Match %(best_match)s'%{'best_match':best_match})
						idx_out = [x[current_match_keys_from] for x in current_from_games].index(best_match[0])
					else:
						self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_match)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_match':best_match})
				except:
					pass
			elif '/' not in current_match_keys_to and '/' in current_match_keys_from:
				try:
					best_match = fuzzp.extractOne(current_game_in[current_match_keys_to],[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']])
					if best_match[1]>self.parsing_settings['fuzzy_match_ratio']:
						self.rootLogger.debug('Best Match %(best_match)s'%{'best_match':best_match})
						idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(best_match[0])
					else:
						self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_match)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_match':best_match})
				except:
					pass
			elif '/' not in current_match_keys_to and '/' not in current_match_keys_from:
				try:
					best_match = fuzzp.extractOne(current_game_in[current_match_keys_to],[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']])
					if best_match[1]>self.parsing_settings['fuzzy_match_ratio']:
						self.rootLogger.debug('Best Match %(best_match)s'%{'best_match':best_match})
						idx_out = [x[current_match_keys_from] for x in current_from_games].index(best_match[0])
					else:
						self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_match)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_match':best_match})
				except:
					pass
			else:
				self.rootLogger.error('Merge Error:  Merge key combination is not recognized %(current_match_keys_to)s / %(current_match_keys_from)s'%{'current_match_keys_to':current_match_keys_to,'current_match_keys_from':current_match_keys_from})
			if idx_out is not None:
				match_found = True
		return idx_out,match_found

	def find_fuzzy_manual_match(self,current_game_in=None,current_from_games=None,current_match_keys_from=None,current_match_keys_to=None):
		#Returns only the first exact match
		idx_out = None
		match_found = False
		if current_game_in is not None and current_from_games is not None and current_match_keys_from is not None and current_match_keys_to is not None:
			if '/' in current_match_keys_to and '/' in current_match_keys_from:
				best_matches = fuzzp.extract(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				if any([x[1]>self.parsing_settings['fuzzy_match_ratio'] for x in best_matches]): #at least one match better than ratio
					user_choice = input('Matching Options for %(current_name)s key %(current_key)s value %(current_value)s:\n%(current_choices)s\nChoose option (enter for no choice, -1 for manual text key search): '%{'current_name':current_game_in['@name'],'current_key':current_match_keys_from+'|'+current_match_keys_to,'current_value':current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],'current_choices':'\n'.join([str(ii+1)+'. '+x[0]+' ('+str(x[1])+')' for ii,x in enumerate(best_matches)])})
					if len(user_choice)>0:
						if int(user_choice)!=-1:
							idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(best_matches[int(user_choice)-1][0])
						else:
							idx_out = self.custom_fuzzy_search(current_choices=[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				else:
					self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_matches)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_matches':best_matches})
			elif '/' in current_match_keys_to and '/' not in current_match_keys_from:
				best_matches = fuzzp.extract(current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				if any([x[1]>self.parsing_settings['fuzzy_match_ratio'] for x in best_matches]): #at least one match better than ratio
					user_choice = input('Matching Options for %(current_name)s key %(current_key)s value %(current_value)s:\n%(current_choices)s\nChoose option (enter for no choice, -1 for manual text key search): '%{'current_name':current_game_in['@name'],'current_key':current_match_keys_from+'|'+current_match_keys_to,'current_value':current_game_in[current_match_keys_to.split('/')[0]][current_match_keys_to.split('/')[-1]],'current_choices':'\n'.join([str(ii+1)+'. '+x[0]+' ('+str(x[1])+')' for ii,x in enumerate(best_matches)])})
					if len(user_choice)>0:
						if int(user_choice)!=-1:
							idx_out = [x[current_match_keys_from] for x in current_from_games].index(best_matches[int(user_choice)-1][0])
						else:
							idx_out = self.custom_fuzzy_search(current_choices=[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				else:
					self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_matches)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_matches':best_matches})
			elif '/' not in current_match_keys_to and '/' in current_match_keys_from:
				best_matches = fuzzp.extract(current_game_in[current_match_keys_to],[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				if any([x[1]>self.parsing_settings['fuzzy_match_ratio'] for x in best_matches]): #at least one match better than ratio
					user_choice = input('Matching Options for %(current_name)s key %(current_key)s value %(current_value)s:\n%(current_choices)s\nChoose option (enter for no choice, -1 for manual text key search): '%{'current_name':current_game_in['@name'],'current_key':current_match_keys_from+'|'+current_match_keys_to,'current_value':current_game_in[current_match_keys_to],'current_choices':'\n'.join([str(ii+1)+'. '+x[0]+' ('+str(x[1])+')' for ii,x in enumerate(best_matches)])})
					if len(user_choice)>0:
						if int(user_choice)!=-1:
							idx_out = [x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games].index(best_matches[int(user_choice)-1][0])
						else:
							idx_out = self.custom_fuzzy_search(current_choices=[x[current_match_keys_from.split('/')[0]][current_match_keys_from.split('/')[-1]] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				else:
					self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_matches)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_matches':best_matches})
			elif '/' not in current_match_keys_to and '/' not in current_match_keys_from:
				best_matches = fuzzp.extract(current_game_in[current_match_keys_to],[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				if any([x[1]>self.parsing_settings['fuzzy_match_ratio'] for x in best_matches]): #at least one match better than ratio
					user_choice = input('Matching Options for %(current_name)s key %(current_key)s value %(current_value)s:\n%(current_choices)s\nChoose option (enter for no choice, -1 for manual text key search): '%{'current_name':current_game_in['@name'],'current_key':current_match_keys_from+'|'+current_match_keys_to,'current_value':current_game_in[current_match_keys_to],'current_choices':'\n'.join([str(ii+1)+'. '+x[0]+' ('+str(x[1])+')' for ii,x in enumerate(best_matches)])})
					if len(user_choice)>0:
						if int(user_choice)!=-1:
							idx_out = [x[current_match_keys_from] for x in current_from_games].index(best_matches[int(user_choice)-1][0])
						else:
							idx_out = self.custom_fuzzy_search(current_choices=[x[current_match_keys_from] for x in current_from_games],scorer=self.fuzzy_scoring_type[self.parsing_settings['fuzzy_scoring_type']],limit=self.parsing_settings['max_fuzzy_matches'])
				else:
					self.rootLogger.debug('Best Match did not meet ratio of %(current_ratio)s: %(best_matches)s'%{'current_ratio':self.parsing_settings['fuzzy_match_ratio'],'best_matches':best_matches})
			else:
				self.rootLogger.error('Merge Error:  Merge key combination is not recognized %(current_match_keys_to)s / %(current_match_keys_from)s'%{'current_match_keys_to':current_match_keys_to,'current_match_keys_from':current_match_keys_from})
			if idx_out is not None:
				match_found = True
		return idx_out,match_found

	def custom_fuzzy_search(self,current_choices=None,scorer=None,limit=None):
		idx_out = None
		user_choice = -1
		if current_choices is not None and scorer is not None and limit is not None:
			while len(str(user_choice))>0 and int(user_choice) == -1:
				user_search_input = input('Enter custom search input: ')
				if len(user_search_input)>1:
					best_matches = fuzzp.extract(user_search_input,current_choices,scorer=scorer,limit=limit)
					user_choice = input('Matching Options for input %(current_input)s:\n%(current_choices)s\nChoose option (enter for no choice, -1 for manual text key search): '%{'current_input':user_search_input,'current_choices':'\n'.join([str(ii+1)+'. '+x[0]+' ('+str(x[1])+')' for ii,x in enumerate(best_matches)])})
			if len(str(user_choice))>0 and int(user_choice)>0:
				idx_out = current_choices.index(best_matches[int(user_choice)-1][0])
		return idx_out

	def check_merge_settings(self,merge_settings = None):
		check_out = True
		if merge_settings is not None and type(merge_settings) is dict:
			if len(set([len(merge_settings[keys]) for keys in ['match_type','match_keys']])) != 1:
				check_out = False
			for msk in self.merge_setting_keys:
				if msk not in merge_settings.keys():
					check_out = False
		else:
			check_out = False
		if not check_out:
			self.rootLogger.error('Merge Error:  Merge settings are not well formed.')
		return check_out

	#Common class funcs
	def output_dat_file(self,dict_in,filename_in=None,pop_these_keys_in=None,pretty_print=True,order_by_alpha=True):
		success = False
		if filename_in is not None and dict_in is not None:
			for kk in list(dict_in['datafile'].keys()):
				if pop_these_keys_in is not None and type(pop_these_keys_in) is list:
					if kk in pop_these_keys_in:
						dict_in['datafile'].pop(kk)
			for ii,game in enumerate(dict_in['datafile']['game']):
					for kk in list(game.keys()):
						if pop_these_keys_in is not None and type(pop_these_keys_in) is list:
							if kk in pop_these_keys_in:
								dict_in['datafile']['game'][ii].pop(kk)
					for kk in list(game.keys()):
						if kk in dict_in['datafile']['game'][ii].keys() and dict_in['datafile']['game'][ii][kk] is None or (type(dict_in['datafile']['game'][ii][kk]) is str and len(dict_in['datafile']['game'][ii][kk]) == 0):
							dict_in['datafile']['game'][ii].pop(kk)
						if kk in dict_in['datafile']['game'][ii].keys() and type(dict_in['datafile']['game'][ii][kk]) is list:
							for jj,items in enumerate(dict_in['datafile']['game'][ii][kk]):
								for kk2 in list(items.keys()):  #Remove empty / None values
									if dict_in['datafile']['game'][ii][kk][jj][kk2] is None or (type(dict_in['datafile']['game'][ii][kk][jj][kk2]) is str and len(dict_in['datafile']['game'][ii][kk][jj][kk2]) == 0):
										dict_in['datafile']['game'][ii][kk][jj].pop(kk2)

			if order_by_alpha:
				self.rootLogger.debug('Sorting games alphabetically before writing xml'%{'filename_in':filename_in})
				current_order = [x['@name'] for x in dict_in['datafile']['game']]
				ordered_games = sorted([x['@name'] for x in dict_in['datafile']['game']])
				ordered_dict = list()
				for name in ordered_games:
					idx = current_order.index(name)
					ordered_dict.append(dict_in['datafile']['game'][idx])
				dict_in['datafile']['game'] = ordered_dict

			for ii,game in enumerate(dict_in['datafile']['game']): #Need to make these values unidecoded
				for kk in list(game.keys()):
					if kk in self.unidecode_these_keys_in_xml:
						dict_in['datafile']['game'][ii][kk] = unidecode(dict_in['datafile']['game'][ii][kk])
					if kk == 'plot':
						if dict_in['datafile']['game'][ii][kk][-1] == '\n' or dict_in['datafile']['game'][ii][kk][-1] == '\r':
							dict_in['datafile']['game'][ii][kk] = dict_in['datafile']['game'][ii][kk][:-1]

			self.rootLogger.info('Writing xml file %(filename_in)s'%{'filename_in':filename_in})
			# test = dict_to_etree(dict_in)
			# print(test[174547-100:174547+100])
			ET.ElementTree(ET.fromstring(dict_to_etree(dict_in))).write(os.path.join(self.output_path,filename_in))
			if pretty_print:
				self.rootLogger.debug('Pretty printing xml file %(filename_in)s'%{'filename_in':filename_in})
				parser = lxml_etree.XMLParser(resolve_entities=False, strip_cdata=False)
				document = lxml_etree.parse(os.path.join(self.output_path,filename_in), parser)
				document.write(os.path.join(self.output_path,filename_in), pretty_print=True, encoding='utf-8')
				success = True
		else:
			self.rootLogger.error('Filename and dict are not well defined to write xml')
		return success

	def create_json_save(self,dat_file_in=None,filename_in=None,overwrite_save=False):
		success = False
		if filename_in is not None and dat_file_in is not None:
			if not os.path.exists(os.path.join(self.dat_path_converted,filename_in)) or overwrite_save:
				with open(os.path.join(self.dat_path_converted,filename_in), 'w') as fn:
					json.dump(dat_file_in,fn)
					self.rootLogger.info('DAT conversion was saved as %(save_name)s'%{'save_name': filename_in})
				success = True
			else:
				self.rootLogger.error('The requested file already esists %(save_name)s, set overwrite to true if you want to overwrite'%{'save_name': filename_in})
		else:
			self.rootLogger.error('Filename/DAT File to save is required.')
		return success

	def load_json_save(self,filename_in=None):
		dat_file_out = None
		if filename_in is not None:
			if os.path.exists(os.path.join(self.dat_path_converted,filename_in)):
				with open(os.path.join(self.dat_path_converted,filename_in), 'r') as fn:
					dat_file_out = json.load(fn)
					self.rootLogger.info('DAT conversion was loaded %(load_name)s'%{'load_name': filename_in})
			else:
				self.rootLogger.error('The requested file does exists %(load_name)s'%{'load_name': filename_in})
		else:
			self.rootLogger.error('Filename to load is required.')
		return dat_file_out

	def get_rom_ext(self,name_in):
		ext_out = ''
		if name_in is not None:
			if name_in[-4] == '.':
				# ext_out = name_in[:-4]
				ext_out = name_in[-3:].lower()
			elif '.' not in name_in:
				ext_out = ''
			else:
				if '.7z' in name_in:
					ext_out = '7z'
				elif '.vb' in name_in:
					ext_out = 'vb'
				elif '.nkit.gz' in name_in:
					ext_out = 'gz'
				elif '.ws' in name_in:
					ext_out = 'ws'
				elif '.md' in name_in:
					ext_out = 'md'
				elif '.gb' in name_in:
					ext_out = 'gb'
				elif '.sg' in name_in:
					ext_out = 'sg'
				elif '.gg' in name_in:
					ext_out = 'gg'
				elif '.sc' in name_in:
					ext_out = 'sc'
				else:
					self.rootLogger.error('The extension for file %(name_in)s could not be determined'%{'name_in': name_in})
		return ext_out

	def create_tags(self,title_in):
		tags_out = None
		try:
			tags_out = [x.strip() for x in self.flatten_list([x.replace('(','').replace(')','').split(',') for x in self.clean_game_tags.findall(title_in)])]
			if len(tags_out)<1:
				tags_out = None
		except:
			tags_out = None
		return tags_out

	def create_codes(self,title_in):
		codes_out = None
		try:
			codes_out = [x.strip() for x in self.flatten_list([x.replace('[','').replace(']','').split(',') for x in self.clean_game_codes.findall(title_in)])]
			if len(codes_out)<1:
				codes_out = None
		except:
			codes_out = None
		return codes_out

	def create_title_clean(self,title_in):
		if title_in is not None:
			title_out = title_in
			title_out = title_out.replace('.zip','').replace('.7z','').replace('.nkit','')
			title_out = self.clean_game_tags.sub('',title_out).strip()
			title_out = self.clean_game_codes.sub('',title_out).strip()
			#Fix the the's
			if title_out.endswith(', The'):
				title_out = title_out.replace(', The','')
				title_out = 'The '+title_out
			if title_out.endswith(', the'):
				title_out = title_out.replace(', the','')
				title_out = 'the '+title_out
			if ', The -' in title_out:
				title_out = title_out.replace(', The -',' -')
				title_out = 'The '+title_out
			if ', the -' in title_out:
				title_out = title_out.replace(', the -',' -')
				title_out = 'the '+title_out
			return title_out
		else:
			return None

	def create_title_search(self,title_in):
		if title_in is not None:
			title_out = title_in
			title_out = self.create_title_clean(title_out).lower()
			title_out = unidecode(title_out)
			title_out = self.clean_alphanumeric.sub('',title_out)
			title_out = title_out.replace('  ',' ').replace('  ',' ')
			return title_out
		else:
			return None

	def clean_videoid(self,videoid_in=None):
		videoid_out = videoid_in
		throw_these_out = ['http://www.gametrailers.com/user-movie/final-fantasy-viii-official/281556',
							'https://www.google.com.br/url',
							'http://cdn.akamai.steamstatic.com/steam/apps/2036869/movie480.webm',
							'http://pancake-surprise.yolasite.com/',
							'http://www.dailymotion.com/video/k6WzREHE15gb2EQgb1',
							'https://www.nytimes.com/video/business/1194817122168/yaris-game-trailer-by-toyota.html',
							'https://m.ign.com/videos/2019/07/08/race-with-ryan-teaser-trailer',
							'https://www.google.com/url?sa=i&rct=j&q=&esrc=s&source=images&cd=&ved=0ahUKEwjGt8SHqdjUAhUi8YMKHUARBsUQjRwIBw&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DLlUaBCnmd9M&psig=AFQjCNHqM_rJI2dOxs1ouC3v8TQvxsduoA&ust=1498456679561257',
							'https://play.google.com/store/apps/details?id=com.terribletoybox.thimbleweedparkandroid&hl=en',
							'https://www.google.com/url',
							'https://i.ytimg.com/vi/Roah1eNdlXM/hqdefault.jpg?sqp=-oaymwEjCPYBEIoBSFryq4qpAxUIARUAAAAAGAElAADIQj0AgKJDeAE=&rs=AOn4CLD7SE7T9F2SxOobpVTO1KaKrqxOCw',
							'https://www.google.co.uk/url',
							'https://www.google.com.pr/url',
							'https://www.youtube.com/watch',
							'https://www.google.dk/url',
							]
		if videoid_out is not None and len(videoid_out)>0:
			videoid_out = videoid_out.strip().replace('https://youtu.be/','')
			videoid_out = videoid_out.strip().replace('http://youtu.be/','')
			if len(videoid_out.strip().replace('https://','').replace('http://','').replace('/','')) == 11:
				#Likely a video id with http appended errantly
				videoid_out = videoid_out.strip().replace('https://','').replace('http://','').replace('/','')
			if 'youtube' in videoid_out or '=' in videoid_out:
				videoid_out = videoid_out.split('v=')[-1].split('?hd=1')[0].split('&hd=1')[0].split('&feature=')[0].split('&playnext=')[0].split('&list=')[0].split('&ab_channel=')[0].replace('http://www.youtube.com/v/','').replace('&t=0s','')
			if videoid_out.startswith('https://en.wikipedia.org') or videoid_out in throw_these_out:
				videoid_out = None
			if videoid_out is not None and 'http' in videoid_out and '.' not in videoid_out: #Not a valid url but starts with http
				videoid_out = videoid_out.replace('https://','').replace('http://','')
			if videoid_out is not None and ('http' in videoid_out or '=' in videoid_out):
				self.rootLogger.error('VideoID not found in mapping *%(videoid_in)s*, id set to *%(videoid_out)s*'%{'videoid_in':videoid_in,'videoid_out':videoid_out})
			return videoid_out
		else:
			return None
	def clean_esrb(self,esrb_in=None):
		if esrb_in is not None:
			esrb_out = esrb_in
			if esrb_in.lower() == 'not rated' or esrb_in.lower() == 'other - nr (not rated)':
				esrb_out = None
			return esrb_out
		else:
			return None

	def clean_releasedate(self,releasedate_in=None):
		if releasedate_in is not None and len(releasedate_in)>0:
			if releasedate_in not in self.ignore_releasedate_values:
				try:
					return str(date_parser.parse(releasedate_in).strftime('%d/%m/%Y'))
				except Exception as exc: #except Exception, (exc):
					if releasedate_in=='0/13/95':
						releasedate_in = '01/13/95'
						return str(date_parser.parse(releasedate_in).strftime('%d/%m/%Y'))
					self.rootLogger.error('Date Conversion Error for date %(date_in)s: %(exc)s '%{'date_in':releasedate_in,'exc': exc})
					return None
			else:
				return None
		else:
			return None

	def clean_releaseyear(self,year_in=None,releasedate_in=None):
		if year_in is not None and len(year_in)>0:
			if year_in not in self.ignore_releasedate_values:
				try:
					return str(date_parser.parse(year_in).strftime('%Y'))
				except Exception as exc: #except Exception, (exc):
					if year_in=='0/13/95':
							year_in = '1995'
							return str(date_parser.parse(year_in).strftime('%Y'))
					self.rootLogger.error('Year Conversion Error for year %(date_in)s: %(exc)s '%{'date_in':year_in,'exc': exc})
					return None
			else:
				return None
		else:
			if releasedate_in is not None and len(releasedate_in)>0:
				if releasedate_in not in self.ignore_releasedate_values:
					try:
						return str(date_parser.parse(releasedate_in).strftime('%Y'))
					except:
						if releasedate_in=='0/13/95':
							releasedate_in = '01/13/95'
							return str(date_parser.parse(releasedate_in).strftime('%Y'))
						self.rootLogger.error('Year Conversion Error for date %(date_in)s: %(exc)s '%{'date_in':releasedate_in,'exc': exc})
						return None
				else:
					return None
			else:
				return None

	def clean_name(self,name_in):
		if name_in is not None:
			name_out = name_in
			name_out = self.clean_game_tags.sub('',name_in).strip().lower()
			if ', the' in name_out.lower():
				name_out = name_out.replace(', the','')
				name_out = 'the '+name_out
			name_out = name_out.replace(' - ',' ')
			name_out = name_out.replace(': ',' ')
			return name_out.strip().lower()
		else:
			return None

	def clean_plot(self,name_in):
		if name_in is not None:
			name_out = name_in
			if name_out.startswith('"'):
				name_out = name_out[1:]
			if name_out.endswith('"'):
				name_out = name_out[:-1]
			if name_out.endswith('\n'):
				name_out = name_out[:-1]
			name_out = name_out.replace('\r\n','[CR]')
			name_out = name_out.replace('\n','[CR]')
			name_out = name_out.replace('\r','[CR]')
			name_out = name_out.replace('[CR][CR]','[CR]')
			name_out = name_out.replace('[CR][CR]','[CR]')
			name_out = name_out.replace('[CR][CR]','[CR]')
			name_out = name_out.replace('[CR][CR]','[CR]')
			name_out = name_out.replace(' & ',' and ')
			if name_out.startswith('[CR]'):
				name_out = name_out[4:]
			if name_out.endswith('[CR]'):
				name_out = name_out[:-4]
			name_out = unidecode(self.html2text.handle(name_out))
			return name_out
		else:
			return None

	def clean_company(self,name_in):
		if name_in is not None:
			name_out = name_in
			name_out = name_out.replace(',Ltd.','')
			name_out = name_out.replace(',LTD.','')
			name_out = name_out.replace(', Ltd.','')
			name_out = name_out.replace(', LTD.','')
			name_out = name_out.replace(', ltd.','')
			name_out = name_out.replace(', Ltd','')
			name_out = name_out.replace(', LTD','')
			name_out = name_out.replace(', ltd','')
			name_out = name_out.replace(',Inc.','')
			name_out = name_out.replace(',INC.','')
			name_out = name_out.replace(', Inc.','')
			name_out = name_out.replace(', INC.','')
			name_out = name_out.replace(', inc.','')
			name_out = name_out.replace(', Inc','')
			name_out = name_out.replace(', INC','')
			name_out = name_out.replace(', inc','')
			name_out = name_out.replace(',The','')
			name_out = name_out.replace(',THE','')
			name_out = name_out.replace(', The','')
			name_out = name_out.replace(', THE','')
			name_out = name_out.replace(', the','')
			name_out = name_out.replace(' Co.','')
			name_out = name_out.replace(' co.','')
			name_out = name_out.replace(' Pty.','')
			name_out = name_out.replace(' pty.','')
			name_out = name_out.replace(',LLC','')
			name_out = name_out.replace(',LLC.','')
			name_out = name_out.replace(', LLC.','')
			name_out = name_out.replace(', LLC','')
			name_out = name_out.replace(',llc','')
			name_out = name_out.replace(', llc','')
			name_out = name_out.replace(', Llc','')
			name_out = name_out.replace(', S.L.','')
			name_out = name_out.replace(', S.A.','')
			name_out = name_out.replace(', s.l.','')
			name_out = name_out.replace(', s.a.','')
			# if ',' in name_out:
			# 	print(name_out)
			return unidecode(name_out.strip())
		else:
			return None

	def clean_genres(self,name_in):
		if name_in is not None and len(name_in)>0:
			name_out = name_in

			if name_in is not None and len(name_in)>0:
				name_list = [x.strip() for x in name_in.split(',') if x is not None and len(x)>0]
			genre_map = {'1st Person': '1st Person',
						'2.5D': '2.5D',
						'2D': '2D',
						'3D': '3D',
						'3rd Person': '3rd Person',
						'ATV': 'ATV',
						'Action': 'Action',
						'Action Adventure': 'Action,Adventure',
						'Action RPG': 'Action,RPG',
						'Action; Adventure': 'Action,Adventure',
						'Action; Adventure; Platform': 'Action,Adventure,Platform',
						'Action; Fighting': 'Action,Fighting',
						'Action; Platform': 'Action,Platform',
						'Action; Platform; Puzzle': 'Action,Platform,Puzzle',
						'Action; Puzzle': 'Action,Puzzle',
						'Action; Role-Playing': 'Action,RPG',
						'Action; Shooter': 'Action,Shooter',
						'Action; Stealth': 'Action,Stealth',
						'Action; Strategy': 'Action,Strategy',
						'ActionPlatform': 'Action,Platform',
						'ActionRole-Playing': 'Action,RPG',
						'ActionStealth': 'Action,Stealth',
						'Adult': 'Adult',
						'* Mature *': 'Adult',
						'Adventure': 'Adventure',
						'Adventure - Adventure Creator': 'Adventure',
						'Adventure - AdventureWriter': 'Adventure',
						'Adventure - Animated Graphics & Text':'Adventure,Graphic Adventure',
						'Adventure - Arcade 2D': 'Adventure,Arcade,2D',
						'Adventure - Arcade 3D': 'Adventure,Arcade,3D',
						'Adventure - Arcade Isometric': 'Adventure,Arcade,Isometric',
						'Adventure - Click and Type': 'Adventure,Point and Click',
						'Adventure - Comic': 'Adventure,Comic',
						'Adventure - Construction Kit': 'Adventure,Construction',
						'Adventure - Graphic(Charset)': 'Adventure,Graphic Adventure',
						'Adventure - Graphic(Hi-Res)': 'Adventure,Graphic Adventure',
						'Adventure - Graphics & Text': 'Adventure,Graphic Adventure',
						'Adventure - Joystick only': 'Adventure',
						'Adventure - Miscellaneous': 'Adventure,Miscellaneous',
						'Adventure - Move and Type': 'Adventure,Move and Type',
						'Adventure - Point and Click': 'Adventure,Point and Click',
						'Adventure - RPG 2D': 'Adventure,RPG,2D',
						'Adventure - RPG 3D': 'Adventure,RPG,3D',
						'Adventure - RPG Isometric': 'Adventure,RPG,Isometric',
						'Adventure - RPG Text': 'Adventure,RPG,Text Based',
						'Adventure - Selectable Answers':'Adventure,Selectable Answers',
						'Adventure - Text only': 'Adventure,Text Based',
						'Adventure - [uncategorized]': 'Adventure',
						'Adventure – Graphics & Text': 'Adventure,Graphic Adventure',
						'Adventure – Miscellaneous': 'Adventure,Miscellaneous',
						'Adventure; Platform': 'Adventure,Platform',
						'Adventure; Puzzle': 'Adventure,Puzzle',
						'Adventure; Strategy': 'Adventure,Strategy',
						'Alternative': 'Alternative',
						'Animation': 'Animation',
						'Arcade': 'Arcade',
						'Arcade - Avoid it': 'Arcade',
						'Arcade - Bat & Ball': 'Arcade,Baseball',
						"Arcade - Beat'em Up": 'Arcade,Beat Em Up',
						"Arcade - Beat'em Up - Progressive":'Arcade,Beat Em Up,Progressive',
						'Arcade - Bomberman': 'Arcade',
						'Arcade - Boulder Dash': 'Arcade',
						'Arcade - Boulderdash': 'Arcade',
						'Arcade - Breakout': 'Arcade,Breakout',
						'Arcade - Catch it': 'Arcade',
						"Arcade - Collect'em Up":'Arcade,Collecting',
						'Arcade - Construction Kit': 'Arcade,Construction',
						'Arcade - Frogger': 'Arcade',
						'Arcade - Joust': 'Arcade',
						'Arcade - Labyrinth': 'Arcade,Maze',
						'Arcade - Labyrinth/Maze': 'Arcade,Maze',
						'Arcade - Lander': 'Arcade',
						'Arcade - Logical Game': 'Arcade,Logic',
						'Arcade - Miscellaneous': 'Arcade,Miscellaneous',
						'Arcade - Multigenre': 'Arcade',
						'Arcade - Pac Man': 'Arcade',
						'Arcade - Pengo': 'Arcade',
						'Arcade - Pinball': 'Arcade,Pinball',
						'Arcade - Platformer (3D)': 'Arcade,Platform,3D',
						'Arcade - Platformer (Multi Screen)': 'Arcade,Platform,Multi Screen',
						'Arcade - Platformer (Scrolling Screen)': 'Arcade,Platform,Side Scroller',
						'Arcade - Platformer (Single Screen)': 'Arcade,Platform',
						'Arcade - Qix': 'Arcade',
						'Arcade - Tetris': 'Arcade',
						'Arcade - Tron': 'Arcade',
						'Arcade - Worm': 'Arcade',
						'Arcade - [uncategorized]': 'Arcade',
						'Arcade – Labyrinth/Maze': 'Arcade,Maze',
						'Arcade – Pinball': 'Arcade,Pinball',
						'Armwrestling': 'Arm Wrestling',
						'Ball & Paddle / Breakout': 'Ball and Paddle,Breakout',
						'Ball Guide': 'Ball Guide',
						'Ball and Paddle': 'Ball and Paddle',
						'Baseball': 'Sports,Baseball',
						'Basketball': 'Sports,Basketball',
						'Baseball/Sports': 'Sports,Baseball',
						'Basketball/Sports': 'Sports,Basketball',
						'Biking/Sports': 'Sports,Biking',
						'Boxing/Sports': 'Sports,Boxing',
						'Fishing/Sports': 'Sports,Fishing',
						'Football/Sports': 'Sports,Football',
						'Golf/Sports': 'Sports,Golf',
						'Hockey/Sports': 'Sports,Hockey',
						'Olympic/Sports': 'Sports,Olympic',
						'Skateboarding/Sports': 'Sports,Skateboarding',
						'Snowboarding/Sports': 'Sports,Snowboarding',
						'Soccer/Sports': 'Sports,Soccer',
						'Sports/Surfing': 'Sports,Surfing',
						"Beat 'em Up": 'Beat Em Up',
						'Beat Em Up': 'Beat Em Up',
						"Beat-'Em-Up": 'Beat Em Up',
						'Beat-Em-Up': 'Beat Em Up',
						'Bike': 'Biking',
						'Biking': 'Biking',
						'Billiards': 'Billiards',
						'Board Game': 'Board Game',
						'Board Game - Chess': 'Board Game,Chess',
						'Board Game - Draughts': 'Board Game',
						'Board Game - Kalaha': 'Board Game',
						'Board Game - Miscellaneous': 'Board Game,Miscellaneous',
						'Board Game - Monopoly': 'Board Game',
						'Board Game - Othello': 'Board Game',
						'Board Game / Backgammon': 'Board Game,Backgammon',
						'Board Game / Chess Machine': 'Board Game,Chess',
						'Board Games': 'Board Game',
						'Board Games - Chess': 'Board Game,Chess',
						'Board Games - Jigsaws': 'Board Game,Puzzle',
						'Board Games - Mahjongg (Solitaire)':'Board Game,Mahjong,Solitaire',
						'Board Games - Miscellaneous': 'Board Game,Miscellaneous',
						'Board Games - Othello': 'Board Game',
						'Boat': 'Boating',
						'Boats': 'Boating',
						'Bowling': 'Bowling',
						'Boxing': 'Sports,Boxing',
						'Brain - Arcade': 'Brain Games,Arcade',
						'Brain - Logical Game': 'Brain Games,Logic',
						'Brain - Mastermind': 'Brain Games',
						'Brain - Memory': 'Brain Games,Memory',
						'Brain - Miscellaneous': 'Brain Games,Miscellaneous',
						'Brain - Puzzle': 'Brain Games,Puzzle',
						'Brain - Tic Tac Toe': 'Brain Games,Miscellaneous',
						'Brain - Towers of Hanoi': 'Brain Games,Tower',
						'Breakout': 'Breakout',
						'Breeding/Constructing': 'Breeding,Construction',
						'Building': 'Construction',
						'Bull Fighting': 'Bull Fighting',
						'Business - Terminal': 'Business,Terminal',
						'Calculator / Astrological Computer':'Calculator,Astrological Computer',
						'Car Combat': 'Car Combat',
						'Card': 'Card',
						'Card Battle': 'Card Battle',
						'Cards': 'Card',
						'Cards - Blackjack': 'Card,Blackjack',
						'Cards - Miscellaneous': 'Card,Miscellaneous',
						'Cards - Poker': 'Card,Poker',
						'Cards - Solitaire': 'Card,Solitaire',
						'Casino': 'Casino',
						'Casino / Bingo': 'Casino,Bingo',
						'Casino / Cards': 'Casino,Card',
						'Casino / Misc.': 'Casino,Miscellaneous',
						'Casino / Multiplay': 'Casino,Mini-Games',
						'Casino / Racing': 'Casino,Racing',
						'Catch': 'Catch',
						'Checkers': 'Checkers',
						'Chess': 'Chess',
						'Chinese': 'Chinese',
						'Christian': 'Christian',
						'City Building': 'Construction',
						'Civilian Plane': 'Flying',
						'Climbing': 'Climbing',
						'Climbing / Tree - Plant': 'Climbing,Planting,Nature',
						'Collect': 'Collecting',
						'Collect and Put': 'Collecting',
						'Command': 'Command',
						'Compilation': 'Compilation',
						'Computer': 'Computer',
						'Computer / Business - Terminal':'Computer,Business,Terminal',
						'Computer / Construction Kit': 'Computer,Construction',
						'Computer / Home System': 'Computer,Home System',
						'Computer / Punched Car': 'Computer,Punched Card',
						'Computer / Single Board': 'Computer,Single Board',
						'Computer / Training Board': 'Computer,Training Board',
						'Computer / Word-processing Machine':'Computer,Word Processor',
						'Console': 'Console',
						'Console-style RPG': 'RPG',
						'Construction and Management Simulation':'Construction,Management,Simulation',
						'Cricket': 'Sports,Cricket',
						'Cross': 'Cross',
						'Dance': 'Dance',
						'Dancing': 'Dance',
						'Darts': 'Darts',
						'Defeat Enemies': 'Defeat Enemies',
						'Demo': 'Demo',
						'Demo Disc': 'Demo',
						'Demolition Derby': 'Driving,Demolition Derby',
						'Digging': 'Digging',
						'Dodgeball': 'Dodgeball',
						'Drag': 'Racing',
						'Driving': 'Driving',
						'Driving (chase view)': 'Driving,3rd Person',
						'Driving / 1st Person': 'Driving,1st Person',
						'Driving / Boat': 'Driving,Boating',
						'Driving / Misc.': 'Driving,Miscellaneous',
						'Driving / Race': 'Driving,Race',
						'Driving / Race (chase view)': 'Driving,Racing,3rd Person',
						'Driving / Race (chase view) Bike':'Driving,Racing,3rd Person,Biking',
						'Driving / Race Track': 'Driving,Racing',
						'Driving 1st Person': 'Driving,1st Person',
						'Driving Diagonal': 'Driving,Isometric',
						'Driving Horizontal': 'Driving,Horizontal',
						'Driving Vertical': 'Driving,Vertical',
						'Drop': 'Drop',
						'Education': 'Educational',
						'Educational': 'Educational',
						'Educational - Geography': 'Educational,Geography',
						'Educational - Maths': 'Educational,Math',
						'Educational - Miscellaneous': 'Educational,Miscellaneous',
						'Educational - Quiz': 'Educational,Quiz',
						'Educational - Typing': 'Educational,Typing',
						'Educational - Vocabulary': 'Educational,Vocabulary',
						'Edutainment': 'Educational',
						'Electromechanical': 'Electromechanical',
						'Electromechanical / Misc.': 'Electromechanical,Miscellaneous',
						'Electromechanical / Pinball': 'Electromechanical,Pinball',
						'Electromechanical / Redemption':'Electromechanical,Redemption',
						'Electromechanical / Reels': 'Electromechanical,Reels',
						'English': 'English',
						'English - Music': 'English,Music',
						'Escape': 'Escape',
						'Exercise / Fitness': 'Fitness',
						'FPS': 'FPS',
						'Fanmade': 'Homebrew',
						'Fantasy': 'Fantasy',
						'Field': 'Field',
						'Fighter': 'Fighter',
						'Fighter / 2.5D': 'Fighter,2.5D',
						'Fighter / 2D': 'Fighter,2D',
						'Fighter / 3D': 'Fighter,3D',
						'Fighter / Versus': 'Fighter,Versus',
						'Fighter / Vertical': 'Fighter,Vertical',
						'Fighter Scrolling': 'Fighter,Side Scroller',
						'Fighting': 'Fighter',
						'Fighting; Sports': 'Fighter,Sports',
						'First Person': '1st Person',
						'First-Person': '1st Person',
						'Fishing': 'Fishing',
						'Flight': 'Flying',
						'Flight Simulator': 'Flight Simulator',
						'Flight Simulator; Strategy': 'Flight Simulator,Strategy',
						'Flying': 'Flying',
						'Flying (chase view)': 'Flying,3rd Person',
						'Flying 1st Person': 'Flying,1st Person',
						'Flying Diagonal': 'Flying,Isometric',
						'Flying Horizontal': 'Flying,Horizontal',
						'Flying Vertical': 'Flying,Vertical',
						'Football': 'Sports,Football',
						'Formula One': 'Racing,Formula One',
						'French': 'French',
						'Futuristic': 'Sci-Fi',
						'Futuristic Jet': 'Sci-Fi,Flying',
						'GT / Street': 'Racing,GT',
						'Gallery': 'Gallery',
						'Gambling': 'Gambling',
						'Gambling - Cards': 'Gambling,Card',
						'Gambling - Casino': 'Gambling,Casino',
						'Gambling - Miscellaneous': 'Gambling,Miscellaneous',
						'Gambling - Quiz': 'Gambling,Quiz',
						'Gambling - Racing': 'Gambling,Racing',
						'Gambling - Slot Machine': 'Casino,Slot Machine',
						'Game Console': 'Console',
						'Game Console / Home Videogame': 'Console,Home System',
						'Game Show': 'Game Show',
						'General': 'Miscellaneous',
						'Go': 'Board Game',
						'Golf': 'Golf',
						'Guide and Collect': 'Collecting',
						'Gun': 'Shooter',
						'Hammer': 'Hammer',
						'Hanafuda': 'Hanafuda',
						'Handball': 'Handball',
						'Handheld / Electronic Game': 'Handheld,Electronic Game',
						"Handheld / Plug n' Play TV Game":'Handheld,Plug and Play,TV Game',
						'Handheld / Pocket Device - Pad - PDA':'Handheld,Pocket Device,PDA',
						'Hang Gliding': 'Flying,Hang Gliding',
						'Hardware': 'Hardware',
						'Helicopter': 'Flying,Helicopter',
						'Hidden Object': 'Hidden Object',
						'Historic': 'Historic',
						'Hockey': 'Sports,Hockey',
						'Home Videogame Console': 'Console,Home Videogame',
						'Horror': 'Horror',
						'Horse Racing': 'Horse Racing',
						'Horseshoes': 'Horseshoes',
						'Hot-air Balloon': 'Flying,Hot-air Balloon',
						'Hunting': 'Hunting',
						'Ice Hockey': 'Sports,Ice Hockey',
						'Instruments': 'Instruments',
						'Integrate': 'Integrate',
						'Interactive Fiction': 'Interactive Fiction',
						'Interactive Movie': 'Interactive Movie',
						'Isometric': 'Isometric',
						'Italian': 'Italian',
						'Japanese': 'Japanese',
						'Jump & Scrolling': 'Jumping,Side Scroller',
						'Jump and Bounce': 'Jumping',
						'Jump and Scrolling': 'Jumping,Side Scroller',
						'Jump and Touch': 'Jumping',
						'Kart': 'Racing,Kart',
						'Ladders': 'Ladders',
						'Landing': 'Landing',
						'Language': 'Language',
						'Large Spaceship': 'Flying,Space',
						'Life Simulation': 'Virtual Life,Simulation',
						'Light Gun': 'Gun',
						'Logic': 'Logic',
						'Lottery': 'Gambling',
						'MMO': 'MMO',
						'Mahjong': 'Mahjong',
						'Management': 'Management',
						'Managerial': 'Management',
						'Match': 'Matching',
						'Matching': 'Matching',
						'Maze': 'Maze',
						'Maze / Change Surface': 'Maze,Changing Surface',
						'Maze / Collect': 'Maze,Collecting',
						'Maze / Shooter Small': 'Maze,Shooter',
						'Maze / Surround': 'Maze,Surround',
						'Mech': 'Mecha',
						'Medal Game': 'Electromechanical',
						'Military': 'War',
						'Mini-Games': 'Mini-Games',
						'Minigames': 'Mini-Games',
						'Misc. / Bank-teller Terminal':'Miscellaneous,Terminal',
						'Misc. / Catch': 'Miscellaneous,Catch',
						'Misc. / Coin Pusher': 'Miscellaneous,Coin Pusher',
						'Misc. / Document Processors':'Miscellaneous,Word Processor',
						'Misc. / Electronic Board Game':'Miscellaneous,Electronic Game',
						'Misc. / Laser Disk Simulator':'Miscellaneous,Laserdisc Player',
						'Misc. / Teletype': 'Miscellaneous,Teletype',
						'Miscellaneous': 'Miscellaneous',
						'Miscellaneous - Adult': 'Miscellaneous,Adult',
						'Miscellaneous - Weird!': 'Miscellaneous',
						'Miscellaneous Horizontal': 'Miscellaneous,Side Scroller',
						'Miscellaneous Vertical': 'Miscellaneous,Vertical',
						'Mission Based': 'Mission Based',
						'Mission-based': 'Mission Based',
						'Modern': 'Modern',
						'Modern Jet': 'Flying',
						'Motocross': 'Racing,Motorcycle',
						'Motorcycle': 'Motorcycle',
						'Mountain - Wall': 'Climbing',
						'Move and Sort': 'Move and Sort',
						'Multi-Directional': 'Multi-Directional',
						'Multi-Games': 'Mini-Games',
						'Multi-Screen': 'Multi Screen',
						'MultiGame': 'Mini-Games',
						'MultiGame / Compilation': 'Mini-Games,Compilation',
						'Multiplay': 'Mini-Games',
						'Music': 'Music',
						'Music / Synthesizer': 'Music,Synthesizer',
						'Music Maker': 'Music,Music Maker',
						'Nature': 'Nature',
						'Not Classified': None,
						'Olympic': 'Sports,Olympic',
						'Olympic Sports': 'Sports,Olympic',
						'On-foot': 'Walking',
						'Othello': 'Othello',
						'Other': 'Miscellaneous',
						'Outline': 'Outline',
						'PC-style RPG': 'RPG',
						'Pachinko': 'Pachinko',
						'Paint': 'Paint',
						'Parlor': 'Party Game',
						'Party': 'Party Game',
						'Pinball': 'Pinball',
						'Ping Pong': 'Pong',
						'Ping pong': 'Pong',
						'Platform': 'Platform',
						'Platform / Fighter': 'Platform,Fighter',
						'Platform / Fighter Scrolling': 'Platform,Fighter,Side Scroller',
						'Platform / Run': 'Platform,Run',
						'Platform / Run Jump': 'Platform,Run and Jump',
						'Platform / Shooter Scrolling': 'Platform,Shooter,Side Scroller',
						'Platform; Puzzle': 'Platform,Puzzle',
						'Platformer': 'Platform',
						'Platformer - Multi Screen': 'Platform,Multi Screen',
						'Platformer - Single Screen': 'Platform',
						'Platformer – Scrolling Screen': 'Platform,Side Scroller',
						'Pong': 'Pong',
						'Pool': 'Billiards',
						'Pool and Dart': 'Billiards,Darts',
						'Print Club': 'Print Club',
						'Puzzle': 'Puzzle',
						'Puzzle / Drop': 'Puzzle,Drop',
						'Puzzle / Drop * Mature *': 'Puzzle,Drop,Adult',
						'Puzzle / Match': 'Puzzle,Matching',
						'Puzzle / Misc.': 'Puzzle,Miscellaneous',
						'Puzzle / Toss': 'Puzzle,Toss',
						'Questions in English': 'Quiz,English',
						'Questions in Japanese': 'Quiz,Japanese',
						'Questions in Korean': 'Quiz,Korean',
						'Questions in Spanish': 'Quiz,Spanish',
						'Quill': 'Quill',
						'Quiz': 'Quiz',
						'Quiz / Questions in Japanese': 'Quiz,Japanese',
						'RPG': 'RPG',
						'Race': 'Racing',
						'Race (chase view)': 'Racing,3rd Person',
						'Race (chase view) Bike': 'Racing,3rd Person,Biking',
						'Race 1st Person': 'Racing,1st Person',
						'Race Bike': 'Racing,Biking',
						'Race Track': 'Racing',
						'Racing': 'Racing',
						'Racing - Cars': 'Racing',
						'Racing - Formula One': 'Racing,Formula One',
						'Racing - Isometric': 'Racing,Isometric',
						'Racing - Miscellaneous': 'Racing,Miscellaneous',
						'Racing - Motorcycle': 'Racing,Motorcycle',
						'Racing - Overhead': 'Racing,Field',
						'Racing - Stay on Track': 'Racing',
						'Racing - [uncategorized]': 'Racing',
						'Rail': 'Rail',
						'Rail Shooter': 'Rail,Shooter',
						'Rail-Shooter': 'Rail,Shooter',
						'Rally / Offroad': 'Racing,Off Road',
						'Real-Time': 'Real Time',
						'Realtime': 'Real Time',
						'Reconstruction': 'Construction',
						'Redemption': 'Redemption',
						'Reels': 'Slot Machine,Reels',
						'Renju': 'Renju',
						'Retro': 'Classics',
						'Rhythm': 'Rhythm',
						'Rhythm / Dance': 'Rhythm,Dance',
						'Role-Playing': 'RPG',
						'Role-Playing; Shooter': 'RPG,Shooter',
						'Role-Playing; Strategy': 'RPG,Strategy',
						'Role-playing': 'RPG',
						'Roulette': 'Casino,Roulette',
						'Rugby': 'Sports,Rugby',
						'Rugby Football': 'Sports,Rugby',
						'Run': 'Run',
						'Run Jump': 'Run and Jump',
						'Run-and-Gun': 'Run and Gun',
						'Sandbox': 'Sandbox',
						'Sci-Fi': 'Sci-Fi',
						'Scrolling': 'Side Scroller',
						'Shoot Em Up': 'Shoot Em Up',
						"Shoot'em Up - 3D":'Shoot Em Up,3D',
						"Shoot'em Up - Asteroids": 'Shoot Em Up,Field',
						"Shoot'em Up - Centipede": 'Shoot Em Up',
						"Shoot'em Up - Chase View": 'Shoot Em Up,3rd Person',
						"Shoot'em Up - Crosshair":'Shoot Em Up',
						"Shoot'em Up - D-Scrolling": 'Shoot Em Up,Multi-Directional',
						"Shoot'em Up - Defender": 'Shoot Em Up,Field',
						"Shoot'em Up - Duel":'Shoot Em Up,Versus',
						"Shoot'em Up - FPS":'Shoot Em Up,FPS',
						"Shoot'em Up - Gauntlet":'Shoot Em Up',
						"Shoot'em Up - H-Scrolling":'Shoot Em Up,Side Scroller',
						"Shoot'em Up - Horizontal":'Shoot Em Up,Horizontal',
						"Shoot'em Up - Isometric":'Shoot Em Up,Isometric',
						"Shoot'em Up - Miscellaneous":'Shoot Em Up,Miscellaneous',
						"Shoot'em Up - Missile Command":'Shoot Em Up',
						"Shoot'em Up - Multi-Directional":'Shoot Em Up,Multi-Directional',
						"Shoot'em Up - Multi-Scrolling":'Shoot Em Up,Multi-Directional',
						"Shoot'em Up - Platformer": 'Shoot Em Up,Platform',
						"Shoot'em Up - Racing":'Shoot Em Up,Racing',
						"Shoot'em Up - SEUCK":'Shoot Em Up',
						"Shoot'em Up - Scramble":'Shoot Em Up',
						"Shoot'em Up - Space Invaders":'Shoot Em Up',
						"Shoot'em Up - Uridium":'Shoot Em Up',
						"Shoot'em Up - V-Scrolling":'Shoot Em Up,Vertical',
						"Shoot'em Up - Versus":'Shoot Em Up,Versus',
						"Shoot'em Up - Vertical":'Shoot Em Up,Vertical',
						"Shoot'em Up - [uncategorized]":'Shoot Em Up',
						"Shoot'em Up – 3D":'Shoot Em Up,3D',
						"Shoot'em Up – Horizontal":'Shoot Em Up,Side Scroller',
						"Shoot-'Em-Up":'Shoot Em Up',
						"Shoot-'em-Up":'Shoot Em Up',
						'Shooter': 'Shooter',
						'Shooter / 1st Person': 'Shooter,1st Person',
						'Shooter / 3rd Person': 'Shooter,3rd Person',
						'Shooter / Driving': 'Shooter,Driving',
						'Shooter / Driving (chase view)': 'Shooter,Driving,3rd Person',
						'Shooter / Driving Vertical': 'Shooter,Driving,Vertical',
						'Shooter / Field': 'Shooter,Field',
						'Shooter / Flying': 'Shooter,Flying',
						'Shooter / Flying (chase view)': 'Shooter,Flying,3rd Person',
						'Shooter / Flying 1st Person': 'Shooter,Flying,1st Person',
						'Shooter / Flying Horizontal': 'Shooter,Flying,Horizontal',
						'Shooter / Flying Vertical': 'Shooter,Flying,Vertical',
						'Shooter / Gallery': 'Shooter,Gallery',
						'Shooter / Gun': 'Shooter,Gun',
						'Shooter / Misc. Horizontal': 'Shooter,Horizontal',
						'Shooter / Misc. Vertical': 'Shooter,Vertical',
						'Shooter / Versus': 'Shooter,Versus',
						'Shooter / Walking': 'Shooter,Walking',
						'Shooter Large': 'Shooter',
						'Shooter Scrolling': 'Shooter,Side Scroller',
						'Shooter Small': 'Shooter',
						'Shougi': 'Shougi',
						'Shuffleboard': 'Shuffleboard',
						'Side Scroller': 'Side Scroller',
						'Side-Scrolling': 'Side Scroller',
						'Sim': 'Simulation',
						'Simulation': 'Simulation',
						'Simulation - Flight (Civil)': 'Flight Simulator',
						'Simulation - Flight (Military)': 'Flight Simulator',
						'Simulation - Marine': 'Simulation,Water',
						'Simulation - Miscellaneous': 'Simulation',
						'Simulation - Space': 'Simulation,Space',
						'Simulation - Spy': 'Simulation,Spy',
						'Simulation - Tank': 'Simulation,Tank',
						'Skateboard': 'Skateboarding',
						'Skateboarding': 'Skateboarding',
						'Skating': 'Skating',
						'Skiing': 'Skiing',
						'SkyDiving': 'Sky Diving',
						'Sliding': 'Sliding',
						'Slot Machine': 'Casino,Slot Machine',
						'Slot Machine / Reels': 'Slot Machine,Reels',
						'Slot Machine / Video Slot': 'Slot Machine,Video Slot',
						'Small Spaceship': 'Space',
						'Snake': 'Snake',
						'Snow / Water': 'Snow,Water',
						'Snowboarding': 'Snowboarding',
						'Soccer': 'Sports,Soccer',
						'Soccer (Arcade)': 'Sports,Soccer,Arcade',
						'Soccer (Manager)': 'Sports,Soccer,Management',
						'Space': 'Space',
						'Sports': 'Sports',
						'Sports - American Football': 'Sports,Football',
						'Sports - Athletics': 'Sports',
						'Sports - Baseball': 'Sports,Baseball',
						'Sports - Basketball': 'Sports,Basketball',
						'Sports - Bowling': 'Sports,Bowling',
						'Sports - Boxing': 'Sports,Boxing',
						'Sports - Cricket': 'Sports,Cricket',
						'Sports - Cycling': 'Sports,Cycling',
						'Sports - Darts': 'Sports,Darts',
						'Sports - Fighting': 'Sports,Fighting',
						'Sports - Football': 'Sports,Football',
						'Sports - Football/Soccer': 'Sports,Soccer',
						'Sports - Golf': 'Sports,Golf',
						'Sports - Ice Hockey': 'Sports,Hockey',
						'Sports - Icehockey': 'Sports,Hockey',
						'Sports - Miscellaneous': 'Sports',
						'Sports - Multi-Event': 'Sports',
						'Sports - Rugby': 'Sports,Rugby',
						'Sports - Shooting': 'Sports,Shooting',
						'Sports - Skating': 'Sports,Skating',
						'Sports - Skiing': 'Sports,Skiing',
						'Sports - Snooker': 'Sports,Billiards',
						'Sports - Snooker/Pool': 'Sports,Billiards',
						'Sports - Squash': 'Sports,Squash',
						'Sports - Table Tennis': 'Sports,Table Tennis',
						'Sports - Tennis': 'Sports,Tennis',
						'Sports - Volleyball': 'Sports,Volleyball',
						'Sports - Watersports': 'Sports,Watersports',
						'Sports - Wrestling': 'Sports,Wrestling',
						'Sports / Armwrestling': 'Sports,Arm Wrestling',
						'Sports / Baseball': 'Sports,Baseball',
						'Sports / Basketball': 'Sports,Basketball',
						'Sports / Bowling': 'Sports,Bowling',
						'Sports / Boxing': 'Sports,Boxing',
						'Sports / Darts': 'Sports,Darts',
						'Sports / Fishing': 'Sports,Fishing',
						'Sports / Football': 'Sports,Football',
						'Sports / Golf': 'Sports,Golf',
						'Sports / Horse Racing': 'Sports,Horse Racing',
						'Sports / Misc.': 'Sports,Miscellaneous',
						'Sports / Soccer': 'Sports,Soccer',
						'Sports / Track & Field': 'Sports,Track and Field',
						'Sports / Wrestling': 'Sports,Wrestling',
						'Sports – Bowling': 'Sports,Bowling',
						'Sports – Football/Soccer': 'Sports,Soccer',
						'Sports – Miscellaneous': 'Sports,Miscellaneous',
						'Sports/Baseball': 'Sports,Baseball',
						'Sports/Basketball': 'Sports,Basketball',
						'Sports/Boxing': 'Sports,Boxing',
						'Sports/Cricket': 'Sports,Cricket',
						'Sports/Cycling': 'Sports,Cycling',
						'Sports/Fighting': 'Sports,Fighting',
						'Sports/Football': 'Sports,Football',
						'Sports/Golf': 'Sports,Golf',
						'Sports/Hockey': 'Sports,Hockey',
						'Sports/Multi-Event': 'Sports',
						'Sports/Olympic': 'Sports,Olympic',
						'Sports/Pool and Dart': 'Sports,Billiards',
						'Sports/Skating': 'Sports,Skating',
						'Sports/Skiing': 'Sports,Skiing',
						'Sports/Snowboarding': 'Sports,Snowboarding',
						'Sports/Soccer': 'Sports,Soccer',
						'Sports/Tennis': 'Sports,Tennis',
						'Sports/Track & Field': 'Sports,Track and Field',
						'Sports/Volleyball': 'Sports,Volleyball',
						'Sports/Watersports': 'Sports,Watersports',
						'Sports/Wrestling': 'Sports,Wrestling',
						'Stacking': 'Stacking',
						'Static': 'Static',
						'Stealth': 'Stealth',
						'Stock Car': 'Racing',
						'Strategy': 'Strategy',
						'Strategy - Company': 'Strategy',
						'Strategy - Detective': 'Strategy,Mystery',
						'Strategy - Life': 'Strategy,Virtual Life',
						'Strategy - Miscellaneous': 'Strategy,Miscellaneous',
						'Strategy - Politics': 'Strategy',
						'Strategy - Trading': 'Strategy',
						'Strategy - War': 'Strategy,War',
						'Strategy – Action': 'Strategy,Action',
						'Strategy – Company': 'Strategy',
						'Street': 'Street',
						'Submarine': 'Submarine',
						'Sumo': 'Sumo Wrestling',
						'Surfing': 'Surfing',
						'Surround': 'Surround',
						'Survival Horror': 'Survival,Horror',
						'Swimming': 'Swimming',
						'System / BIOS': 'System,BIOS',
						'System / Device': 'System,Device',
						'Tabletop': 'Tabletop',
						'Tabletop / Mahjong * Mature *': 'Tabletop,Mahjong,Adult',
						'Tabletop / Misc.': 'Tabletop,Miscellaneous',
						'Tactical': 'Tactical,Strategy',
						'Tactics': 'Tactical,Strategy',
						'Tank': 'Tank',
						'Tennis': 'Sports,Tennis',
						'Test': None,
						'Text': 'Text Based',
						'Text-Based': 'Text Based',
						'Third-Person': '3rd Person',
						'Timing': 'Timing',
						'Top Down': 'Field',
						'Toss': 'Toss',
						'Track and Field': 'Track and Field',
						'Traditional': 'Traditional',
						'Train': 'Train',
						'Tree - Plant': 'Planting,Nature',
						'Trivia': 'Trivia',
						'Trivia / Game Show': 'Trivia,Game Show',
						'Truck': 'Trucking',
						'Turn-Based': 'Turn Based',
						'Turn Based':'Turn Based',
						'Turnbased': 'Turn Based',
						'Tycoon': 'Management',
						'Utilities': 'Utilities',
						'Vehicle Simulation': 'Driving,Simulation',
						'Versus': 'Versus',
						'Versus Co-op': 'Versus,Co-Op',
						'Vertical': 'Vertical',
						'Video': 'Video',
						'Video Slot': 'Casino,Video Slot',
						'Videos': 'Video',
						'Virtual Life': 'Virtual Life,Simulation',
						'Visual Novel': 'Visual Novel',
						'Volley - Soccer': 'Sports,Soccer',
						'Volleyball': 'Sports,Volleyball',
						'WWII': 'War',
						'Wakeboarding': 'Wakeboarding,Water',
						'Walking': 'Walking',
						'Wargame': 'War',
						'Water': 'Water',
						'Whac-A-Mole': 'Whac-A-Mole',
						'Whac-A-Mole / Hammer': 'Whac-A-Mole',
						'Wrestling': 'Wrestling',
						'[uncategorized]': None,
						'Ball & Paddle / Breakout * Mature *':'Ball and Paddle,Breakout,Adult',
						'Ball & Paddle / Jump and Touch':'Ball and Paddle,Jumping',
						'Ball & Paddle / Misc.':'Ball and Paddle,Miscellaneous',
						'Ball & Paddle / Pong':'Ball and Paddle,Pong',
						'Board Game / Bridge Machine':'Board Game',
						'Calculator / Math Game Learning':'Calculator,Educational,Math',
						'Calculator / Pocket Computer':'Calculator,Pocket Device',
						'Calculator / Talking Calculator':'Calculator',
						'Casino / Cards * Mature *':'Casino,Card,Adult',
						'Casino / Lottery':'Casino,Gambling',
						'Casino / Misc. * Mature *':'Casino,Miscellaneous,Adult',
						'Casino / Multi-Games':'Casino,Mini-Games',
						'Casino / Roulette':'Casino,Roulette',
						'Climbing / Mountain - Wall':'Climbing',
						'Computer / Child Computer':'Computer',
						'Computer / Development System':'Computer,Development System',
						'Computer / Educational Game':'Computer,Educational',
						'Computer / Laptop - Notebook - Portable':'Computer,Portable Device',
						'Computer / Microcomputer':'Computer',
						'Computer / Milling':'Computer',
						'Computer / Pocket PC':'Computer,Pocket Device',
						'Computer / Programming Machine':'Computer,Development System',
						'Computer / Video Production':'Computer,Video',
						'Computer / Workstation - Server':'Computer,Workstation',
						'Driving / Catch':'Driving,Catch',
						'Driving / Demolition Derby':'Driving,Demolition Derby',
						'Driving / Guide and Collect':'Driving,Collecting',
						'Driving / Guide and Shoot':'Driving,Shooter',
						'Driving / Landing':'Driving',
						'Driving / Motorbike':'Driving,Motorcycle',
						'Driving / Plane':'Driving,Flying',
						'Driving / Race 1st Person':'Driving,Racing,1st Person',
						'Driving / Race Bike':'Driving,Racing,Biking',
						'Electromechanical / Bingo':'Electromechanical,Bingo',
						'Electromechanical / Change Money':'Electromechanical',
						'Electromechanical / Utilities':'Electromechanical',
						'Fighter / Field':'Fighter,Field',
						'Fighter / Misc.':'Fighter,Miscellaneous',
						'Fighter / Versus Co-op':'Fighter,Versus,Co-Op',
						'Game Console / Home Videogame Console Expansion':'Console,Home Videogame',
						'Handheld / Child Computer':'Handheld',
						'Handheld / E-Book Reading':'Handheld,E-Book',
						'Handheld / Handpuppet Toy':'Handheld',
						'Handheld / Home Videogame Console':'Handheld,Console,Home Videogame',
						'Maze / Ball Guide':'Maze,Ball Guide',
						'Maze / Blocks':'Maze,Blocks',
						'Maze / Blocks * Mature *':'Maze,Blocks,Adult',
						'Maze / Collect & Put':'Maze,Collecting',
						'Maze / Collect * Mature *':'Maze,Collecting,Adult',
						'Maze / Cross':'Maze',
						'Maze / Defeat Enemies':'Maze,Defeat Enemies',
						'Maze / Digging':'Maze,Digging',
						'Maze / Digging * Mature *':'Maze,Digging,Adult',
						'Maze / Driving':'Maze,Driving',
						'Maze / Driving * Mature *':'Maze,Driving,Adult',
						'Maze / Escape':'Maze,Escape',
						'Maze / Escape * Mature *':'Maze,Escape,Adult',
						'Maze / Fighter':'Maze,Fighter',
						'Maze / Marble Madness':'Maze,Ball Guide',
						'Maze / Misc.':'Maze,Miscellaneous',
						'Maze / Move and Sort':'Maze,Move and Sort',
						'Maze / Outline':'Maze',
						'Maze / Paint':'Maze,Paint',
						'Maze / Run Jump':'Maze,Run and Jump',
						'Maze / Shooter Large':'Maze,Shooter',
						'Medal Game / Action':'Action',
						'Medal Game / Adventure':'Adventure',
						'Medal Game / Cards':'Card',
						'Medal Game / Coin Pusher':'Coin Pusher',
						'Medal Game / Compilation':'Compilation',
						'Medal Game / Dance':'Dance',
						'Medal Game / Driving':'Driving',
						'Medal Game / Horse Racing':'Horse Racing',
						'Medal Game / Timing':'Timing',
						'Medal Game / Versus':'Versus',
						'Medical Equipment / ECG Unit':'Miscellaneous,Medical Equipment',
						'Misc. / Credit Card Terminal':'Miscellaneous,Terminal',
						'Misc. / DVD Player':'Miscellaneous,DVD Device',
						'Misc. / DVD Reader-Writer':'Miscellaneous,DVD Device',
						'Misc. / Dot-Matrix Display':'Miscellaneous,Dot-Matrix Display',
						'Misc. / Drum Machine':'Miscellaneous,Drum Machine',
						'Misc. / Educational Game':'Miscellaneous,Educational',
						'Misc. / Electronic Game':'Miscellaneous,Handheld',
						'Misc. / Gambling Board':'Miscellaneous,Gambling',
						'Misc. / Graphic Tablet':'Miscellaneous,Tablet',
						'Misc. / Hot-air Balloon':'Miscellaneous,Flying,Hot-air Balloon',
						'Misc. / In Circuit Emulator':'Miscellaneous,Circuit Emulator',
						'Misc. / Laserdisc Player':'Miscellaneous,Laserdisc Player',
						'Misc. / Laserdisc Simulator':'Miscellaneous,Laserdisc Player',
						'Misc. / Multiplay':'Miscellaneous,Mini-Games',
						'Misc. / Order':'Miscellaneous,Ordering',
						'Misc. / Pachinko':'Miscellaneous,Pachinko',
						'Misc. / Pinball':'Miscellaneous,Pinball',
						'Misc. / Pinball * Mature *':'Miscellaneous,Pinball,Adult',
						'Misc. / Portable Media Player':'Miscellaneous,Portable Device',
						'Misc. / Prediction':'Miscellaneous,Prediction',
						'Misc. / Print Club':'Miscellaneous,Print Club',
						'Misc. / Redemption':'Miscellaneous,Redemption',
						'Misc. / Robot Control':'Miscellaneous,Robot Control',
						'Misc. / Satellite Receiver':'Miscellaneous,Satellite Receiver',
						'Misc. / Shoot Photos':'Miscellaneous,Shoot Photos',
						'Misc. / Speech Synthesizer':'Miscellaneous,Speech Synthesizer',
						'Misc. / Temperature Controller':'Miscellaneous,Temperature Controller',
						'Misc. / Time-Access Control TerminalTime and access control terminal':'Miscellaneous,Terminal',
						'Misc. / Unknown':'Miscellaneous',
						'Misc. / VTR Control':'Miscellaneous,VTR Control',
						'Misc. / Virtual Environment':'Miscellaneous,Virtual Environment',
						'Misc. / Wavetables Generator':'Miscellaneous,Wavetables Generator',
						'MultiGame / Compilation * Mature *':'Mini-Games,Compilation,Adult',
						'MultiGame / Gambling':'Mini-Games,Gambling',
						'MultiGame / Gambling Board':'Mini-Games,Gambling',
						'MultiGame / Mini-Games':'Mini-Games',
						'Multiplay / Cards':'Mini-Games,Card',
						'Multiplay / Compilation':'Mini-Games,Compilation',
						'Multiplay / Mini-Games':'Mini-Games',
						'Multiplay / Mini-Games * Mature *':'Mini-Games,Adult',
						'Multiplay / Misc. * Mature *':'Mini-Games,Adult',
						'Music / Audio Sequencer':'Music,Audio',
						'Music / Drum Machine':'Music,Drum Machine',
						'Music / JukeBox':'Music,Player',
						'Music / MIDI Player':'Music,Player',
						'Music / Player':'Music,Player',
						'Music / Tone Generator':'Music,Tone Generator',
						'Platform / Run Jump * Mature *':'Platform,Run and Jump,Adult',
						'Platform / Shooter':'Platform,Shooter',
						'Printer / 3D Printer':'Printer',
						'Printer / Barcode Printer':'Printer',
						'Printer / Laser Printer':'Printer',
						'Printer / Matrix Printer':'Printer',
						'Printer / Thermal Printer':'Printer',
						'Puzzle / Cards':'Puzzle,Card',
						'Puzzle / Match * Mature *':'Puzzle,Matching,Adult',
						'Puzzle / Maze':'Puzzle,Maze',
						'Puzzle / Misc. * Mature *':'Puzzle,Adult',
						'Puzzle / Outline':'Puzzle,Outline',
						'Puzzle / Outline * Mature *':'Puzzle,Outline,Adult',
						'Puzzle / Paint * Mature *':'Puzzle,Paint,Adult',
						'Puzzle / Reconstruction * Mature *':'Puzzle,Reconstruction,Adult',
						'Puzzle / Sliding':'Puzzle,Sliding',
						'Puzzle / Sliding * Mature *':'Puzzle,Sliding,Adult',
						'Puzzle / Toss * Mature *':'Puzzle,Toss,Adult',
						'Quiz / Questions in Chinese':'Quiz,Chinese',
						'Quiz / Questions in English':'Quiz,English',
						'Quiz / Questions in English * Mature *':'Quiz,English,Adult',
						'Quiz / Questions in French':'Quiz,French',
						'Quiz / Questions in German':'Quiz,German',
						'Quiz / Questions in Italian':'Quiz,Italian',
						'Quiz / Questions in Japanese * Mature *':'Quiz,Japanese,Adult',
						'Quiz / Questions in Korean':'Quiz,Korean',
						'Quiz / Questions in Spanish':'Quiz,Spanish',
						'Rhythm / Instruments':'Rhythm,Instruments',
						'Rhythm / Misc.':'Rhythm,Miscellaneous',
						'Shooter / Command':'Shooter,Command',
						'Shooter / Driving 1st Person':'Shooter,Driving,1st Person',
						'Shooter / Driving Diagonal':'Shooter,Driving,Isometric',
						'Shooter / Driving Horizontal':'Shooter,Driving,Horizontal',
						'Shooter / Flying Diagonal':'Shooter,Flying,Isometric',
						'Shooter / Flying Horizontal * Mature *':'Shooter,Flying,Horizontal,Adult',
						'Shooter / Flying Vertical * Mature *':'Shooter,Flying,Vertical,Adult',
						'Shooter / Gallery * Mature *':'Shooter,Gallery,Adult',
						'Shooter / Misc.':'Shooter,Miscellaneous',
						'Shooter / Motorbike':'Shooter,Motorcycle',
						'Shooter / Outline * Mature *':'Shooter,Outline,Adult',
						'Shooter / Submarine':'Shooter,Submarine',
						'Shooter / Underwater':'Shooter,Underwater',
						'Slot Machine / Video Slot * Mature *':'Slot Machine,Video Slot,Adult',
						'Sports / Bull Fighting':'Sports,Bull Fighting',
						'Sports / Dodgeball':'Sports,Dodgeball',
						'Sports / Gun':'Sports,Gun',
						'Sports / Hang Gliding':'Sports,Hang Gliding',
						'Sports / Hockey':'Sports,Hockey',
						'Sports / Horseshoes':'Sports,Horseshoes',
						'Sports / Multiplay':'Sports,Mini-Games',
						'Sports / Ping Pong':'Sports,Pong',
						'Sports / Pool':'Sports,Pool',
						'Sports / Pool * Mature *':'Sports,Pool,Adult',
						'Sports / Rugby Football':'Sports,Rugby',
						'Sports / Shuffleboard':'Sports,Shuffleboard',
						'Sports / Skateboarding':'Sports,Skateboarding',
						'Sports / Skiing':'Sports,Skiing',
						'Sports / SkyDiving':'Sports,Sky Diving',
						'Sports / Sumo':'Sports,Sumo Wrestling',
						'Sports / Swimming':'Sports,Swimming',
						'Sports / Tennis':'Sports,Tennis',
						'Sports / Volleyball':'Sports,Volleyball',
						'Tabletop / Cards':'Tabletop,Card',
						'Tabletop / Hanafuda':'Tabletop,Hanafuda',
						'Tabletop / Hanafuda * Mature *':'Tabletop,Hanafuda,Adult',
						'Tabletop / Mahjong':'Tabletop,Mahjong',
						'Tabletop / Othello - Reversi':'Tabletop,Othello,Reversi',
						'Tabletop / Renju':'Tabletop,Renju',
						'Tabletop / Shougi':'Tabletop,Shougi',
						'Telephone / ComputerPhone':'Telephone',
						'Telephone / Mobile Phone - Smartphone':'Telephone,Mobile Phone,Smartphone',
						'Utilities / Arcade Switcher':'Utilities',
						'Utilities / Arcade System':'Utilities',
						'Utilities / Electronic Digital Thermostat':'Utilities,Thermostat',
						'Utilities / TV Test Pattern Generator':'Utilities,Test Pattern Generator',
						'Utilities / Test':'Utilities,Test',
						'Utilities / Test ROM':'Utilities,Test',
						'Utilities / Update':'Utilities,Update',
						'Utilities / Weather Station':'Utilities,Weather Station',
						'Utilities / Weight Scale':'Utilities,Weight Scale',
						'Whac-A-Mole / Footsteps':'Whac-A-Mole',
						'Whac-A-Mole / Gun':'Whac-A-Mole,Gun',
						'Whac-A-Mole / Shooter':'Whac-A-Mole,Shooter',
						'Driving / Truck Guide':'Driving,Trucking',
						'Tabletop / Multi-Games':'Tabletop,Mini-Games',
						'Misc. / Clock':'Miscellaneous',
						'Utilities / EPROM Programmer':'Utilities,Test',
						'Computer / Portable Digital Teletype':'Computer,Portable Device',
						'Computer / Misc.':'Computer,Miscellaneous',
						'Utilities / Modem':'Utilities,Modem',
						'Coin Pusher / Misc.':'Miscellaneous,Coin Pusher',
						'Electromechanical / Crane Machines':'Electromechanical,Crane',
						'Board Game / Cards':'Board Game,Card',
						'Board Game / Checker Machine':'Board Game,Checkers',
						'Board Game / Dame Machine':'Board Game',
						'Casino / Horse Racing':'Casino,Horse Racing',
						'Casino / Unknown':'Casino',
						'Climbing / Building':'Climbing,Building',
						'Computer / Cablenet Controller':'Computer',
						'Computer Graphic Workstation / Broadcast Television':'Computer,Workstation',
						'Driving / Ambulance Guide':'Driving',
						'Driving / FireTruck Guide':'Driving',
						'Driving / Motorbike (Motocross)':'Driving,Motorcycle',
						'Fighter / Asian 3D':'Fighter,Asian,3D',
						'Fighter / Compilation':'Fighter,Compilation',
						'Fighter / Driving Vertical':'Fighter,Driving,Vertical',
						'Fighter / Multiplay':'Fighter,Mini-Games',
						'Fighter / Versus * Mature *':'Fighter,Versus,Adult',
						'Game Console / Fitness Game':'Console,Fitness',
						'Maze / Integrate':'Maze',
						'Maze / Ladders':'Maze,Climbing',
						'Medal Game / Bingo':'Bingo',
						'Medal Game / Casino':'Casino',
						'Medal Game / Crane Machines':'Electromechanical,Crane',
						'Medical Equipment / Visual Field Screener':'Medical Equipment',
						'Misc. / Car Voice Alert':'Miscellaneous',
						'Misc. / Cash Counter':'Miscellaneous',
						'Misc. / Dartboard':'Miscellaneous,Darts',
						'Misc. / Device Programmer':'Miscellaneous,Development System',
						'Misc. / Digital MultiMeter (DMM)':'Miscellaneous',
						'Misc. / Dog Sitter':'Miscellaneous',
						'Misc. / EPROM Programmer':'Miscellaneous,Development System',
						'Misc. / Electronic Typewriter':'Miscellaneous,Electronic Typewriter',
						'Misc. / Engine Control Unit':'Miscellaneous,Engine Control Unit',
						'Misc. / Fingerprint Reader':'Miscellaneous,Fingerprint Reader',
						'Misc. / Graphics Display Controller':'Miscellaneous,Graphics',
						'Misc. / Jump and Bounce':'Miscellaneous,Jump and Bounce',
						'Misc. / Mini-Games':'Miscellaneous,Mini-Games',
						'Misc. / Reflex':'Miscellaneous,Reflex',
						'Misc. / Response Time':'Miscellaneous,Reflex',
						'Misc. / Similar Bowling Game':'Miscellaneous,Bowling',
						'Misc. / Spank * Mature *':'Miscellaneous,Adult',
						'Misc. / Toy Cars':'Miscellaneous,Toy Cars',
						'Misc. / Toy Robot':'Miscellaneous,Toy Robot',
						'Misc. / Versus':'Miscellaneous,Versus',
						'Music / Instruments':'Music,Instruments',
						'Platform / Maze':'Platform,Maze',
						'Printer / Handbook':'Printer',
						'Puzzle / Reconstruction':'Puzzle,Reconstruction',
						'Shooter / Flying * Mature *':'Shooter,Flying,Adult',
						'Sports / Cards':'Sports,Card',
						'Sports / Handball':'Sports,Handball',
						'Sports / Volley - Soccer':'Sports,Volleyball,Soccer',
						'Tabletop / Go':'Tabletop',
						'Tabletop / Match * Mature *':'Tabletop,Matching,Adult',
						'Tabletop / Multiplay':'Tabletop,Mini-Games',
						'Tabletop / Othello - Reversi * Mature *':'Tabletop,Othello,Reversi,Adult',
						'Telephone / Car Phone':'Telephone',
						'Telephone / Landline Phone':'Telephone',
						'Utilities / Devices Communication':'Utilities',
						'Utilities / Disk Unit':'Utilities',
						'Utilities / Monitor':'Utilities,Monitor',
						'Utilities / Network Processor':'Utilities,Network Processor',
						'Utilities / Redemption Board':'Utilities,Redemption',
						'Whac-A-Mole / Fighter':'Whac-A-Mole,Fighter',
						'1st-person':'1st Person',
						'2D scrolling':'2D,Side Scroller',
						'3rd-person (Other)':'3rd Person',
						'4X':None,
						'Africa':'Africa',
						'Agricultural / Industrial':'Planting,Industrial',
						'Anime / Manga':'Anime,Manga',
						'Artillery':'Artillery',
						'Asia':'Asian',
						'Athletics':'Sports',
						'Audio game':'Audio',
						'Augmented reality':'Augmented Reality',
						'Automobile':'Driving',
						"Beat 'em up / Brawler":"Beat Em Up",
						'Behind view':'3rd Person',
						'Bike / Bicycling':'Biking',
						"Bird's-eye view":"Field",
						'Cards / Tiles':'Card,Tile',
						'Casino / Gambling':'Casino,Gambling',
						'China (Ancient/Imperial)':'Historic',
						'Cinematic camera':'Cinematic',
						'City Building / Construction Simulation':'Building,Construction,Simulation',
						'Classical antiquity':'Historic',
						'Cold War':'War',
						'Comedy':'Comedy',
						'Contemporary':'Modern',
						'Crime':'Crime',
						'Currency':'Currency',
						'Customization / Outfit / Skin':'Customization',
						'Cyberpunk / Dark Sci-Fi':'Cyberpunk,Sci-Fi',
						'DLC / Add-on':'Extra Content',
						'Darts / Target Shooting':'Darts,Shooting',
						'Dating Simulation':'Dating Simulation',
						'Detective / Mystery':'Mystery',
						'Digital Extras':'Extra Content',
						'Direct Control':'Direct Control',
						'Ecology / Nature':'Nature',
						'Egypt (Ancient)':'Historic',
						'Europe':'Europe',
						'Extra Content/Game':'Extra Content',
						'Extras':'Extra Content',
						'Falling Block Puzzle':'Blocks,Puzzle',
						'Fixed / Flip-screen':'Fixed Screen',
						'Flight / Aviation':'Flying',
						'Football (American)':'Sports,Football',
						'Football (European) / Soccer':'Sports,Soccer',
						'Foreign Language':'Foreign Language',
						'Free-roaming camera':'3rd Person',
						'Full Motion Video (FMV)':'Full Motion Video',
						'Game Mode':None,
						'Game Show / Trivia / Quiz':'Game Show,Trivia,Quiz',
						'Geography':'Geography',
						'Graphic Adventure':'Graphic Adventure',
						'Graphics / Art':'Graphics,Art',
						'Hack and Slash':'Hack and Slash',
						'Health / Nutrition':'Health',
						'Healthcare':'Health',
						'Hidden object':'Hidden Object',
						'Historical Events':'Historic',
						'History':'Historic',
						'Horse / Derby':'Horse Racing',
						'Hovercraft':'Hovercraft',
						'Interactive Book':'Interactive Book',
						'Interactive Fiction / Text Adventure':'Interactive Fiction,Adventure,Text Based',
						'Interwar':'War',
						'Item':None,
						'Japan (Ancient/Classical/Medieval)':'Historic',
						'Japanese-style Adventure':'Japanese,Adventure',
						'Japanese-style RPG (JRPG)':'JRPG',
						'Licensed':None,
						'Life / Social Simulation':'Life Simulation',
						'Managerial / Business Simulation':'Management,Simulation',
						'Map / Level':None,
						'Martial Arts':'Martial Arts',
						'Massively Multiplayer':'MMO',
						'Math / Logic':'Math,Logic',
						'Mecha / Giant Robot':'Mecha',
						'Medieval':'Medieval',
						'Meditative / Zen':'Meditative,Zen',
						'Mental training':'Mental Training',
						'Menu Structures':None,
						'Metroidvania':'Metroidvania',
						'Middle East':'Middle East',
						'Motion Control':'Motion Control',
						'Multiple Units/Characters Control':None,
						'Music / Rhythm':'Music,Rhythm',
						'NPC / Enemy':None,
						'Naval / Watercraft':'Naval,Watercraft',
						'North America':'North America',
						'Oceania':'Oceania',
						'Off-roading':'Off Road',
						'Olympiad / Mixed Sports':'Olympic,Sports',
						'Paddle / Pong':'Pong',
						'Party Game':'Party Game',
						'Persistent':None,
						'Physical Extras':'Extra Content',
						'Player Unit':None,
						'Point and Select':'Point and Click',
						'Pool / Snooker':'Billiards',
						'Post-Apocalyptic':'Post Apocalyptic',
						'Pre-school / Toddler':'Educational',
						'Prehistoric':'Historic',
						'Puzzle elements':'Puzzle',
						'Quick Time Events (QTEs)':'Full Motion Video',
						'RPG elements':'RPG',
						'Racing / Driving':'Racing,Driving',
						'Racquetball / Squash':'Sports,Racquetball,Squash',
						'Reading / Writing':'Reading,Writing',
						'Real-time strategy':'Real Time,Strategy',
						'Regional Differences':None,
						'Roguelike':'Roguelike',
						'Role-Playing (RPG)':'RPG',
						'Romance':'Romance',
						'Sailing / Boating':'Sailing,Boating',
						'Sandbox / Open World':'Sandbox,Open World',
						'Sci-Fi / Futuristic':'Sci-Fi,Futuristic',
						'Science':'Science',
						'Sea Pirates/Caribbean':'Sailing',
						'Side view':'Side Scroller',
						'Snowboarding / Skiing':'Snowboarding,Skiing',
						'Sociology':'Sociology',
						'South America':'South America',
						'Space Flight':'Space,Flying',
						'Special Edition':None,
						'Spy / Espionage':'Spy',
						'Steampunk':'Steampunk',
						'Story / Mission':'Mission Based',
						'Strategy/Tactics':'Strategy,Tactical',
						'Street Racing':'Racing',
						'Survival':'Survival',
						'Tactical RPG':'Tactical,RPG',
						'Tactical Shooter':'Tactical,Shooter',
						'Text Parser':'Text Based',
						'Text-based / Spreadsheet':'Text Based',
						'Thriller':'Thriller',
						'Tile Matching Puzzle':'Tile,Matching,Puzzle',
						'Time Management':'Reflex',
						'Timed Input':'Reflex',
						'Top-down':'Field',
						'Tower Defense':'Tower Defense',
						'Track Racing':'Racing',
						'Trading / Collectible Card':'Card Battle',
						'Transport':'Driving',
						'Tricks / Stunts':'Stunts',
						'Turn-based':'Turn Based',
						'Turn-based strategy':'Turn Based,Strategy',
						'Typing':'Typing',
						'Vehicle Simulator':'Driving,Simulation',
						'Vehicular Combat Simulator':'Car Combat,Driving,Simulation',
						'Video backdrop':'Video',
						'Voice Control':'Voice Control',
						'War':'War',
						'Western':'Western',
						'Word Construction':'Word Construction',
						'World War I':'War',
						'World War II':'War',
						'Bus':'Driving',
						'Industrial Age':'Historic',
						'Live action':'Live Action',
						'Paintball':'Paintball',
						'Ping Pong / Table Tennis':'Pong,Table Tennis',
						'Pre-Columbian Americas':'Historic',
						'Religion':'Religion',
						'Self-propelled Artillery':'Artillery',
						'actionadventure':'Action,Adventure',
						'adventure':'Adventure',
						'anco':None,
						'clicker':'Point and Click',
						'comic':'Comic',
						'detective':'Mystery',
						'educational':'Educational',
						'fantasy':'Fantasy',
						'football':'Sports,Football',
						'gambling':'Gambling',
						'games':'Mini-Games',
						'horror':'Horror',
						'humour':'Comedy',
						'manager':'Manager',
						'maze':'Maze',
						'movie':'Interactive Movie',
						'multidirectional':'Multi-Directional',
						'multievent':'Mini-Games',
						'multitype':'Mini-Games',
						'piracy':'Fantasy',
						'platform':'Platform',
						'poker':'Poker',
						'prison':'Prison',
						'puzzle':'Puzzle',
						'quiz':'Quiz',
						'racing':'Racing',
						'reaction':'Reflex',
						'robinhood':'Fantasy',
						'rome':'Historic',
						'rpg':'RPG',
						'scifi':'Sci-Fi',
						'scrabble':'Board Game',
						'scrolling':'Side Scroller',
						'seriallink':None,
						'shanghai':'Historic',
						'shapecombination':'Puzzle',
						'shooter':'Shooter',
						'sideways':'Side Scroller',
						'sierra':'Point and Click',
						'simulation':'Simulation',
						'single':None,
						'singlescreen':None,
						'snakes':None,
						'solomonskey':None,
						'space':'Space',
						'spaceharrier':'Space',
						'spaceinvaders':'Space',
						'spaceship':'Space',
						'splitscreen':'Split Screen',
						'sports':'Sports',
						'squad':None,
						'starships':'Flying,Space',
						'stategy':'Stategy',
						'stomp':None,
						'strategy':'Strategy',
						'streetfighter':'Fighter',
						'strippoker':'Card,Poker,Adult',
						'submarine':'Submarine',
						'swordandsorcery':'Fantasy',
						'swordsandsorcerey':'Fantasy',
						'swordsandsorcery':'Fantasy',
						'tabletennis':'Table Tennis',
						'tank':'Tank',
						'tennis':'Sports,Tennis',
						'territoryconquer':'Strategy',
						'tetris':'Puzzle',
						'text':'Adventure,Text Based',
						'textandgraphics':'Adventure,Text Based',
						'thrust':None,
						'timelimit':None,
						'todown':'Field',
						'tomclancy':None,
						'topdown':'Field',
						'trackandfield':'Sports,Track and Field',
						'trading':'Trading',
						'train':'Train,Simulation',
						'transport':'Driving',
						'tunnel':None,
						'turnbased':'Turn Based',
						'tv':None,
						'undead':None,
						'uridium':None,
						'utility':'Utilities',
						'vertical':'Vertical',
						'viking':'Historical',
						'virtualworld':'Virtual Life',
						'wahammer40000':None,
						'walkabout':'Walking',
						'wanderer':'Walking',
						'war':'War',
						'wargame':'War',
						'wildwest':'Western',
						'windsurfing':'Wind Surfing',
						'winter':'Snow',
						'wintergames':'Sports,Snow',
						'wizard':'Fantasy',
						'wonderboy':None,
						'wrestling':'Wrestling',
						'ww1':'War',
						'ww2':'War',
						'zaxxon':None,
						'zombie':'Zombie',
						'action':'Action',
						'adult':'Adult',
						'advenure':'Adventure',
						'angle':'Isometric',
						'arcade':'Arcade',
						'book':'Text Based',
						'cards':'Card',
						'chess':'Chess',
						'constructionkit':'Construction',
						'Construction':'Construction',
						'Breeding':'Breeding',
						'crime':'Crime',
						'espionage':'Spy',
						'firstperson':'1st Person',
						'government':'Management,Simulation',
						'interactivemovie':'Interactive Movie',
						'isometric':'Isometric',
						'math':'Math',
						'minigolf':'Golf',
						'pacman':'Arcade',
						'pointandclick':'Point and Click',
						'postapocalyptic':'Post-Apocalyptic',
						'prehistoric':'Historic',
						'progressive':'Progressive',
						'puzzler':'Puzzle',
						'rally':'Racing',
						'reversi':'Board Game',
						'scary':'Horror',
						'scfi':'Sci-Fi',
						'sciencefiction':'Sci-Fi',
						'shootemup':'Shoot Em Up',
						'shop':None,
						'solitaire':'Card',
						'sonic':'Arcade',
						'sowrdsandsorcery':'Fantasy',
						'sowrdsansorcery':'Fantasy',
						'spaceships':'Flying,Space',
						'spacestation':'Space',
						'specialforces':'War',
						'speedboats':'Boating',
						'squarenavigator':None,
						'squash':'Sports,Squash',
						'storybook':'Text Based',
						'superhero':'Fantasy',
						'tactic':'Strategy',
						'targetpractice':'Shooting',
						'terrorist':None,
						'terroristattack':None,
						'textandgraphic':'Graphic Adventure',
						'thriller':'Thriller',
						'tilearrangement':'Puzzle',
						'tileremoval':'Puzzle',
						'timetravel':None,
						'topdwon':'Field',
						'tower':'Tower',
						'trailblazer':None,
						'treasure':None,
						'tron':'Sci-Fi',
						'truck':'Driving,Trucking',
						'typing':'Typing',
						'vampire':'Horrot',
						'vector':'Vector Graphics',
						'verticalscrolling':'Vertical',
						'vietnam':'War',
						'volleyball':'Sports,Volleyball',
						'weird':'Miscellaneous',
						'western':'Western',
						'wireframe':None,
						'2d fighting':'Fighter,2D',
						'2d platformer':'Platform,2D',
						'3d fighting':'Fighter,3D',
						'3d platformer':'Platform,3D',
						'action rpg':'Action,RPG',
						'baseball':'Sports,Baseball',
						'basketball':'Sports,Basketball',
						"beat 'em up":"Beat Em Up",
						'bike racing':'Biking,Racing',
						'billiards':'Billiards',
						'board game':'Board Game',
						'bowling':'Bowling',
						'boxing':'Boxing',
						'compilation':'Compilation',
						'dance':'Dance',
						'demo':'Demo',
						'fighting':'Fighter',
						'first-person shooter':'1st Person,Shooter',
						'fishing':'Fishing',
						'flight simulation':'Flight Simulator',
						'futuristic racing':'Sci-Fi,Racing',
						'golf':'Sports,Golf',
						'historic':'Historic',
						'hockey':'Sports,Hockey',
						'hunting':'Hunting',
						'karaoke':'Karaoke',
						'kart racing':'Racing,Kart',
						'life simulation':'Virtual Life,Simulation',
						'martial arts':'Martial Arts',
						'modern day':'Modern Day',
						'motorcycle racing':'Racing,Motorcycle',
						'music':'Music',
						'off-road racing':'Racing,Off Road',
						'party':'Party Game',
						'pinball':'Pinball',
						'platformer':'Platform',
						'real-time strategy':'Real Time,Strategy',
						'rhythm':'Rhythm',
						'role-playing':'RPG',
						'run and gun':'Run and Gun',
						'sampler':'Demo',
						'sci-fi':'Sci-Fi',
						"shoot 'em up":"Shoot Em Up",
						'sim racing':'Simulation,Racing',
						'skateboarding':'Skateboarding',
						'snowboarding':'Snowboarding',
						'soccer':'Sports,Soccer',
						'software':None,
						'stealth action':'Action,Stealth',
						'surfing':'Sports,Surfing',
						'survival horror':'Survival,Horror',
						'tactical rpg':'Tactical,RPG',
						'third-person shooter':'3rd Person,Shooter',
						'truck racing':'Trucking,Racing',
						'turn-based strategy':'Turn Based,Strategy',
						'virtual pet':'Virtual Life,Simulation',
						'watercraft racing':'Watercraft,Racing',
						}
			name_out_new = ''
			for gg in name_list:
				if gg in genre_map.keys():
					if genre_map[gg] is not None:
						name_out_new = name_out_new+genre_map[gg]+','
				else:
					print('Genre not found in mapping %(current_genre)s'%{'current_genre':gg})
					if gg is not None:
						name_out_new = gg+','
			if len(name_out_new.replace(',,',','))>1:
				name_out_new = name_out_new.replace(',,',',')
			if name_out_new.endswith(','):
				name_out_new =name_out_new[:-1]
			return name_out_new.strip()
		else:
			return None

	def clean_years(self,year_in):
		if year_in is not None:
			year_map = {'1971':'1971',
					 '1972':'1972',
					  '1973':'1973',
					  '1974':'1974',
					  '1975':'1975',
					  '1976':'1976',
					  '1977':'1977',
					  '1978':'1978',
					  '1979':'1979',
					  '1980':'1980',
					  '1981':'1981',
					  '1982':'1982',
					  '1983':'1983',
					  '1984':'1984',
					  '1985':'1985',
					  '1986':'1986',
					  '1987':'1987',
					  '1987?':'1987',
					  '1988':'1988',
					  '1989':'1989',
					  '198?':None,
					  '198x':None,
					  '1990':'1990',
					  '1990?':'1990',
					  '1991':'1991',
					  '1992':'1992',
					  '1993':'1993',
					  '1994':'1994',
					  '1995':'1995',
					  '1996':'1996',
					  '1996?':'1996',
					  '1997':'1997',
					  '1998':'1998',
					  '1999':'1999',
					  '199?':None,
					  '19??':None,
					  '2000':'2000',
					  '2001':'2001',
					  '2002':'2002',
					  '2003':'2003',
					  '2004':'2004',
					  '2005':'2005',
					  '2006':'2006',
					  '2007':'2007',
					  '2008':'2008',
					  '2009':'2009',
					  '2010':'2010',
					  '2011':'2011',
					  '2012':'2012',
					  '2013':'2013',
					  '2014':'2014',
					  '2015':'2015',
					  '2016':'2016',
					  '2017':'2017',
					  '2018':'2018',
					  '2019':'2019',
					  '2020':'2020',
					  '2021':'2021',
					  '2022':'2022',
					  '2023':'2023',
					  '2024':'2024',
					  '2025':'2025',
					  '????':None,
					  '[unreleased]':None,
					  'Linel':None,
					  }
			if year_in in year_map.keys():
				year_out = year_map[year_in]
			else:
				print('Year not found in mapping %(current_year)s'%{'current_year':year_in})
				year_out = str(year_in)

			return year_out
		else:
			return None

	def clean_nplayers(self,name_in):
		if name_in is not None:
			name_out = name_in
			name_out = name_out.replace(' Players','')
			name_out = name_out.replace(' players','')
			name_out = name_out.replace(' Player','')
			name_out = name_out.replace(' player','')

			player_map = {  '0': None,
							'2 (1)':'1-2',
							'1': '1',
							'1 Co-Op': '1 Co-Op',
							'1 Player': '1',
							'1 or 2 Alternating ; CO-OP': '1-2 Alt,1-2 Co-Op',
							'1 or 2 Alternating; CO-OP': '1-2 Alt,1-2 Co-Op',
							'1 or 2 VS/Alternating': '1-2 VS,1-2 Alt',
							'1 or 2 alternating': '1-2 Alt',
							'1 to 4 alternating': '1-4 Alt',
							'1-10': '1-10',
							'1-10 Co-Op': '1-10 Co-Op',
							'1-10 Sim': '1-10 Sim',
							'1-10 VS': '1-10 VS',
							'1-12': '10+',
							'1-12 Sim': '10+ Sim',
							'1-16': '10+',
							'1-16 Sim': '10+ Sim',
							'1-16 VS': '10+ VS',
							'1-2': '1-2',
							'1-2 Alt': '1-2 Alt',
							'1-2 Alternating': '1-2 Alt',
							'1-2 Co-Op': '1-2 Co-Op',
							'1-2 Sim': '1-2 Sim',
							'1-2(2)': '1-2 Sim',
							'1-2 VS': '1-2 VS',
							'1-3': '1-3',
							'1-3 Alt': '1-3 Alt',
							'1-3 Co-Op': '1-3 Co-Op',
							'1-3 Sim': '1-3 Sim',
							'1-3 VS': '1-3 VS',
							'1-4': '1-4',
							'1-4 Players': '1-4',
							'1-4(1)': '1-4',
							'1-4 Alt': '1-4 Alt',
							'1-4 Co-Op': '1-4 Co-Op',
							'1-4 Sim': '1-4 Sim',
							'1 - 4  (4)': '1-4 Sim',
							'1-4 VS': '1-4 VS',
							'1-5': '1-5',
							'1-5 Co-Op': '1-5 Co-Op',
							'1-5 Sim': '1-5 Sim',
							'1 - 5 (2)': '1-2 Sim',
							'1 - 5 (5)': '1-5 Sim',
							'1-5 VS': '1-5 VS',
							'1-6': '1-6',
							'1-6 Alt': '1-6 Alt',
							'1-6 Co-Op': '1-6 Co-Op',
							'1-6 Sim': '1-6 Sim',
							'1-6 VS': '1-6 VS',
							'1-7': '1-7',
							'1-7 Sim': '1-7 Sim',
							'1-7 Alt': '1-7 Alt',
							'1-8': '1-8',
							'1-8 Alt': '1-8 Alt',
							'1-8 Co-Op': '1-8 Co-Op',
							'1-8 Sim': '1-8 Sim',
							'1-8 VS': '1-8 VS',
							'1-9 Alt': '1-9 Alt',
							'1 - 10 (1)': '1-10',
							'10': '1-10',
							'10 Co-Op': '1-10 Co-Op',
							'100': '10+',
							'100 Co-Op': '10+ Co-Op',
							'1000000000 Co-Op': '10+ Co-Op',
							'10P sim': '1-10 Sim',
							'11': '10+',
							'12': '10+',
							'12 Co-Op': '10+ Co-Op',
							'120 Co-Op': '10+ Co-Op',
							'128 Co-Op': '10+ Co-Op',
							'14 Co-Op': '10+ Co-Op',
							'15': '10+',
							'15 Co-Op': '10+ Co-Op',
							'150': '10+',
							'1500 Co-Op': '10+ Co-Op',
							'16': '10+',
							'16 Co-Op': '10+ Co-Op',
							'18': '10+',
							'18 Co-Op': '10+ Co-Op',
							'19 Co-Op': '10+ Co-Op',
							'1P': '1',
							'2': '2',
							'2 Co-Op': '1-2 Co-Op',
							'2 VS': '1-2 VS',
							'2-4s': '1-4 Sim',
							'20': '10+',
							'20 Co-Op': '10+ Co-Op',
							'2000': '10+',
							'2000 Co-Op': '10+ Co-Op',
							'21': '10+',
							'22': '10+',
							'22 Co-Op': '10+ Co-Op',
							'24': '10+',
							'24 Co-Op': '10+ Co-Op',
							'255': '10+',
							'2P alt': '1-2 Alt',
							'2P sim': '1-2 Sim',
							'2s': '1-2 Sim',
							'3': '1-3',
							'3 Co-Op': '1-3 Co-Op',
							'30': '10+',
							'30 Co-Op': '10+ Co-Op',
							'32': '10+',
							'32 Co-Op': '10+ Co-Op',
							'35': '10+',
							'36 Co-Op': '10+ Co-Op',
							'3P alt': '1-3 Alt',
							'3P sim': '1-3 Sim',
							'4': '1-4',
							'4 Co-Op': '1-4 Co-Op',
							'40': '10+',
							'40 Co-Op': '10+ Co-Op',
							'43': '10+',
							'46': '10+',
							'48': '10+',
							'4P alt': '1-4 Alt',
							'4P alt / 2P sim': '1-4 Alt,1-2 Sim',
							'4P sim': '1-4 Sim',
							'5': '1-5',
							'5 Co-Op': '1-5 Co-Op',
							'50': '10+',
							'50 Co-Op': '10+ Co-Op',
							'500 Co-Op': '10+ Co-Op',
							'5P alt': '1-5 Alt',
							'5P sim': '1-5 Sim',
							'6': '1-6',
							'6 Co-Op': '1-6 Co-Op',
							'60 Co-Op': '10+ Co-Op',
							'64': '10+',
							'64 Co-Op': '10+ Co-Op',
							'6P alt': '1-6 Alt',
							'6P sim': '1-6 Sim',
							'7': '1-7',
							'7 Co-Op': '1-7 Co-Op',
							'72': '10+',
							'7P alt': '1-7 Alt',
							'7P sim': '1-7 Sim',
							'8': '1-8',
							'8 Co-Op': '1-8 Co-Op',
							'8P alt': '1-8 Alt',
							'8P alt / 2P sim': '1-8 Alt,1-2 Sim',
							'8P sim': '1-8 Sim',
							'9': '1-9',
							'90': '10+',
							'96 Co-Op': '10+ Co-Op',
							'99': '10+',
							'9P alt': '1-9 Alt',
							'9P sim': '1-9 Sim',
							'9 Co-Op':'1-9 Co-Op',
							'6P alt / 2P sim': '1-6 Alt,1-2 Sim',
							'11 Co-Op':'10+ Co-Op',
							'???': None,
							'BIOS': None,
							'Device': None,
							'device': None,
							'Device ': None,
							'Non-arcade': None,
							'Pinball': None,
							'0 Co-Op': None,
							'1 - 12 (12)':'10+ Sim',
							'1 - 12 (2)':'1-2 Sim',
							'1 - 16 (4)':'1-4 Sim',
							'1 - 16 (2)':'1-2 Sim',
							'1 - 2 (1)':'1-2',
							'1 - 2 (2)':'1-2 Sim',
							'1 -  2 (2)':'1-2 Sim',
							'1 - 20 (2)':'1-2 Sim',
							'1 - 28 (4)':'1-4 Sim',
							'1 - 3 (1)':'1-3',
							'1 - 3 (3)':'1-3 Sim',
							'1 - 32 (2)':'1-2 Sim',
							'1 - 35 (1)':'10+',
							'1 - 4 (1)':'1-4',
							'1 - 4 (2)':'1-2 Sim',
							'1 - 4 (4)':'1-4 Sim',
							'1 - 5 (1)':'1-5',
							'1 - 6 (1)':'1-6',
							'1 - 6 (2)':'1-2 Sim',
							'1 - 6 (6)':'1-6 Sim',
							'1 - 8 (3)':'1-3 Sim',
							'1 - 64 (2)':'1-2 Sim',
							'2 - 2 (2)':'2 Co-Op',
							'1 - 72 (1)':'10+',
							'1 - 8 (1)':'1-8',
							'1 - 8 (2)':'1-2 Sim',
							'1 - 9 (2)':'1-2 Sim',
							'1 -2 (1)':'1-2',
							'1 -2 (2)':'1-2 Sim',
							'1 -20 (2)':'1-2 Sim',
							'1 -4 (2)':'1-2 Sim',
							'1-32(2)':'1-2 Sim',
							'1 - 15 (2)':'1-2 Sim',
							'2 - 5 (5)':'1-5 Sim',
							}

			if name_out in player_map.keys():
				name_out=player_map[name_out]
			else:
				print('NPlayer not found in mapping %(current_nplayer)s'%{'current_nplayer':name_out})
			if name_out is not None:
				return name_out.strip()
			else:
				return None
		else:
			return None

	def clean_match_data(self,dat_file_in):
		for ii,gg in enumerate(dat_file_in['datafile']['game']):
			dat_file_in['datafile']['game'][ii]['bookkeeping']['exact_match'] = False
			dat_file_in['datafile']['game'][ii]['bookkeeping']['fuzzy_match'] = False
		return dat_file_in

##General functions
def etree_to_dict(t):
	d = {t.tag: {} if t.attrib else None}
	children = list(t)
	if children:
		dd = defaultdict(list)
		for dc in map(etree_to_dict, children):
			for k, v in dc.items():
				dd[k].append(v)
		d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
	if t.attrib:
		d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
	if t.text:
		text = t.text.strip()
		if children or t.attrib:
			if text:
				d[t.tag]['#text'] = text
		else:
			d[t.tag] = text
	return d

def dict_to_etree(d):
	def _to_etree(d, root):
		if not d:
			pass
		elif isinstance(d, basestring):
			root.text = d
		elif isinstance(d, dict):
			for k,v in d.items():
				assert isinstance(k, basestring)
				if k.startswith('#'):
					assert k == '#text' and isinstance(v, basestring)
					root.text = v
				elif k.startswith('@'):
					assert isinstance(v, basestring)
					root.set(k[1:], v)
				elif isinstance(v, list):
					for e in v:
						_to_etree(e, ET.SubElement(root, k))
				else:
					_to_etree(v, ET.SubElement(root, k))
		else:
			raise TypeError('invalid type: ' + str(type(d)))
	assert isinstance(d, dict) and len(d) == 1
	tag, body = next(iter(d.items()))
	node = ET.Element(tag)
	_to_etree(body, node)
	return ET.tostring(node)

def string_to_bytes(string_in):
	string_out = None
	if string_in is not None:
		if 'k' in string_in.lower():
			number_in = string_in.lower().split('k')[0].strip().replace(',','')
			multiplier = 1024
		elif 'm' in string_in.lower():
			number_in = string_in.lower().split('m')[0].strip().replace(',','')
			multiplier = 1048576
		elif 'g' in string_in.lower():
			number_in = string_in.lower().split('g')[0].strip().replace(',','')
			multiplier = 1073741824
		else:
			number_in = string_in.lower().split('b')[0].strip().replace(',','')
			multiplier = 1
		string_out = str(int(float(number_in)*multiplier))
	return string_out

def get_crc32(filename):
	return zlib_csum(filename, zlib.crc32)

def zlib_csum(filename, func):
	csum = None
	# chunk_size = 1024
	chunk_size = 10485760 #10MB
	# with open(filename, 'rb') as f:
	with io.FileIO(filename, 'rb') as f: #Using FileIO as open fails on Android
		try:
			chunk = f.read(chunk_size)
			if len(chunk)>0:
				csum = func(chunk)
				while True:
					chunk = f.read(chunk_size)
					if len(chunk)>0:
						csum = func(chunk, csum)
					else:
						break
		finally:
			f.close()
	if csum is not None:
		csum = csum & 0xffffffff

	return '%X'%(csum & 0xFFFFFFFF)

def grouper(iterable, n, fillvalue=None):
	"Collect data into fixed-length chunks or blocks"
	# grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
	args = [iter(iterable)] * n
	return zip_longest(*args, fillvalue=fillvalue)

def select_column_and_value(db, sql, parameters=()):
	execute = db.execute(sql, parameters)
	fetch = execute.fetchone()
	return {k[0]: v for k, v in list(zip(execute.description, fetch))}