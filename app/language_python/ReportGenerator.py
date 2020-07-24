import json
import os


class ReportGenerator:

    def generate_report(self, parserlist, target_path):
        scripts = {}
        for parser in parserlist:
            key_value = parser.get_file_info()
            scripts[list(key_value.keys())[0]] = list(key_value.values())[0]
        with open(os.path.join(target_path, "script_info.json"), 'w+') as outputfile:
            json.dump(scripts, outputfile)

        return 0