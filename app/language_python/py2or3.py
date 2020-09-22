# This module will help figuring out if the given code is python2 or python3

import re

# we initially assume that the code is python3

# Removing the commented part of a line
def removeCommentedPart(line):
    f = line.find('#')
    if(f==-1):
        return line
    else:
        return line[0:f]

def python2or3(filename):
    # filename contains the absolute path to the filename

    python2 = False
    python3 = True 
    line = ""
    with open(filename,'r') as infile:
        for line in infile.readlines():
            line = removeCommentedPart(line)
            line = re.sub(r"([\"\'])(?:(?=(\\?))\2.)*?\1",'',line) # This removes everything within quotes (does consider back-slashes, uses look-ahead regex)
            check = re.match("\s*(print\s*[^\s\(])",line) # matching for string which does not start with 'print ('  (only py2)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.match("\s*(print\s*$)",line) # matching for string only 'print' (only py2)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.match("\s*(print)",line) # matching for print("...",sep=..,end=...,file=...) (only py3)
            if(check!=None):
                arr = line.split(',')
                for i in arr:
                    i = i.lstrip()
                    if(i.startswith("sep") | i.startswith("end") | i.startswith("file")):
                        python3 = True
                        python2= False
                        break

            check = re.search("(xrange)\s*\(",line) # matching for string xrange (only py2)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.search("(raw_input)\s*\(",line) # matching for string raw_input (only py2)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.search("(\.has_key)\s*\(",line) # matching for string .has_key (only py2)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.search("(\.iteritems)\s*\(",line)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.search("nonlocal",line) # matching for string nonlocal
            if(check!=None):
                python2 = False
                python3 = True
                break

            check = re.search("<>",line)
            if(check!=None):
                python2 = True
                python3 = False
                break

            check = re.search("`",line)
            if(check!=None):
                python2 = True
                python3 = False
                break
    print(line)
    return python3

