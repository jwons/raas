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
import docker
import random
import string
import celery
import time
import cgi
import tarfile

import pandas as pd
import numpy as np
from app.Parse import Parser as ProvParser
from urllib.parse import urlparse
from app.models import User, Dataset
from app import app, db
from celery.exceptions import Ignore
from celery.contrib import rdb
from shutil import copy


def doi_to_directory(doi):
    """Converts a doi string to a more directory-friendly name
    Parameters
    ----------
    doi : string
          doi

    Returns
    -------
    doi : string
          doi with "/" and ":" replaced by "-" and "--" respectively
    """
    return doi.replace("/", "-").replace(":", "--")


def directory_to_doi(doi):
    """Converts a doi string to a more directory-friendly name
    Parameters
    ----------
    doi : string
          doi

    Returns
    -------
    doi : string
          doi with "-" and "--" replaced by "/" and ":" respectively
    """
    return doi.replace("--", ":").replace("-", "/")


def download_dataset(doi, destination, dataverse_key,
                     api_url="https://dataverse.harvard.edu/api/"):
    """Download doi to the destination directory
    Parameters
    ----------
    doi : string
          doi of the dataset to be downloaded
    destination : string
                  path to the destination in which to store the downloaded directory
    dataverse_key : string
                    dataverse api key to use for completing the download
    api_url : string
              URL of the dataverse API to download the dataset from
    Returns
    -------
    bool
    whether the dataset was successfully downloaded to the destination
    """
    api_url = api_url.strip("/")
    # make a new directory to store the dataset
    # (if one doesn't exist)
    if not os.path.exists(destination):
        os.makedirs(destination)

    try:
        # query the dataverse API for all the files in a dataverse
        files = requests.get(api_url + "/datasets/:persistentId",
                             params={"persistentId": doi}) \
            .json()['data']['latestVersion']['files']

    except:
        return False

    # convert DOI into a friendly directory name by replacing slashes and colons
    doi_direct = destination + '/' + doi_to_directory(doi)

    # make a new directory to store the dataset
    if not os.path.exists(doi_direct):
        os.makedirs(doi_direct)
    # for each file result
    for file in files:
        try:
            # parse the filename and fileid
            # filename = file['dataFile']['filename']
            fileid = file['dataFile']['id']
            contentType = file['dataFile']['contentType']

            if (contentType == 'type/x-r-syntax'):
                # query the API for the file contents
                response = requests.get(api_url + "/access/datafile/" + str(fileid))
            else:
                # query the API for the file contents
                response = requests.get(api_url + "/access/datafile/" + str(fileid),
                                        params={"format": "original", "key": dataverse_key})

            value, params = cgi.parse_header(response.headers['Content-disposition'])
            if 'filename*' in params:
                filename = params['filename*'].split("'")[-1]
            else:
                filename = params['filename']

            # write the response to correctly-named file in the dataset directory
            with open(doi_direct + "/" + filename, 'wb') as handle:
                handle.write(response.content)
        except:
            return False
    return True


def get_runlog_data(path_to_datasets):
    """Aggregate run-time data for all datasets in the given
    Parameters
    ----------
    path_to_datasets : string
                       path to the directory containing processed datasets
    Returns
    -------
    (run_data_df, error_dois) : tuple of (pandas.DataFrame, list of string)
                                a tuple containing a pandas DataFrame with the
                                aggregated results of attempting to run the R code
                                in all the datasets, followed by a list of datasets
                                for which aggregating the results failed (should be
                                an empty list unless there was a catastrophic error)

    """
    # get list of dataset directories, ignoring macOS directory metadata file (if present)
    doi_directs = [doi for doi in os.listdir(path_to_datasets) if doi != '.DS_Store']
    # initialize empty dataframe to store run logs of all the files
    run_data_df = pd.DataFrame()
    # initialize empty list to store problem doi's
    error_dois = []

    # iterate through directories and concatenate run logs
    for my_doi in doi_directs:
        try:
            # assemble path
            my_path = path_to_datasets + '/' + my_doi + '/prov_data/' + 'run_log.csv'
            # concatenate to dataframe
            run_data_df = pd.concat([run_data_df, pd.read_csv(my_path)])
        except:
            error_dois.append(my_doi)
    return (run_data_df, error_dois)


def get_missing_files(path_to_datasets, pickle_path):
    """Aggregate missing files data for all datasets in the given path and pickle the result
    Parameters
    ----------
    path_to_datasets : string
                       path to the directory containing processed datasets
    pickle_path : string
                  path to pickle file to store the dictionary
    """
    # get list of dataset directories, ignoring macOS directory metadata file (if present)
    doi_directs = [doi for doi in os.listdir(path_to_datasets) if doi != '.DS_Store']
    missing_dict = {}

    # iterate through directories and concatenate run logs
    for my_doi in doi_directs:
        if my_doi.startswith("doi"):
            missing_dict[my_doi] = []
            try:
                # assemble path
                my_path = path_to_datasets + '/' + my_doi + '/prov_data/' + 'missing_files.txt'
                # open the file for reading and collect the results
                with open(my_path, 'r') as my_file:
                    for line in my_file.readlines():
                        if line.strip():
                            missing_dict[my_doi].append(line.strip())
                    missing_dict[my_doi] = list(set(missing_dict[my_doi]))
            except:
                pass

    # pickle the file
    with open(pickle_path + '/missing_files.pkl', 'wb') as handle:
        pickle.dump(missing_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


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
        with open(file_to_copy, 'r') as infile:
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
        with open("install_and_load.R", 'r') as infile:
            map(outfile.write, infile.readlines())
            outfile.write("\n")
        # write code from .R file, replacing function calls as necessary
        with open(file_to_copy, 'r') as infile:
            for line in infile.readlines():
                # ignore commented lines
                if re.match("^#", line):
                    outfile.write(line)
                else:
                    # replace "library" calls
                    library_replace = re.sub("library\s*\(\"?([^\"]*)\"?\)",
                                             "install_and_load(\"\\1\")", line)
                    # replace "require" calls
                    require_replace = re.sub("require\s*\(\"?([^\"]*)\"?\)",
                                             "install_and_load(\"\\1\")", library_replace)
                    # replace "install.packages" calls
                    install_replace = re.sub("install.packages\s*\(\"?([^\"]*)\"?\)",
                                             "install_and_load(\"\\1\")", require_replace)
                    # write the preprocessed result
                    outfile.write(install_replace)
                    # if the line clears the environment, re-declare "install_and_load" immediately after
                    if re.match("^\s*rm\s*\(", line):
                        with open("install_and_load.R", 'r') as install_and_load:
                            map(outfile.write, install_and_load.readlines())
                            outfile.write("\n")

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
    report_path = script_dir + "/prov_data/missing_files.txt"
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
        with open(file_to_copy, 'r') as infile:
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
                                    rel_path = find_file(extract_filename(potential_path), curr_wd)
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
        with open(file_to_copy, 'r') as infile:
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
                        rel_path = find_rel_path(sourced_file, curr_wd)
                        if not rel_path:
                            rel_path = find_file(extract_filename(sourced_file), curr_wd)
                        # if relative path found, recursively call function on the sourced file
                        if rel_path:
                            sourced_filename = os.path.basename(rel_path)
                            sourced_path = '/'.join((curr_wd + '/' + rel_path).split('/')[:-1])
                            preprocess_source(sourced_filename, sourced_path, from_preproc)
                            with open(sourced_path + '/' + re.sub('.R\$', '__preproc__.R\$', sourced_filename),
                                      'r') as infile:
                                map(outfile.write, infile.readlines())
                    else:
                        outfile.write(line)
                else:
                    outfile.write(line)

    # remove the file with _temp suffix if file was previously preprocessed
    if from_preproc:
        try:
            os.remove(file_to_copy)
        except:
            pass


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
    # parse out filename and construct file path
    filename = get_r_filename(r_file)
    file_path = path + "/" + r_file
    # path to preprocessed file, named with suffix "_preproc"
    preproc_path = path + "/" + filename + "__preproc__" + ".R"
    # try all 3 preprocessing methods if there is an error
    if error_string != "success":
        preprocess_source(r_file, path, from_preproc=True)
        preprocess_lib(r_file, path, from_preproc=True)
        preprocess_file_paths(r_file, path, from_preproc=True, report_missing=True)
    # else just copy and rename the file
    else:
        shutil.copyfile(file_path, preproc_path)


def get_io_from_prov_json(prov_json):
    """Identify input and output files from provenance JSON
    Parameters
    ----------
    prov_json : OrderedDict
                ordered dictionary generated from json prov file using python's json module
                i.e. json.load(path_to_json_file, object_pairs_hook=OrderedDict)

    Returns
    -------
    (input_files, output_files, file_locs) : tuple of (list, list, dict)
                                             input files and output files (empty lists if none) and
                                             dict mapping files to location (empty if none)
    """
    # initializing data structures
    entity_to_file = {}
    file_locs = {}
    input_files = []
    output_files = []

    # get file entity names and locations
    for key, value in prov_json['entity'].items():
        if value['rdt:type'] == 'File':
            filename = value['rdt:name']
            entity_to_file[key] = filename
            file_locs[filename] = value['rdt:location']

    entities = set(entity_to_file.keys())

    # if a file entity is used by an activity, it must be an input file
    for value in prov_json['used'].values():
        if value['prov:entity'] in entities:
            input_files.append(entity_to_file[value['prov:entity']])

    # if a file entity was generated by an activity, it must be an output file
    for value in prov_json['wasGeneratedBy'].values():
        if value['prov:entity'] in entities:
            output_files.append(entity_to_file[value['prov:entity']])

    return input_files, output_files, file_locs


def get_pkgs_from_prov_json(prov_json, optimize=False):
    """Identify packages used from provenance JSON
    Parameters
    ----------
    prov_json : OrderedDict
                ordered dictionary generated from json prov file using python's json module
                i.e. json.load(path_to_json_file, object_pairs_hook=OrderedDict)
    optimize : bool
               whether to attempt to optimize which packages to install based on
               whether the packages were used

    Returns
    -------
    packages : list of tuple of (string, string)
               list of (package_name, version) tuples
    """
    # regular expression to capture library name
    library_regex = re.compile(r"library\((?P<lib_name>.*)\)", re.VERBOSE)

    if optimize:
        # set of used libraries
        used_packages = set()
        # Identify libraries being used in script and add them to set
        for command in prov_json['activity'].values():
            code_line = command['rdt:name']
            # extract the package name from the JSON
            package_match = re.match('^\s*library\s*\((?:.*?package\s*=\s*|\s*)[\"\']([^\"]+)[\"\']',
                                     code_line)
            if not package_match:
                package_match = re.match('^\s*require\s*\((?:.*?package\s*=\s*|\s*)[\"\']([^\"]+)[\"\']',
                                         code_line)
            # if a package name was found, add to the set
            if package_match:
                used_packages.add(package_match.group(1))

    # list of (package, version) tuples
    packages = []

    # Filter packages in user's environment by which ones were used
    for package_dict in prov_json.getLibs().iterrows():
        package_name = package_dict[1][0]
        package_version = package_dict[1][1]
        if package_name not in set(['datasets', 'utils', 'graphics', 'grDevices',
                                    'methods', 'stats', 'provR', 'devtools', 'base']):
            if optimize:
                if package_dict["package"] in used_packages:
                    packages.append((package_dict["package"], package_dict["version"]))
            else:
                packages.append((package_name, package_version))

    return packages


"""
The following block of file decoding functions are heavily-modified versions of 
Sebastian RoccoSerra's answer on this Stack Overflow post:
https://stackoverflow.com/questions/191359/how-to-convert-a-file-to-utf-8-in-python
(block ends with a series of # marks)
"""


def get_encoding_type(current_file):
    detectee = open(current_file, 'rb').read()
    result = chardet.detect(detectee)
    return result['encoding']


def writeConversion(sourceFh, sourceFile, outputDir, targetFormat):
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    with codecs.open(outputDir + '/' + sourceFile, 'w', targetFormat) as targetFile:
        for line in sourceFh:
            targetFile.write(line)


def convertFileWithDetection(sourceDir, sourceFile, outputDir, targetFormat, replace=False,
                             logs=False):
    if logs:
        print("Converting '" + sourceFile + "'...")
    sourcePath = os.path.join(sourceDir, sourceFile)
    if replace:
        os.rename(os.path.join(sourceDir, sourceFile),
                  os.path.join(sourceDir, "__orig__" + sourceFile))
        sourcePath = os.path.join(sourceDir, "__orig__" + sourceFile)

    sourceFormat = get_encoding_type(sourcePath)

    try:
        with codecs.open(sourcePath, 'rU', sourceFormat) as sourceFh:
            writeConversion(sourceFh, sourceFile, outputDir, targetFormat)
            if logs:
                print('Done.')
        if replace:
            os.remove(sourcePath)
        return
    except UnicodeDecodeError:
        pass

    print("Error: failed to convert " + sourceFile + ".")


def convertFileBestGuess(filename):
    sourceFormats = ['ascii', 'iso-8859-1']
    for format in sourceFormats:
        try:
            with codecs.open(sourceFile, 'rU', format) as sourceFile:
                writeConversion(sourceFile)
                print('Done.')
                return
        except UnicodeDecodeError:
            pass


"""
End of file decoding function block from Stack Overflow
"""


def convert_r_files(path, replace=False, output_path=''):
    """Convert all R files to utf-8 in the directory pointed to by path
    Parameters
    ----------
    path : string
           path to the directory containing R scripts
    output_path : string
                  relative path from "path" parameter to directory
                  to place converted files
    replace : bool
              whether to replace original files with converted ones
    """
    targetFormat = 'utf-8'
    # calculate correct output
    output_path = 'converted' if not output_path else output_path
    outputDir = path if replace else os.path.join(path, output_path)
    orig_files = [my_file for my_file in os.listdir(path) if \
                  my_file.endswith(".R") or my_file.endswith(".r")]
    for my_file in orig_files:
        convertFileWithDetection(path, my_file, outputDir, 'utf-8', replace)


def replace_files_with_preproc(path, file_type):
    """Replace original R files with preprocessed R files
    path : string
           path to dataset directory
    file_type : string
                either "r" or "json", the type of file to replace
    """
    if file_type == "r":
        orig_files = [my_file for my_file in os.listdir(path) if \
                      (my_file.endswith(".R") or my_file.endswith(".r")) and \
                      not "__preproc__" in my_file]
        preproc_files = [my_file for my_file in os.listdir(path) if \
                         (my_file.endswith(".R") or my_file.endswith(".r")) and \
                         "__preproc__" in my_file]
    elif file_type == "json":
        orig_files = [my_file for my_file in os.listdir(path) if \
                      my_file.endswith(".json") and \
                      not "__preproc__" in my_file]
        preproc_files = [my_file for my_file in os.listdir(path) if \
                         my_file.endswith(".json") and \
                         "__preproc__" in my_file]
    else:
        return

    # remove the original files
    for my_file in orig_files:
        os.remove(os.path.join(path, my_file))
    # rename the preprocessed files
    for my_file in preproc_files:
        os.rename(os.path.join(path, my_file),
                  os.path.join(path, re.sub('__preproc__', '', my_file)))


def build_docker_package_install(package, version):
    """Outputs formatted dockerfile command to install a specific version
       of an R package into a docker image
    Parameters
    ----------
    package : string
              Name of the R package to be installed
    version : string
              Version number of the desired package
    """
    return 'RUN R -e \"require(\'devtools\');install_version(\'' + \
           package + '\', version=\'' + version + '\', repos=\'http://cran.rstudio.com\')\"\n'


def naive_error_classifier(error_string):
    """Attempts to guess the cause of an error in R
    Parameters
    ----------
    error_string : string
                   error output

    Returns
    -------
    Likely error type (library, setwd, No such file) or None
    """
    if re.search('library\s*\(', error_string):
        return '(This is likely an error with a call to the \"library\" function. ' + \
               'Please ensure that you\'re not specifying a particular location for the package you\'re trying to load. ' + \
               'To try and automatically correct this error, select the automatic error fixing option in the Build Image form.)'

    if re.search('setwd\s*\(', error_string):
        return '(This is likely an error with a call to the \"setwd\" function. ' + \
               'Please ensure that you\'re not specifying an absolute path for your working directory. ' + \
               'To try and automatically correct this error, select the automatic error fixing option in the Build Image form.)'
    if (re.search('file\s*\(', error_string) or re.search('cannot open the connection', error_string)
            or re.search('No such file', error_string)):
        return '(This is likely an error importing data from a file. ' + \
               'Please ensure that you\'re specifying the correct path to your data, and that your data is ' + \
               'included in the file you uploaded. ' + \
               'To try and automatically correct this error, select the automatic error fixing option in the Build Image form.)'
    return ''


def clean_up_datasets():
    # delete any stored data
    for dataset_directory in os.listdir(os.path.join(app.instance_path, 'r_datasets')):
        try:
            shutil.rmtree(os.path.join(app.instance_path, 'r_datasets', dataset_directory))
        except:
            try:
                os.remove(os.path.join(app.instance_path, 'r_datasets', dataset_directory))
            except:
                pass


def gather_json_files_from_url(url):
    json_files = []

    # Strip the beginning of the url
    container_name = urlparse(url)[2][3:]
    # Strip the last '/'
    image_name = container_name[:-1]

    client = docker.from_env()
    client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))

    container = client.containers.run(image=image_name, detach=True, environment=["PASSWORD=llvis"],
                                      ports={'8787': '8787'})

    result = container.exec_run("find /home/rstudio -name 'prov_data'")
    f = open(os.path.join(app.instance_path, './docker_dir/prov.tar'), 'wb+')
    bits, stat = container.get_archive(result[1].decode("ascii").strip())

    for chunk in bits:
        f.write(chunk)

    f.close()
    container.kill()
    tar = tarfile.open(os.path.join(app.instance_path, './docker_dir/prov.tar'), "r:")
    tar.extractall(path=os.path.join(app.instance_path, './docker_dir/'))
    tar.close()

    for file in os.listdir(os.path.join(app.instance_path, './docker_dir/prov_data')):
        if file.endswith(".json"):
            json_files.append(file)

    return (json_files)


@celery.task(bind=True)  # allows the task to be run in the background with Celery
def build_image(self, current_user_id, name, preprocess, dataverse_key='', doi='', zip_file=''):
    """Build a docker image for a user-provided dataset
    Parameters
    def build_image(self,user_id,zipfile_path,
                      name,language,
                      need_prepro,
                      extended_lib,
                      adv_opt)
    ----------
    current_user_id : int
                      id of current user
    name : string
           name of the image
    preprocess : bool
                 whether to preprocess the code in the dataset
    dataverse_key : string
                    API key for a dataverse instance
    doi : string
          DOI of the dataset if retrieving dataset from dataverse
    zip_file : string
               name of the .zip file if dataset uploaded as a .zip
    """
    ########## GETTING DATA ######################################################################
    # either get the dataset from the .zip file or download it from dataverse

    dataset_dir = ''
    # current_user_id = info.user_id
    # name = info.name
    # preprocess = info.need_prepro,
    # dataverse_key = ''
    # doi = ''
    # zip_file = info.zipfile_path

    if zip_file:
        # assemble path to zip_file
        zip_path = os.path.join(app.instance_path, 'r_datasets', zip_file)
        # unzip the zipped directory and remove zip file
        with zipfile.ZipFile(zip_path) as zip_ref:
            dir_name = zip_ref.namelist()[0].strip('/')
            zip_ref.extractall(os.path.join(app.instance_path, 'r_datasets', dir_name))
        os.remove(os.path.join(app.instance_path, 'r_datasets', zip_file))
        # find name of unzipped directory
        dataset_dir = os.path.join(app.instance_path, 'r_datasets', dir_name, dir_name)
        doi = dir_name
    else:
        dataset_dir = os.path.join(app.instance_path, 'r_datasets', doi_to_directory(doi),
                                   doi_to_directory(doi))
        success = download_dataset(doi=doi, dataverse_key=dataverse_key,
                                   destination=os.path.join(app.instance_path, 'r_datasets',
                                                            doi_to_directory(doi)))
        if not success:
            clean_up_datasets()
            return {'current': 100, 'total': 100, 'status': ['Data download error.',
                                                             [['Download error',
                                                               'There was a problem downloading your data from ' + \
                                                               'Dataverse. Please make sure the DOI is correct.']]]}
    # print(dataset_dir, file=sys.stderr)

    ########## GETTING PROV ######################################################################

    # run the R code and collect errors (if any)
    if preprocess:
        try:
            self.update_state(state='PROGRESS', meta={'current': 1, 'total': 5,
                                                      'status': 'Preprocessing files for errors and ' + \
                                                                'collecting provenance data... ' + \
                                                                '(This may take several minutes or longer,' + \
                                                                ' depending on the complexity of your scripts)'})
            subprocess.run(['bash', 'app/get_prov_for_doi_preproc.sh', dataset_dir])
            replace_files_with_preproc(dataset_dir, "r")
            replace_files_with_preproc(os.path.join(dataset_dir, 'prov_data'), "json")
        except:
            clean_up_datasets()
    else:
        self.update_state(state='PROGRESS', meta={'current': 1, 'total': 5,
                                                  'status': 'Collecting provenance data... ' + \
                                                            '(This may take several minutes or longer,' + \
                                                            ' depending on the complexity of your scripts)'})
        subprocess.run(['bash', 'app/get_prov_for_doi.sh', dataset_dir, "app/get_dataset_provenance.R"])

    ########## CHECKING FOR PROV ERRORS ##########################################################
    # make sure an execution log exists

    run_log_path = os.path.join(dataset_dir, 'prov_data', 'run_log.csv')
    if not os.path.exists(run_log_path):
        print(run_log_path, file=sys.stderr)
        error_message = "ContainR could not locate any .R files to collect provenance for. " + \
                        "Please ensure that .R files to load dependencies for are placed in the " + \
                        "top-level directory."
        clean_up_datasets()
        return {'current': 100, 'total': 100, 'status': ['Provenance collection error.',
                                                         [['Could not locate .R files',
                                                           error_message]]]}

    # check the execution log for errors
    errors_present, error_list, my_file = checkLogForErrors(run_log_path)

    if errors_present:
        clean_up_datasets()
        return {'current': 100, 'total': 100, 'status': ['Provenance collection error.',
                                                         error_list]}

    ########## PARSING PROV ######################################################################

    self.update_state(state='PROGRESS', meta={'current': 2, 'total': 5,
                                              'status': 'Parsing provenance data... '})
    # build dockerfile from provenance
    # get list of json provenance files
    prov_jsons = [my_file for my_file in os.listdir(os.path.join(dataset_dir, 'prov_data')) \
                  if my_file.endswith('.json')]

    used_packages = []

    # assemble a set of packages used
    for prov_json in prov_jsons:
        print(prov_json, file=sys.stderr)
        used_packages += get_pkgs_from_prov_json( \
            ProvParser(os.path.join(dataset_dir, 'prov_data', prov_json)))

    print(used_packages, file=sys.stderr)
    docker_file_dir = os.path.join(app.instance_path,
                                   'r_datasets', doi_to_directory(doi))
    try:
        os.makedirs(docker_file_dir)
    except:
        pass

    ########## BUILDING DOCKER ###################################################################

    self.update_state(state='PROGRESS', meta={'current': 3, 'total': 5,
                                              'status': 'Building Docker image... '})
    # try:
    # copy relevant packages, system requirements, and directory
    sysreqs = []
    with open(os.path.join(dataset_dir, 'prov_data', "sysreqs.txt")) as reqs:
        sysreqs = reqs.readlines()
    shutil.rmtree(os.path.join(dataset_dir, 'prov_data'))

    # Write the Dockkerfile
    # 1.) First install system requirements, this will allow R packages to install with no errors (hopefully)
    # 2.) Install R packages
    # 3.) Add the analysis folder
    # 4.) Copy in the scripts that run the analysis
    # 5.) Change pemissions? TODO: why?
    # 6.) Run analyses
    # 7.) Collect installed packages for report
    with open(os.path.join(docker_file_dir, 'Dockerfile'), 'w') as new_docker:
        new_docker.write('FROM rocker/tidyverse:latest\n')
        if (len(sysreqs) == 1):
            sysinstall = "RUN export DEBIAN_FRONTEND=noninteractive; apt-get -y update && apt-get install -y "
            new_docker.write(sysinstall + sysreqs[0])
        used_packages = list(set(used_packages))
        if used_packages:
            for package, version in used_packages:
                new_docker.write(build_docker_package_install(package, version))

        # copy the new directory and change permissions
        new_docker.write('ADD ' + doi_to_directory(doi) \
                         + ' /home/rstudio/' + doi_to_directory(doi) + '\n')

        copy("app/get_prov_for_doi.sh", "instance/r_datasets/" + doi_to_directory(doi))
        copy("app/get_dataset_provenance.R", "instance/r_datasets/" + doi_to_directory(doi))
        new_docker.write('COPY get_prov_for_doi.sh /home/rstudio/\n')
        new_docker.write('COPY get_dataset_provenance.R /home/rstudio/\n')

        new_docker.write('RUN chmod a+rwx -R /home/rstudio/' + doi_to_directory(doi) + '\n')
        new_docker.write("RUN /home/rstudio/get_prov_for_doi.sh " \
                         + "/home/rstudio/" + doi_to_directory(doi) + " /home/rstudio/get_dataset_provenance.R\n")
        new_docker.write("RUN R -e 'write(paste(as.data.frame(installed.packages()," \
                         + "stringsAsFactors = F)$Package, collapse =\"\\n\"), \"./listOfPackages.txt\")'\n")

    # create docker client instance
    client = docker.from_env()
    # build a docker image using docker file
    client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))
    # name for docker image
    current_user_obj = User.query.get(current_user_id)
    # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    image_name = current_user_obj.username + '-' + name
    repo_name = os.environ.get('DOCKER_REPO') + '/'

    client.images.build(path=docker_file_dir, tag=repo_name + image_name)

    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 5,
                                              'status': 'Collecting container environment information... '})

    ########## Generate Report About Build Process ##########################################################
    # The report will have various information from the creation of the container
    # for the user
    report = {}
    report["Container Report"] = {}
    report["Individual Scripts"] = {}

    # There is provenance and other information from the analyses in the container.
    # to get it we need to run the container
    container = client.containers.run(image=repo_name + image_name, \
                                      environment=["PASSWORD=" + repo_name + image_name], detach=True)

    # Grab the files from inside the container and the filter to just JSON files
    prov_files = container.exec_run("ls /home/rstudio/" + doi_to_directory(doi) + "/prov_data")[1].decode().split("\n")
    json_files = [prov_file for prov_file in prov_files if ".json" in prov_file]

    # Each json file will represent one execution so we need to grab the information from each.
    # Begin populating the report with information from the analysis and scripts
    container_packages = []
    for json_file in json_files:
        report["Individual Scripts"][json_file] = {}
        prov_from_container = \
            container.exec_run("cat /home/rstudio/" + doi_to_directory(doi) + "/prov_data/" + json_file)[1].decode()
        prov_from_container = ProvParser(prov_from_container, isFile=False)
        container_packages += get_pkgs_from_prov_json(prov_from_container)
        report["Individual Scripts"][json_file]["Input Files"] = list(
            set(prov_from_container.getInputFiles()["name"].values.tolist()))
        report["Individual Scripts"][json_file]["Output Files"] = list(
            set(prov_from_container.getOutputFiles()["name"].values.tolist()))
    container_packages = list(set([package[0] for package in container_packages]))

    # There should be a file written to the container's system that
    # lists the installed packages from when the analyses were run
    installed_packages = container.exec_run("cat listOfPackages.txt")[1].decode().split("\n")

    # The run log will show us any errors in execution
    # this will be used after report generation to check for errors when the script was
    # run inside the container
    run_log_path_in_container = "/home/rstudio/" + doi_to_directory(doi) + "/prov_data/run_log.csv"
    run_log_from_container = container.exec_run("cat " + run_log_path_in_container)

    # information from the container is no longer needed
    container.kill()

    # Finish out report generation
    report["Container Report"]["Installed Packages"] = installed_packages
    report["Container Report"][
        "Packages Called In Analysis"] = container_packages  # [list(package_pair) for package_pair in container_packages]
    report["Container Report"]["System Dependencies Installed"] = sysreqs[0].split(" ")

    # Note any missing packages
    missing_packages = []
    for package in used_packages:
        if package[0] not in installed_packages:
            missing_packages.append(package[0])

    # Error if a package or more is missing
    if (len(missing_packages) > 0):
        print(missing_packages, file=sys.stderr)
        error_message = "ContainR could not correctly install all the R packages used in the upload inside of the container. " + \
                        "Docker container could not correctly be created." + \
                        "Missing packages are: " + " ".join(missing_packages)
        clean_up_datasets()
        return {'current': 100, 'total': 100, 'status': ['Docker Build Error.',
                                                         [['Could not install R package',
                                                           error_message]]]}

    run_log_path = os.path.join(app.instance_path, 'r_datasets', doi_to_directory(doi), "run_log.csv")

    with open(run_log_path, 'wb') as f:
        f.write(run_log_from_container[1])

    if not os.path.exists(run_log_path):
        print(run_log_path, file=sys.stderr)
        error_message = "ContainR could not locate any .R files to collect provenance for. " + \
                        "Please ensure that .R files to load dependencies for are placed in the " + \
                        "top-level directory."
        clean_up_datasets()
        return {'current': 100, 'total': 100, 'status': ['Provenance collection error.',
                                                         [['Could not locate .R files',
                                                           error_message]]]}

    # check the execution log for errors
    errors_present, error_list, my_file = checkLogForErrors(run_log_path)

    if errors_present:
        clean_up_datasets()
        return {'current': 100, 'total': 100,
                'status': ['Provenance collection error while executing inside container.',
                           error_list]}

    ########## PUSHING IMG ######################################################################
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 5,
                                              'status': 'Pushing Docker image to Dockerhub... '})

    print(client.images.push(repository=repo_name + image_name), file=sys.stderr)

    ########## UPDATING DB ######################################################################

    # add dataset to database
    new_dataset = Dataset(url="https://hub.docker.com/r/" + repo_name + image_name + "/",
                          author=current_user_obj,
                          name=name,
                          report=report)
    db.session.add(new_dataset)
    db.session.commit()

    ########## CLEANING UP ######################################################################

    clean_up_datasets()
    print("Returning")
    return {'current': 5, 'total': 5,
            'status': 'containR has finished! Your new image is accessible from the home page.',
            'result': 42, 'errors': 'No errors!'}


def extractProvData(container):
    result = container.exec_run("find /home/rstudio -name 'prov_data'")
    f = open(os.path.join(app.instance_path, './docker_dir/prov.tar'), 'wb+')
    bits, stat = container.get_archive(result[1].decode("ascii").strip())

    for chunk in bits:
        f.write(chunk)
    f.close()
    container.kill()
    tar = tarfile.open(os.path.join(app.instance_path, './docker_dir/prov.tar'), "r:")
    tar.extractall(path=os.path.join(app.instance_path, './docker_dir/'))
    tar.close()


def checkLogForErrors(run_log_path):
    # check the execution log for errors
    error_list = []
    errors_present = False
    run_log_df = pd.read_csv(run_log_path)

    # assemble error messages for each file
    for _, my_row in run_log_df.iterrows():
        my_file, my_error = my_row['filename'], my_row['error']
        if my_error == 'success':
            error_list.append(my_file + 'successfully ran!')
        else:
            errors_present = True
            file_error_message = ['Error running \"' + my_file + '\"']
            # try to add a friendlier error message for common errors
            error_type = naive_error_classifier(my_error)
            if error_type:
                my_error += '<br>' + error_type
                # build up list of error messages
            file_error_message.append(my_error)
            error_list.append(file_error_message)
    return errors_present, error_list, my_file
