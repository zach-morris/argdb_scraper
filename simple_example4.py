#Example 4

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
					'common_platforms':['Sega Genesis'], #A common name for the platform your scraping
					}
output_settings = {	'type':'IAGL', #Dat type to output.  This is currently the only option.  ARGDB will be added later
					'output_filename':'Gen_Game_Example.xml', #Filename to output
					'header_name': 'Genesis Games Example', #IAGL header will be populated with this
					'categories': 'Sega,Consoles', #IAGL header will be populated with this
					'save_output':True, #Simple trigger to turn on and of file saving after parsing
					'author':'Zach Morris', #Author for the IAGL header
					'base_url':'https://archive.org/download/', #Base URL for the IAGL header
					}

#This time, I put 'all' in the platform to create a converted save file for the entire metadata set, I can use this for every other scrape I perform later, and i can filter the game lists after they're loaded
dat_info = [
	{'type': 'archive_org','filename':'Gen_Example.htm','platform':['all'],'save_conversion':False}, #0
	{'type': 'OVGDB','filename':'OpenVGDB 28.0.sqlite','platform':['all'],'save_conversion':True}, #1
	{'type': 'launchbox','filename':'Metadata.xml','platform':['all'],'save_conversion':True}, #2, Launchbox, save converted file to json
	{'type': 'thegamesdb','filename':'dump_102419','platform':['all'],'save_conversion':True}, #3, thegamesdb, save converted file to json
	{'type': 'mobygames','filename':'mobygames_012020.json','platform':['all'],'save_conversion':True}, #4
	]


#Define your argdb scraper object
argdb_scraper = argdb_scraper(parsing_settings=parsing_settings,output_settings=output_settings)

#Convert the data and metedata source
converted_dat_files = [argdb_scraper.convert_input_file(x) for x in dat_info] #Warning this takes a while the first time you run it, because the metadata has to be converted, if you have save_conversion set to True above though, the next time you use this source, it's already converted and available


#Now filter the large list down to the correct platform
converted_dat_files[1]['datafile']['game'] = [x for x in converted_dat_files[1]['datafile']['game'] if (type(x['bookkeeping']['database_platform']) is not list and (x['bookkeeping']['database_platform'] == 'Sega Genesis/Mega Drive')) or (type(x['bookkeeping']['database_platform']) is list and any([y == 'Sega Genesis/Mega Drive' for y in x['bookkeeping']['database_platform']]))]
converted_dat_files[2]['datafile']['game'] = [x for x in converted_dat_files[2]['datafile']['game'] if (type(x['bookkeeping']['database_platform']) is not list and (x['bookkeeping']['database_platform'] == parsing_settings['common_platforms'][0])) or (type(x['bookkeeping']['database_platform']) is list and any([y == parsing_settings['common_platforms'][0] for y in x['bookkeeping']['database_platform']]))]
converted_dat_files[3]['datafile']['game'] = [x for x in converted_dat_files[3]['datafile']['game'] if (type(x['bookkeeping']['database_platform']) is not list and (x['bookkeeping']['database_platform'] == parsing_settings['common_platforms'][0])) or (type(x['bookkeeping']['database_platform']) is list and any([y == parsing_settings['common_platforms'][0] for y in x['bookkeeping']['database_platform']]))]
converted_dat_files[4]['datafile']['game'] = [x for x in converted_dat_files[4]['datafile']['game'] if (type(x['bookkeeping']['database_platform']) is not list and (x['bookkeeping']['database_platform'] == 'Genesis')) or (type(x['bookkeeping']['database_platform']) is list and any([y == 'Genesis' for y in x['bookkeeping']['database_platform']]))]


#Here's my list of OVGDB keys to populate
ovgdb_keys = ['boxart1','boxart2','genre','plot','releasedate','studio','year']
lb_keys = ['banner1','boxart1','boxart2','boxart3','boxart4','boxart5','boxart6','boxart7','boxart8','clearlogo1','clearlogo2','fanart1','fanart2','genre','nplayers','plot','rating','releasedate','snapshot1','snapshot2','snapshot3','snapshot4','snapshot5','studio','videoid','year']
thegamesdb_keys = ['ESRB','boxart1','boxart2','clearlogo1','fanart1','fanart2','genre','nplayers','plot','releasedate','year']
moby_keys = ['boxart1','genre','plot','rating','snapshot1','snapshot2','snapshot3','snapshot4']

#Fix name in archive_org source.  Not required, just making the xml output prettier
for game in converted_dat_files[0]['datafile']['game']:
	game['@name'] = game['description']

# #Merge your game list with OVGDB data
merged_dat_files = list()
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[1],dat_file_merge_into=converted_dat_files[0],merge_indices=None,merge_settings={'match_type':['exact'],'match_keys':['bookkeeping/rom_name_no_ext|bookkeeping/rom_name_no_ext'],'keys_to_populate':ovgdb_keys,'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[2],dat_file_merge_into=merged_dat_files[-1],merge_indices=None,merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['bookkeeping/description_clean|bookkeeping/description_clean'],'keys_to_populate':lb_keys,'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[3],dat_file_merge_into=merged_dat_files[-1],merge_indices=None,merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['bookkeeping/description_clean|bookkeeping/description_clean'],'keys_to_populate':thegamesdb_keys,'keys_to_overwrite':None,'keys_to_overwrite_if_populated':None,'keys_to_append':None}))
merged_dat_files.append(argdb_scraper.merge_dat_files(dat_file_merge_from=converted_dat_files[4],dat_file_merge_into=merged_dat_files[-1],merge_indices=None,merge_settings={'match_type':['fuzzy_automatic'],'match_keys':['bookkeeping/description_clean|bookkeeping/description_clean'],'keys_to_populate':moby_keys,'keys_to_overwrite':['groups'],'keys_to_overwrite_if_populated':None,'keys_to_append':None}))


#Save the xml file to ...resources/output/
if output_settings['save_output']:
	success = argdb_scraper.output_dat_file(merged_dat_files[-1],filename_in=output_settings['output_filename'],pop_these_keys_in=['bookkeeping'])