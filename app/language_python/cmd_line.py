# cmd_line.py :
#       cmd_line_preprocessor -> Takes an input of the user given command line and the folder name which contains the user's scripts and data
#                             -> returns the absolute address of the directory from which the command line has to be run

#       finder                -> Takes a list of absolute paths of directories having the same name and the path given by the user which is relative to the directory name
#                             -> returns the correct absolute path of the directory

# User defined modules

from collections import defaultdict

class invalidCMDError(Exception): # The CMD is of invalid format
    pass

class nonPythonError(Exception): # The first word of the command is not python nor python2 nor python3
    pass
    
class DuplicateError(Exception): # Two files exist with the same name
    pass

class DirectoryError(Exception): # Given directory doesn't exist or duplicate directories
    pass

class PathError(Exception): # Path not valid
    pass

class fileNotFoundError(Exception): # file name not found
    pass

# Built in python modules
import re
from pathlib import Path
import os

def generate_multimap(dir): # This maps filenames to their absolute path, this is one to many, as there can be same filenames with different paths
    p = Path(dir)
    arr = defaultdict(list)
    for i in p.rglob('*'):
        arr[i.name].append(str(i.resolve()))
    return arr

def get_parent(cmd,folder_name):
    
    arr = cmd.split(' ')
    arr = list(filter(lambda x: x !='', arr)) # remove empty string elements from the array
    path_of_file_to_be_executed = arr[1]
    l = re.split(r'/|\\',path_of_file_to_be_executed) # Paths may contain back slash or forward slash
            #l = path_of_file_to_be_executed.split('/') # Have to check with windows environment later
            
    l = list(filter(lambda x: x !='', l)) # remove empty string elements from the array
    Dfdict = generate_multimap(folder_name)
    ar = Dfdict[l[-1]]
    if(ar==[]):
        raise DirectoryError
    else:
        return finder(ar,l)
    

def finder(ar,l):
    # ar -> list of absolute paths of directories with the same name
    # l  -> rel. path given by user

    str_cat = ''
    location = ''
    path_found = False
    for j in range(1,len(l)):
        str_cat = str_cat +'/' + l[j] # concating rel. path given by user to absolute path of directory to identify the right directory
    for i in ar:
        new_path = i + str_cat
        if(os.path.exists(new_path)):
            if(path_found==False):
                path_found =True
                location = new_path
            else:
                return DuplicateError
    if(path_found):
        p  =Path(location)
        return str(p.parent)
    else:
        return PathError

def cmd_line_preprocessor(cmd,folder_name):
    # cmd - string containing the user given command line

    Dfdict = generate_multimap(folder_name) # Dfdict - filename -> file address multi map (ie. one key to many values), default value of Dfdict is [] 
    
    # Convert command line from string format to array format
    arr = cmd.split(' ')
    arr = list(filter(lambda x: x !='', arr)) # remove empty string elements from the array
    
    if(len(arr)<2):
        raise invalidCMDError
    else:
        if(arr[0] in ['python','python2','python3']):
            path_of_file_to_be_executed = arr[1]
            
            l = re.split(r'/|\\',path_of_file_to_be_executed) # Paths may contain back slash or forward slash
            #l = path_of_file_to_be_executed.split('/') # Have to check with windows environment later
            
            l = list(filter(lambda x: x !='', l)) # remove empty string elements from the array

            if(len(l)==1): # Directory of execution will be the same location as the executable python file
                ar = Dfdict[l[0]]
                if(len(ar)==1):
                    return str(Path(ar[0]).parent)
                elif(len(ar)==0):
                    raise fileNotFoundError
                else: # only file name given by user but there exists two files with same name
                    raise DuplicateError
                    # return None # error to be raised
            else:
                ar = Dfdict[l[0]] # The directory of execution will be the parent dir of l[0], ex: python3 code/file.py, the directory containing code is the directory of execution
                if(ar==[]):
                    raise DirectoryError
                else:
                    return finder(ar,l)
        else:
            raise nonPythonError
