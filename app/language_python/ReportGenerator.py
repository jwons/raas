import json
import os


class ReportGenerator:

    def generate_report(self, parserlist,target_path):
        scripts=[]
        for parser in parserlist:
            scripts.append(parser.get_file_info())
        with open(os.path.join(target_path,"script_info.json"), 'w+') as outputfile:
            json.dump(scripts, outputfile)

        # print("HERE IS the output" + str(jsontext))
        return 0

    def get_pkg_report(self, pkg_list):
        pkg_report = []
        for p in pkg_list:
            pkg_report.append({"name": p[0], "version": p[1]})
        return pkg_report

    def get_script_report(self, script):
        json_text = {"script " + str(script.get_id()) + ", line " + str(script.get_line()):
                        {"input files": script.get_input_files(), "output files": script.get_output_files()}}
        return json_text
