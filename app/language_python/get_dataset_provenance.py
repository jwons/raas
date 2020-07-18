import os
import re
import sys

from Parser_py import Parser_py
from ReportGenerator import ReportGenerator

from cmd_line import cmd_line_preprocessor
from cmd_line import get_parent

def get_dataset_provenance(dire):
    direct = dire + '/data_set_content/'
    orig_dir = os.getcwd()
    ins = []
    with open(direct+'run_instr.txt') as infile:
        for lines in infile.readlines():
            lines = lines.rstrip("\n")
            if(lines!=""):
                ins.append(lines)

    parser_list = []


    if(len(ins)==0):
        for dirpath,dirs,files in os.walk(direct):
            for filename in files:
                f = os.path.join(dirpath,filename)
                if(".py" in f):
                    os.system("now run "+f)

                    p = Parser_py(dirpath,f)
                    parser_list.append(p)
                # if(".py" in f):
                #     os.system("now run "+f)
                #     p = Parser_py(direct,f)
                #     parser_list.append(p)
        r = ReportGenerator()
        r.generate_report(parser_list, direct)

    else:

        for cmd in ins:
            cmd = cmd.rstrip('\n')
            arr = cmd.split(" ")
            arr = list(filter(lambda x: x !='',arr))

            arr[0] = "now run"
            
            file_to_exec = re.split(r'/|\\',arr[1])[-1]
            
            cur_dir = cmd_line_preprocessor(cmd,direct)
            par = get_parent(cmd,direct)
            cmd_str = ""
            for i in arr:
                cmd_str = cmd_str + i + " "
            os.chdir(cur_dir)
            os.system(cmd_str)
            p = Parser_py(par,file_to_exec)
            parser_list.append(p)
        os.chdir(orig_dir)
        r = ReportGenerator()
        r.generate_report(parser_list, direct)

if len(sys.argv) == 2:
    get_dataset_provenance(sys.argv[1])
