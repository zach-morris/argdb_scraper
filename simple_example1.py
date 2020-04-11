#Simplest Example

from resources.lib.argdb_scraper import *

#Settings
parsing_settings = {'logging':'info', #Use 'debug' or 'info' based on how much log info you want on the progress
					'log_to_file':False, #For debugging purposes, logging to a file if necessary
					'concurrent_processes':1, #Not used yet
					'overwrite_locals':False, #For efficiency, overwrite local variables when running script, or reuse available local variables in memory
					'overwrite_conversions':False, #Saving the parsed file conversions can be saved and is usually not overwritten, this will override that
					'match_response':'best', #How to respond to match decisions:  best (highest ratio=default) or query (it will ask you to choose)
					'keep_no_matches':True, #If no match is found, return same game dict with no merged data.  If false, nothing will be added to the merged dict (i.e. the game will be thrown out)
					'fuzzy_match_ratio':90.9, #only consider fuzzy matches with at least this score.  In testing, I've found anything higher than 90 is a prety close match
					'fuzzy_scoring_type':'token_set_ratio', #scoring ratio to use, see fuzzywuzzy manual for the scoring methods
					'max_fuzzy_matches':5, #Max number of matches for a fuzzy match.  For query matching it will give you this many choices to look at
					'use_converted_files':True, #Use the converted version of the file if it already exists
					'common_platforms':['Nintendo Entertainment System PD Games'], #A common name for the platform your scraping
					}
output_settings = {	'type':'IAGL', #Dat type to output.  This is currently the only option.  ARGDB will be added later
					'output_filename':'NES_PD_GAMES.xml', #Filename to output
					'header_name': 'Nintendo Entertainment System PD Games', #IAGL header will be populated with this
					'categories': 'Nintendo,PD Games', #IAGL header will be populated with this
					'save_output':True, #Simple trigger to turn on and of file saving after parsing
					'author':'Zach Morris', #Author for the IAGL header
					'base_url':'https://drive.google.com/', #Base URL for the IAGL header
					}

#Here's my 3 files
files = ['uc?export=download&id=11-S0be1FQqV_Lvn0e3st9AUtvimStZDg&name=/2048.nes',
		'uc?export=download&id=1lvwzcqBCrm4ODPEY9P6ih03uN7SyAiDe&name=/BladeBuster.nes',
		'uc?export=download&id=13_QczPj-5faspIj_kB2nNW8BUtE7yBP7&name=/dpadhero2.nes']

#Define your argdb scraper object
argdb_scraper = argdb_scraper(parsing_settings=parsing_settings,output_settings=output_settings)

#Initalize your dat file
dat_file_out = dict()
dat_file_out['datafile'] = dict()
#Bookkeeping can be empty in this example because we're not merging anything
dat_file_out['datafile']['bookkeeping'] = argdb_scraper.get_empty_datafile_bookkeeping_dict()
#Generate the header for the xml file
dat_file_out['datafile']['header'] = argdb_scraper.get_new_IAGL_header_dict(emu_name=output_settings['header_name'],emu_description=output_settings['header_name'],emu_category=output_settings['categories'],emu_version='010101',emu_date='040820',emu_author=output_settings['author'],emu_baseurl=output_settings['base_url'])

#Initialize a list of games
dat_file_out['datafile']['game'] = list()

#Populate the list of games by name/description and rom url
for ff in files:
	dat_file_out['datafile']['game'].append(argdb_scraper.get_new_IAGL_game_dict(name = ff.split('/')[-1].split('.')[0],description=ff.split('/')[-1].split('.')[0],rom_in={'@name':ff,'@size':'0'}))

#Save the xml file to ...resources/output/
if output_settings['save_output']:
	success = argdb_scraper.output_dat_file(dat_file_out,filename_in=output_settings['output_filename'],pop_these_keys_in=['bookkeeping'])