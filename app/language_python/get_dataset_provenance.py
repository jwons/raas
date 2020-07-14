import os
import sys

from Parser_py import Parser_py
from ReportGenerator import ReportGenerator


def get_dataset_provenance(direct, run_instr):
    print(run_instr)
    run_instr=run_instr.replace(","," ")
    print("!")
    parser_list = []
    files = os.listdir(direct)
    for f in files:
        if ".py" in f:
            os.system("now run " + direct + f + " " + run_instr)
            p = Parser_py(direct, direct + f, run_instr)
            parser_list.append(p)

    r = ReportGenerator()
    r.generate_report(parser_list, direct)


if len(sys.argv) > 1:
    get_dataset_provenance(sys.argv[1],sys.argv[2])
