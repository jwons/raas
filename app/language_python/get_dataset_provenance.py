import os
import re
import sys

from Parser_py import Parser_py
from ReportGenerator import ReportGenerator

from cmd_line import cmd_line_preprocessor
from cmd_line import get_parent

def get_dataset_provenance(dire):
    orig_dir = os.getcwd()
    ins = []
    with open(dire+'run_instr.txt') as infile:
        for lines in infile.readlines():
            lines = lines.rstrip("\n")
            if(lines!=""):
                ins.append(lines)

    parser_list = []


    if(len(ins)==0):
        for dirpath,dirs,files in os.walk(dire):
            for filename in files:
                f = os.path.join(dirpath,filename)
                if(".py" in f):
                    try:
                        os.system("now run "+f)
                    except:
                        os.system("python "+f)
                        continue

                    p = Parser_py(dirpath,f)
                    parser_list.append(p)
                # if(".py" in f):
                #     os.system("now run "+f)
                #     p = Parser_py(direct,f)
                #     parser_list.append(p)
        r = ReportGenerator()
        r.generate_report(parser_list, dire)

    else:

        for cmd in ins:
            cmd = cmd.rstrip('\n')
            arr = cmd.split(" ")
            arr = list(filter(lambda x: x !='',arr))

            arr[0] = "now run"
            
            cur_dir = cmd_line_preprocessor(cmd,dire)
            par = get_parent(cmd,dire)
            cmd_str = ""
            for i in arr:
                cmd_str = cmd_str + i + " "
            cmd_str = cmd_str.rstrip()
            os.chdir(cur_dir)
            try:
                os.system(cmd_str)
            except:
                os.system(cmd)
                continue
            file_path_to_exec = re.findall("^now run\s(.*)",cmd_str)[0]
            p = Parser_py(par,file_path_to_exec)
            parser_list.append(p)
        os.chdir(orig_dir)
        r = ReportGenerator()
        r.generate_report(parser_list, dire)

if len(sys.argv) == 2:
    get_dataset_provenance(sys.argv[1])
