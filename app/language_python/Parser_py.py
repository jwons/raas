import json
import os
import sqlite3


class Parser_py:
    def __init__(self, dir_path, filepath, arguments):

        # os.system("now run " + filepath + " " + arguments)
        conn = sqlite3.connect(dir_path + '/.noworkflow/db.sqlite')
        self.filepath = filepath
        self.cursor = conn.cursor()
        self.cursor.execute('select MAX(id) from trial where command= ? ', (str("run " + filepath),))
        self.trial_id = self.cursor.fetchall()[0][0]

    def get_file_info(self):
        self.cursor.execute(
            'SELECT DISTINCT t.script, f.name, f.mode '
            'FROM trial t, file_access f '
            'WHERE t.id = ? AND t.id= f.trial_id '
            'ORDER by t.script ', (self.trial_id,))
        file_info = self.cursor.fetchall()
        if len(file_info) >= 1:
            script_current = Script(file_info[0][0])
            for i in range(0, len(file_info)):
                f = file_info[i]
                if f[2] == "rU" or f[2] == "rb":
                    script_current.add_input_file(f[1])
                if f[2] == "wU" or f[2] == "wb":
                    script_current.add_output_file(f[1])
            return script_current.get_script_report()
        else:
            self.cursor.execute(
                'SELECT DISTINCT t.script '
                'FROM trial t '
                'WHERE t.id = ? ', (self.trial_id,))
            file_info = self.cursor.fetchall()
            script_current = Script(file_info[0][0])
            return script_current.get_script_report()



    def get_module_info(self):
        self.cursor.execute("select name,version from module where trial_id=?", (self.trial_id,))
        module_list = self.cursor.fetchall()
        return module_list

    def get_pkg_info(self):
        self.cursor.execute("select path,version from module where trial_id=?", (self.trial_id,))
        path_list = self.cursor.fetchall()
        pkg_list = []
        for p in path_list:
            print(p[0])
            if p[0] is not None and "site-packages" in p[0]:
                pkg_name = p[0].split("site-packages")[1].split("\\")[1].replace("_", "")
                pkg_list.append((pkg_name.replace(".py", ""), p[1]))
        return pkg_list

    def get_pkg_report(self, pkg_list):
        pkg_report = []
        for p in pkg_list:
            pkg_report.append({"name": p[0], "version": p[1]})
        return pkg_report

    def get_whole_report(self, pkg_report, script_report):
        jsontext = {
            'Pyplace Report': {"Modules Depended": pkg_report, "Individual Scripts": script_report}}
        return (jsontext)


class Script(object):

    def __init__(self, id):
        self.input_files = []
        self.output_files = []
        self.id = id

    def get_id(self):
        return self.id

    def get_output_files(self):
        return self.output_files

    def get_input_files(self):
        return self.input_files

    def add_input_file(self, file):
        self.input_files.append(file)

    def add_output_file(self, file):
        self.output_files.append(file)

    def get_script_report(self):
        jsontext = {str(self.get_id()):
                        {"input files": self.input_files, "output files": self.output_files}}

        return jsontext
