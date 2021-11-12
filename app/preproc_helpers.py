import requests
import json
import re
import os
import shutil
import fnmatch
import pickle
import zipfile
import sys
import subprocess
import pdb

import pandas as pd
import numpy as np

from celery.contrib import rdb

def find_file(pattern, path):
	"""Recursively search the directory pointed to by path for a file matching pattern.
	   Inspired by https://stackoverflow.com/questions/120656/directory-listing-in-python
	Parameters
	----------
	pattern : string
			  unix-style pattern to attempt to match to a file
	path : string
		   path to the directory to search

	Returns 
	-------
	string 
	path to a matching file or the empty string
	"""
	len_root_path = len(path.split('/'))
	for root, dirs, files in os.walk(path):
		if(root.split("/")[-1] == "__original_scripts__"):
			continue
		for name in files:
			if fnmatch.fnmatch(name, pattern):
				return '/'.join((os.path.join(root, name)).split('/')[len_root_path:])
	return ''

def find_dir(pattern, path):
	"""Recursively search the directory pointed to by path for a directory matching pattern.
	   Inspired by https://stackoverflow.com/questions/120656/directory-listing-in-python
	Parameters
	----------
	pattern : string
			  unix-style pattern to attempt to match to a directory
	path : string
		   path to the directory to search

	Returns 
	-------
	string 
	path to a matching directory or the empty string
	"""
	len_root_path = len(path.split('/'))
	for root, dirs, files in os.walk(path):
		for name in dirs:
			if fnmatch.fnmatch(name, pattern):
				return '/'.join((os.path.join(root, name)).split('/')[len_root_path:])
	return ''

def get_r_filename(r_file):
	"""Remove the file extension from an r_file using regex. Probably unnecessary 
	   but improves readability
	Parameters
	----------
	r_file : string
			 name of R file including file extension
	Returns
	-------
	string
	name of R file without file extension
	"""
	return re.split('\.[rR]$', r_file)[0]

def extract_filename(path):
	"""Parse out the file name from a file path
	Parameters
	----------
	path : string
		   input path to parse filename from
	Returns
	-------
	file_name : string
				file name (last part of path), 
				empty string if none found
	"""
	# get last group of a path
	if path:
		file_name = os.path.basename(path)
		file_name = re.match(".*?\s*(\S+\.[^ \s,]+)\s*", file_name)
		if file_name:
			return file_name.group(1)
	return ''

def find_rel_path(path, root_dir, is_dir=False):
	"""Attempt to search along a user-provided absolute path for 
	   the provided file or directory
	Parameters
	----------
	path : string 
		   input path to search for
	root_dir : string
			   root directory to begin search from
	is_dir : bool
			 whether the path is to a directory
	Returns
	-------
	rel_path : string
			   relative path to the directory or file or empty string
			   if not found
	"""
	path_dirs = path.split('/')
	item_name = path_dirs[-1]
	test_fun = os.path.isdir if is_dir else os.path.exists
	if test_fun(root_dir + '/' + item_name):
		return item_name
	else:
		# if path doesn't contain intermediate dirs, give up
		if len(path_dirs) == 1:
			return ''
		intermediate_dirs = reversed(path_dirs[:-1])
		try_path = item_name
		# iterate through intermediate path directories,
		# attempting to find the path
		for my_dir in intermediate_dirs:
			try_path = my_dir + '/' + try_path
			if test_fun(root_dir + '/' + try_path):
				return try_path
		return ''

def maybe_import_operation(r_command):
	"""Searches an r command for common import functions
	Parameters
	----------
	r_command : string
				command from R file
	Returns
	-------
	bool
	"""
	r_import_list = ['read', 'load', 'fromJSON', 'import', 'scan']
	for pattern in r_import_list:
		if re.search(pattern, r_command):
			return True
	return False

def preprocess_setwd(r_file, script_dir, from_preproc=False):
	"""Attempt to correct setwd errors by finding the correct directory or deleting the function call
	Parameters
	----------
	r_file: string
			name of the R file to be preprocessed
	script_dir : string
		   		 path to the directory containing the R file
	from_preproc : boolean
				   whether the r_file has already been preprocessed (default False)

	"""
	# parse out filename and construct file path
	filename = get_r_filename(r_file)
	file_path = script_dir + '/' + r_file
	# path to preprocessed file, named with suffix "_preproc"
	preproc_path = script_dir + '/' + filename + '__preproc__' + '.R'
	# path to temp file, named with suffix "_temp"
	file_to_copy = script_dir + '/' + filename + '_temp' + '.R'
	# if file has already been preprocessed, rename the preprocessed file
	# to a temporary file with _temp suffix, freeing up the __preproc__ suffix to be used 
	# for the file generated by this function
	if from_preproc:
		os.rename(preproc_path, file_to_copy)
	else:
		file_to_copy = file_path

	# for storing return value
	curr_wd = script_dir

	# wipe the preprocessed file and open it for writing
	with open(preproc_path, 'w') as outfile:
		# write code from .R file, replacing function calls as necessary
		with open(file_to_copy, 'r', errors='replace') as infile:
			for line in infile.readlines():
				# ignore commented lines
				if re.match("^#", line):
					outfile.write(line)
				else:
					contains_setwd = re.match("\s*setwd\s*\(\"?([^\"]*)\"?\)", line)
					# if the line contains a call to setwd
					if contains_setwd:
						# try to find the path to the working directory (if any)
						path_to_wd = find_rel_path(contains_setwd.group(1), curr_wd, is_dir=True)
						if not path_to_wd:
							path_to_wd = find_dir(os.path.basename(contains_setwd.group(1)),
												  curr_wd)
						# if a path was found, append modified setwd call to file
						if path_to_wd and path_to_wd != curr_wd:
							curr_wd += '/' + path_to_wd
							outfile.write("setwd(" + "\"" + path_to_wd + "\"" + ")\n")
					else:
						outfile.write(line)
	
	# remove the file with _temp suffix if file was previously preprocessed
	if from_preproc:
		os.remove(file_to_copy)

def preprocess_lib(r_file, path, from_preproc=False):
	"""Replace calls to "library", "require", and "install.packages" with a special function,
	   "install_and_load". Please see install_and_load.R for more details. 
	Parameters
	----------
	r_file: string
			name of the R file to be preprocessed
	file_path : string
				path to the directory containing the R file
	from_preproc : boolean
				   whether the r_file has already been preprocessed

	"""
	install_and_load = """
##### INJECTED TO FACILITATE REPRODUCIBILITY ##################################
# helper function to load packages, installing them if necessary
if(!("stringr" %in% rownames(installed.packages()))){
      install.packages(pkgs="stringr", repos="http://cran.r-project.org")
}
require("stringr", character.only=TRUE)
install_and_load <- function(x, ...){
  # if the input is a string
  if (is.character(x) & length(x) == 1) {
    # check if there are commas in the string
    if (grepl(",", x)) {
      # change x to a vector of strings if there are commas
      x = str_split(x, ",")[[1]]
    }
  }
  for (package in x) {
    if(!(package %in% rownames(installed.packages()))){
      install.packages(pkgs=package, repos="http://cran.r-project.org")
    }
	library(package, character.only=TRUE)
  }
}
###############################################################################
"""
	# TODO decide if we need to keep the injected lib processing
	install_and_load = '##########Preprocessed by RaaS###########\n'
	# parse out filename and construct file path
	filename = get_r_filename(r_file)
	file_path = path + "/" + r_file
	# path to preprocessed file, named with suffix "__preproc__"
	preproc_path = path + "/" + filename + "__preproc__" + ".R"
	# path to temp file, named with suffix "_temp"
	file_to_copy = path + "/" + filename + "_temp" + ".R"
	# if file has already been preprocessed, rename the preprocessed file
	# to a temporary file with _temp suffix, freeing up the __preproc__ suffix to be used 
	# for the file generated by this function
	if from_preproc:
		try:
			os.rename(preproc_path, file_to_copy)
		except:
			file_to_copy = file_path
	else:
		file_to_copy = file_path

	# wipe the preprocessed file and open it for writing
	with open(preproc_path, 'w') as outfile:
		# add in declaration for "install_and_load" at the head of the preprocessed file
		# with open("install_and_load.R", 'r') as infile:
		# 	map(outfile.write, infile.readlines())
		# 	outfile.write("\n")
		outfile.write(install_and_load)
		# write code from .R file, replacing function calls as necessary
		with open(file_to_copy, 'r', errors='replace') as infile:
			for line in infile.readlines():
				# ignore commented lines
				if re.match("^#", line):
					outfile.write(line)
				else:
					# replace "library" calls
					if(re.search("library\s*\(\"?([^\"]*)\"?\)",line) is not None):
						library_replace = re.sub("library\s*\(\"?([^\"]*)\"?\)",
											 "install_and_load(\"\\1\")", line).replace(" ", "")
					else:
						library_replace = line

					# replace "require" calls
					if(re.search("require\s*\(\"?([^\"]*)\"?\)", library_replace) is not None):
						require_replace = re.sub("require\s*\(\"?([^\"]*)\"?\)",
											 "install_and_load(\"\\1\")", library_replace).replace(" ", "")
					else:
						require_replace = library_replace

					# replace "install.packages" calls
					if(re.search("install.packages\s*\(\"?([^\"]*)\"?\)", require_replace) is not None):
						install_replace = re.sub("install.packages\s*\(\"?([^\"]*)\"?\)",
											 "install_and_load(\"\\1\")", require_replace).replace(" ", "")
					else:
						install_replace = require_replace
					# write the preprocessed result
					outfile.write(install_replace)
					# if the line clears the environment, re-declare "install_and_load" immediately after
					if re.match("^\s*rm\s*\(", line):
						# with open("install_and_load.R", 'r') as install_and_load:
						# 	map(outfile.write, install_and_load.readlines())
						# 	outfile.write("\n")
						outfile.write(install_and_load)

	
	# remove the file with _temp suffix if file was previously preprocessed
	if from_preproc:
		try:
			os.remove(file_to_copy)
		except:
			pass

def preprocess_file_paths(r_file, script_dir, from_preproc=False, report_missing=False):
	"""Attempt to correct filepath errors 
	Parameters
	----------
	r_file: string
			name of the R file to be preprocessed
	script_dir : string
		         path to the directory containing the R file
	wd_path : string
			  path to the working directory the R file references, (root directory for file searches)
	from_preproc : bool
				   whether the r_file has already been preprocessed (default False)
	report_missing : bool
					 report when a file can't be found
	"""
	# parse out filename and construct file path
	filename = get_r_filename(r_file)
	file_path = script_dir + "/" + r_file
	# path to preprocessed file, named with suffix "_preproc"
	preproc_path = script_dir + "/" + filename + "__preproc__" + ".R"
	# path to temp file, named with suffix "_temp"
	file_to_copy = script_dir + "/" + filename + "_temp" + ".R"
	# path to write missing files to
	report_path = script_dir + "/missing_files.txt" 
	# if file has already been preprocessed, create _temp file to copy from
	if from_preproc:
		try:
			os.rename(preproc_path, file_to_copy)
		except:
			file_to_copy = file_path
	else:
		file_to_copy = file_path

	curr_wd = script_dir

	# wipe the preprocessed file and open it for writing
	with open(preproc_path, 'w') as outfile:
		# write code from .R file, replacing function calls as necessary
		with open(file_to_copy, 'r', errors='replace') as infile:
			for line in infile.readlines():
				# if not a commented line
				if not re.match('^#', line):
					contains_setwd = re.match("\s*setwd\s*\(\"?([^\"]+)\"?\)", line)
					# track calls to setwd to look in the right place for files
					if contains_setwd:
						curr_wd += '/' + contains_setwd.group(1)
					potential_path = re.search('\((?:.*?file\s*=\s*|\s*)[\"\']([^\"]+\.\w+)[\"\']', line)
					if potential_path:
						# replace windows pathing with POSIX style
						line = re.sub(re.escape('\\\\'), '/', line)
						if maybe_import_operation(line):
							potential_path = potential_path.group(1)
							if potential_path:
								rel_path = find_rel_path(potential_path, curr_wd)
								if not rel_path:
									# try to find the path to the working directory (if any)
									new_path = find_file(extract_filename(potential_path), get_root_dir(curr_wd))
									if new_path:
										new_path = os.path.join( get_root_dir(curr_wd), new_path)
										rel_path = os.path.relpath(new_path, start = curr_wd)
								# if a path was found, change the file part of the line
								if rel_path:
									line = re.sub(potential_path, rel_path, line)
								# if the path wasn't found, report file as missing
								elif report_missing:
									with open(report_path, 'a+') as missing_out:
										missing_out.write(r_file + ',' + potential_path + '\n')
				outfile.write(line)
	
	# remove the file with _temp suffix if file was previously preprocessed
	if from_preproc:
		try:
			os.remove(file_to_copy)
		except:
			pass

def preprocess_source(r_file, script_dir, from_preproc=False):
	"""Recursively paste any sourced R files into the current R file
	Parameters
	----------
	r_file : string
			 name of the R file to be preprocessed
	script_dir : string
		          path to the directory containing the R file
	from_preproc : boolean
				   whether the r_file has already been preprocessed (default False)
	"""
	sourced_files = []
	# parse out filename and construct file path
	preprocess_setwd(r_file, script_dir)
	filename = get_r_filename(r_file)
	file_path = script_dir + "/" + r_file
	# path to preprocessed file, named with suffix "_preproc"
	preproc_path = script_dir + "/" + filename + "__preproc__" + ".R"
	# path to temp file, named with suffix "_temp"
	file_to_copy = script_dir + "/" + filename + "_temp" + ".R"
	# if file has already been preprocessed, create _temp file to copy from
	if from_preproc:
		os.rename(preproc_path, file_to_copy)
	else:
		file_to_copy = file_path
	curr_wd = script_dir

	# wipe the preprocessed file and open it for writing
	with open(preproc_path, 'w') as outfile:
		# write code from .R file, replacing function calls as necessary
		with open(file_to_copy, 'r', errors='replace') as infile:
			for line in infile.readlines():
				# if not a commented line
				if not re.match('^#', line):
					contains_setwd = re.match("\s*setwd\s*\(\"?([^\"]*)\"?\)", line)
					# if the line contains a call to setwd
					if contains_setwd:
						curr_wd += '/' + contains_setwd.group(1)
					sourced_file = re.match('^\s*source\s*\((?:.*?file\s*=\s*|\s*)[\"\']([^\"]+\.[Rr])[\"\']', line)
					if sourced_file:
						sourced_file = sourced_file.group(1)
						# replace windows pathing with POSIX style
						line = re.sub(re.escape('\\\\'), '/', line)
						# try to fine the relative path
						#rel_path = find_rel_path(sourced_file, curr_wd)
						rel_path = ''
						# Try and find the file, otherwise may need to look for the preprocessed version!
						new_path = find_file(extract_filename(sourced_file), get_root_dir(curr_wd))
						if new_path:
							rel_path = os.path.join( get_root_dir(curr_wd), new_path)
							rel_path = os.path.relpath(rel_path, start = curr_wd)

							sourced_filename = os.path.basename(rel_path)
							sourced_path = '/'.join((curr_wd + '/' + rel_path).split('/')[:-1])
							recurred_files = preprocess_source(sourced_filename, sourced_path, from_preproc)
							sourced_files = recurred_files + sourced_files
							sourced_files.append("/" + new_path)
							with open(sourced_path + '/' + re.sub('.R$', '__preproc__.R', sourced_filename),
								      'r') as sourced_file:
								for source_line in sourced_file.readlines():
									outfile.write(source_line)
								
						# check for preprocessed version
						else:
							new_path = find_file(re.sub('.R$', '__preproc__.R', os.path.basename(sourced_file)), get_root_dir(curr_wd))
							if new_path:
								rel_path = os.path.join( get_root_dir(curr_wd), new_path)
								rel_path = os.path.relpath(rel_path, start = curr_wd)

								sourced_filename = os.path.basename(rel_path)
								sourced_path = '/'.join((curr_wd + '/' + rel_path).split('/')[:-1])
								sourced_files.append("/" + re.sub('__preproc__.R$', '.R', new_path))
								with open(sourced_path + '/' + sourced_filename,
								      'r') as sourced_file:
									#map(outfile.write, infile.readlines())
									for source_line in sourced_file.readlines():
										outfile.write(source_line)
								
							#outfile.write(line)
					else:
						outfile.write(line)
				else:
					outfile.write(line)
			outfile.write("\n")
	
	# remove the file with _temp suffix if file was previously preprocessed
	if from_preproc:
		try:
			os.remove(file_to_copy)
		except:
			pass
	return(sourced_files)

# This function grabs the root directory of a dataset from a filepath to a script's dir
# It also returns the root unchanged if the script is in the root
def get_root_dir(filepath):
	path_pieces = filepath.split("/")
	root_parent = path_pieces.index("datasets")
	root_dir = '/'.join(path_pieces[0:root_parent+3])
	return (root_dir)

def all_preproc(r_file, path, error_string="error"):
	"""Attempt to correct setwd, file path, and library errors
	Parameters
	----------
	r_file: string
			name of the R file to be preprocessed
	path : string
		   path to the directory containing the R file
	error_string : string
				   original error obtained by running the R script, defaults to
				   "error", which will perform the preprocessing
	"""
	sourced_files =[]
	# parse out filename and construct file path
	filename = get_r_filename(r_file)
	file_path = path + "/" + r_file
	# path to preprocessed file, named with suffix "_preproc"
	preproc_path = path + "/" + filename + "__preproc__" + ".R"
	# try all 3 preprocessing methods if there is an error
	if error_string != "success":
		sourced_files = preprocess_source(r_file, path, from_preproc=True)
		#preprocess_lib(r_file, path, from_preproc=True)
		preprocess_file_paths(r_file, path, from_preproc=True, report_missing=True)
	# else just copy and rename the file
	else:
		shutil.copyfile(file_path, preproc_path)
	return(sourced_files)
