# This module modifies absolute paths found in the code

import re
import os

import app.files_list as files_list
import app.exceptions as exceptions

# Given a list of abs. address of files with same name, and user given address of file, this module finds the accurate abs. address of the file
def get_correct_path(arr,s,splitter):
    # arr -> list of abs. address
    # s -> user given address of file
    # splitter -> '/' or '\' for string s

    if(arr == []):
        return None

    path_s = s.split(splitter)
    path_s = list(filter(lambda x: x !='',path_s)) # remove empty string elements from the array
    path_arr = []
    for i in arr:
        temp  = i.split('/')
        temp = list(filter(lambda x: x !='',temp)) # remove empty string elements from the array    
        path_arr.append(temp)
    score_map = []
    max_score = 0
    for paths in path_arr:
        j=-1
        while(j>=-len(paths) and j>=-len(path_s) and paths[j]==path_s[j]):
            j=j-1
        score = -j-1
        score_map.append(score)

    ans = []
    for i in range(len(path_arr)):
        if(score_map[i] > max_score):
            max_score = score_map[i]
            ans = path_arr[i]

    unique = 0 
    for scores in score_map:
        if(scores == max_score):
            unique = unique + 1
    
    if(unique > 1):
        raise exceptions.DuplicateError

    ret_str = ''
    for i in ans:
        ret_str =  ret_str + '/' +  i
    return ret_str

def get_correct_dir(arr,s,splitter):

    if(arr==[]):
        return None

    path_s = s.split(splitter)
    path_s = list(filter(lambda x: x !='',path_s)) # remove empty string elements from the array
    new_s = ''
    for i in range(0,len(path_s)-1):
        new_s = new_s +splitter+i
    return get_correct_path(arr,new_s,splitter)

# preprocesses any absolute paths found in the script
def path_preprocess(file_name,folder_path,hash): 
    # file_name is absolute path of the file to be preprocessed
    with open(file_name,'r') as infile:
        store = infile.readlines()
        finish_with_slash = False
        dir_path = folder_path+'/'
        for j in range(len(store)):
            line = store[j]
            check = re.match(r"[^+]*([\'\"]/)",line)  # Linux machine absolute paths
            if(check!=None):
                print(line)
                arr = re.findall(r"[\'\"](/[^\'\"]*/[^\'\"]*)[\'\"]",line)  # searching for two slashes to prevent false positives (mostly escape sequences), assumption made no one works in the root directory (atleast in linux)
                for i in arr:

                    finish_with_slash = False

                    paths = i.split('/')
                    if(paths[-1]== ''):
                        finish_with_slash = True
                    paths = list(filter(lambda x: x !='',paths)) # remove empty string elements from the array
                    pointer=-1

                    if(len(paths)<=1):
                        continue

                    needed_file = paths[pointer]
                    needed_dir= paths[pointer-1]

                    ps = hash[needed_file]

                    new_path = get_correct_path(ps,i,'/')

                    if(new_path!=None):
                        if(finish_with_slash):
                            line = line.replace(i,new_path+'/',1)
                        else:
                            line = line.replace(i,new_path,1)
                    else:
                        ns = hash[needed_dir]
                        new_dir = get_correct_dir(ns,i,'/')
                        if(new_dir!=None):
                            if(finish_with_slash):
                                line = line.replace(i,new_dir+'/'+needed_file+'/',1)
                            else:
                                line = line.replace(i,new_dir+'/'+needed_file,1)
                        else:
                            if(finish_with_slash):
                                line = line.replace(i,dir_path+needed_file+'/',1)
                            else:
                                line = line.replace(i,dir_path+needed_file,1) # Home directory of user's code

                store[j] = line
                
                
                print(line)
                
                
                continue
            else:
                pass

            check = re.match("[^+]*[\'\"]\w:(.*)[\'\"]",line) # Windows absolute path type1

            if(check!=None):
                arr = re.findall("[\'\"](\w:.*)[\'\"]",line)

                for i in arr:
                    finish_with_slash = False
                    start = i[0:2]
                    i = i[2:]
                    paths = i.split('\\')
                    if(paths[-1]== ''):
                        finish_with_slash = True
                    paths = list(filter(lambda x: x !='',paths)) # remove empty string elements from the array
                    pointer=-1

                    if(len(paths)<=1):
                        continue

                    needed_file = paths[pointer]
                    needed_dir = paths[pointer-1]

                    ps = hash[needed_file]

                    new_path = get_correct_path(ps,i,'\\')

                    if(new_path!=None):
                        if(finish_with_slash):
                            line = line.replace(start+i,new_path+'/',1)
                        else:
                            line = line.replace(start+i,new_path,1)
                    else:
                        ns = hash[needed_dir]
                        new_dir = get_correct_dir(ns,i,'\\')
                        if(new_dir!=None):
                            if(finish_with_slash):
                                line = line.replace(start+i,new_dir+'/'+needed_file+'/',1)
                            else:
                                line = line.replace(start+i,new_dir+'/'+needed_file,1)
                        else:
                            if(finish_with_slash):
                                line = line.replace(start+i,dir_path+needed_file+'/',1)
                            else:
                                line= line.replace(start+i,dir_path+needed_file,1) # Home directory of user's code
                store[j] = line

                print(line)


                continue
            else:
                pass

            check = re.match(r"[^+]*([\'\"]\\)",line)  # windows absolute path type2

            if(check!=None):
                arr = re.findall(r"[\'\"](\\[^\'\"]*\\[^\'\"]*)[\'\"]",line) # search for ' \xyz\abc ', we see two slashes to prevent matching with common single escape sequences 
                for i in arr:
                    finish_with_slash = False
                    paths = i.split('\\')
                    if(paths[1]!=''):
                        if(paths[1][0] == 'r' or paths[1][0]=='t' or paths[1][0]== 'n' or paths[1][0]== ' ' or paths[1][0]=='"' or paths[1][0]=='a' or paths[1][0]== 'b' or paths[1][0]=='f' or paths[1][0]=='N' ): # paths[0] will exists as \ is matched
                            continue
                    if(paths[-1]== ''):
                        finish_with_slash = True
                    paths = list(filter(lambda x: x !='',paths)) # remove empty string elements from the array
                    pointer=-1

                    if(len(paths)<=1):
                        continue

                    needed_file = paths[pointer]
                    needed_dir = paths[pointer-1]

                    ps = hash[needed_file]
                    new_path = get_correct_path(ps,i,'\\')

                    if(new_path!=None):
                        if(finish_with_slash):
                            line = line.replace(i,new_path+'/',1)
                        else:
                            line = line.replace(i,new_path,1)
                    else:
                        ns = hash[needed_dir]
                        new_dir = get_correct_dir(ns,i,'\\')
                        if(new_dir!=None):
                            if(finish_with_slash):
                                line = line.replace(i,new_dir+'/'+needed_file+'/',1)
                            else:
                                line = line.replace(i,new_dir+'/'+needed_file,1)
                        else:
                            if(finish_with_slash):
                                line= line.replace(i,dir_path+needed_file+'/',1)
                            else:
                                line= line.replace(i,dir_path+needed_file,1)
                store[j] = line

                print(line)


            else:
                pass

    with open(file_name,'w') as outfile:
        outfile.writelines(store)

    print("path preprocessed for "+file_name)
