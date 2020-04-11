#Simplest Example

from resources.lib.argdb_scraper import *

#Settings
parsing_settings = {'logging':'debug', #Use 'debug' or 'info' based on how much log info you want on the progress
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
					'common_platforms':['Arcade'], #A common name for the platform your scraping
					}
output_settings = {	'type':'IAGL', #Dat type to output.  This is currently the only option.  ARGDB will be added later
					'output_filename':'Arcade_3_Game_Example_2.xml', #Filename to output
					'header_name': 'Arcade Games Example 2', #IAGL header will be populated with this
					'categories': 'Arcade', #IAGL header will be populated with this
					'save_output':True, #Simple trigger to turn on and of file saving after parsing
					'author':'Zach Morris', #Author for the IAGL header
					'base_url':'https://archive.org/download/', #Base URL for the IAGL header
					}

dat_info = [
	{'type': 'OVGDB','filename':'OpenVGDB 28.0.sqlite','platform':['Arcade'],'save_conversion':True}, #0, OVGDB, save converted file to json
	{'type': 'launchbox','filename':'Metadata.xml','platform':['Arcade'],'save_conversion':True}, #1, Launchbox, save converted file to json
	{'type': 'thegamesdb','filename':'dump_102419','platform':['Arcade'],'save_conversion':True}, #2, thegamesdb, save converted file to json
	]

#Here's my 3 files
files = ['MAME2003_Reference_Set_MAME0.78_ROMs_CHDs_Samples/roms/tmnt.zip',
		 'MAME2003_Reference_Set_MAME0.78_ROMs_CHDs_Samples/roms/puckman.zip',
		 'MAME2003_Reference_Set_MAME0.78_ROMs_CHDs_Samples/roms/captcomm.zip']

#Define your argdb scraper object
argdb_scraper = argdb_scraper(parsing_settings=parsing_settings,output_settings=output_settings)

#Initalize your dat file
my_game_list = dict()
my_game_list['datafile'] = dict()
#Bookkeeping can be empty in this example because we're not merging anything
my_game_list['datafile']['bookkeeping'] = argdb_scraper.get_empty_datafile_bookkeeping_dict()
#Generate the header for the xml file
my_game_list['datafile']['header'] = argdb_scraper.get_new_IAGL_header_dict(emu_name=output_settings['header_name'],emu_description=output_settings['header_name'],emu_category=output_settings['categories'],emu_version='010101',emu_date='040820',emu_author=output_settings['author'],emu_baseurl=output_settings['base_url'])

#Initialize a list of games
my_game_list['datafile']['game'] = list()

#Populate the list of games by name/description and rom url
for ff in files:
	my_game_list['datafile']['game'].append(argdb_scraper.get_new_IAGL_game_dict(name = ff.split('/')[-1].split('.')[0],description=ff.split('/')[-1].split('.')[0],rom_in={'@name':ff,'@size':'0'}))

#Convert the metedatasource
converted_dat_files = [argdb_scraper.convert_input_file(x) for x in dat_info] #Warning this takes a while the first time you run it, because the metadata has to be converted, if you have save_conversion set to True above though, the next time you use this source, it's already converted and available

#Here's my list of OVGDB keys to populate
ovgdb_keys = ['boxart1','boxart2','genre','plot','releasedate','studio','year']
lb_keys = ['banner1','boxart1','boxart2','boxart3','boxart4','boxart5','boxart6','boxart7','boxart8','clearlogo1','clearlogo2','fanart1','fanart2','genre','nplayers','plot','rating','releasedate','snapshot1','snapshot2','snapshot3','snapshot4','snapshot5','studio','videoid','year']
thegamesdb_keys = ['ESRB','boxart1','boxart2','clearlogo1','fanart1','fanart2','genre','nplayers','plot','releasedate','year']
#Merge your game list with OVGDB data
merged_dat_files = list()
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[0],dat_file_merge_into=my_game_list,merge_indices=None,merge_settings={'match_type':['exact'],'match_keys':['bookkeeping/rom_name_no_ext|bookkeeping/rom_name_no_ext'],'keys_to_populate':ovgdb_keys,'keys_to_overwrite':['description'],'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[1],dat_file_merge_into=merged_dat_files[-1],merge_indices=None,merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['description|description'],'keys_to_populate':lb_keys,'keys_to_overwrite':['description'],'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[2],dat_file_merge_into=merged_dat_files[-1],merge_indices=None,merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['description|description'],'keys_to_populate':thegamesdb_keys,'keys_to_overwrite':['description'],'keys_to_overwrite_if_populated':None,'keys_to_append':None}))


# #Save the xml file to ...resources/output/
if output_settings['save_output']:
	success = argdb_scraper.output_dat_file(my_game_list,filename_in=output_settings['output_filename'],pop_these_keys_in=['bookkeeping'])