import os
import sys

from Parser_py import Parser_py
from ReportGenerator import ReportGenerator


def get_dataset_provenance(direct):
    print("!")
    parser_list=[]
    files = os.listdir(direct)
    for f in files:
        if ".py" in f:
            os.system("now run " + direct + f)
            p = Parser_py(direct,direct+f, "")
            parser_list.append(p)

    r = ReportGenerator()
    r.generate_report(parser_list,direct)

if len(sys.argv)>1:
    get_dataset_provenance(sys.argv[1])
