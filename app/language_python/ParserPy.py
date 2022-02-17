import json
import os
import pdb
import sqlite3


class ParserPy:
    # modification made by Akash
    # removed arguments parameter and added it to filepath, so its not filepath anymore, its command line
    def __init__(self, dir_path, filepath):

        # os.system("now run " + filepath + " " + arguments)
        conn = sqlite3.connect(dir_path + '/.noworkflow/db.sqlite')
        self.filepath = filepath
        self.cursor = conn.cursor()
        self.cursor.execute('select MAX(id) from trial where command= ? ', (str("run " + filepath),))
        self.trial_id = self.cursor.fetchall()[0][0]

    def get_file_info(self):
        self.cursor.execute(
            'SELECT DISTINCT t.script, f.name, f.mode, f.content_hash_before, f.content_hash_after '
            'FROM trial t, file_access f '
            'WHERE t.id = ? AND t.id= f.trial_id '
            'ORDER by t.script ', (self.trial_id,))
        file_info = self.cursor.fetchall()
        if len(file_info) >= 1:
            script_current = Script(file_info[0][0])
            for i in range(0, len(file_info)):
                f = file_info[i]

                # When the f[3] is None this means there is no content hash from before file access
                # Therefore it has to be a write
                if f[3] is None:
                    script_current.add_output_file(f[1])
                    continue
                if f[3] == f[4]:
                    script_current.add_input_file(f[1])
                    continue
                else:
                    script_current.add_output_file(f[1])

                '''
                if "r" in f[2]:
                    script_current.add_input_file(f[1])
                if "w" in f[2]:
                    script_current.add_output_file(f[1])
                if "a" in f[2]:
                    script_current.add_output_file(f[1])
                if "+" in f[2] and f[3] != f[4]:
                    script_current.add_output_file(f[1])
                '''
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
            if p[0] is not None and "site-packages" in p[0]:
                pkg_name = p[0].split("site-packages")[1].split("\\")[1].replace("_", "")
                pkg_list.append((pkg_name.replace(".py", ""), p[1]))
        return pkg_list

    @staticmethod
    def get_pkg_report(pkg_list):
        pkg_report = []
        for p in pkg_list:
            pkg_report.append({"name": p[0], "version": p[1]})
        return pkg_report

    @staticmethod
    def get_whole_report(pkg_report, script_report):
        jsontext = {
            'Pyplace Report': {"Modules Depended": pkg_report, "Individual Scripts": script_report}}
        return jsontext


class Script(object):

    def __init__(self, arg_id):
        self.input_files = []
        self.output_files = []
        self.id = arg_id

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
