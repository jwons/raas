import os
import re
import sys

from Parser_py import Parser_py
from ReportGenerator import ReportGenerator

from cmd_line import cmd_line_preprocessor
from cmd_line import get_parent


def get_dataset_provenance(dataset_dir, dockerfile_dir):
    orig_dir = os.getcwd()

    # Gather user-provided arguments for running scripts, if provided
    ins = []
    with open(dockerfile_dir + 'run_instr.txt') as infile:
        for lines in infile.readlines():
            lines = lines.rstrip("\n")
            if (lines != ""):
                ins.append(lines)

    parser_list = []

    # If the user provided no instructions for how to run the scripts, search for Python files
    # and execute them using no workflow without arguments
    if (len(ins) == 0):

        # Browse through all directories in the dataset and search for Python files
        for dirpath, dirs, files in os.walk(dataset_dir):
            for filename in files:
                if (".py" in filename):
                    f = os.path.join(dirpath, filename)

                    # Attempt to execute with no workflow,
                    # if it fails execute normally
                    os.chdir(dirpath)
                    try:
                        os.system("now run " + f)
                    except:
                        os.system("python " + f)
                        continue

                    p = Parser_py(dirpath, f)
                    parser_list.append(p)
                # if(".py" in f):
                #     os.system("now run "+f)
                #     p = Parser_py(direct,f)
                #     parser_list.append(p)

        # Once all scripts have completed executing, return to Dockerfile directory
        # and begin to write the report, the rest of which is completed back in RaaS
        os.chdir(orig_dir)
        r = ReportGenerator()
        r.generate_report(parser_list, dockerfile_dir)

    else:

        for cmd in ins:
            cmd = cmd.rstrip('\n')
            arr = cmd.split(" ")
            arr = list(filter(lambda x: x != '', arr))

            arr[0] = "now run"

            cur_dir = cmd_line_preprocessor(cmd, dockerfile_dir)
            par = get_parent(cmd, dockerfile_dir)
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
            file_path_to_exec = re.findall("^now run\s(.*)", cmd_str)[0]
            p = Parser_py(par, file_path_to_exec)
            parser_list.append(p)
        os.chdir(orig_dir)
        r = ReportGenerator()
        r.generate_report(parser_list, dockerfile_dir)


if len(sys.argv) == 3:
    get_dataset_provenance(sys.argv[1], sys.argv[2])
