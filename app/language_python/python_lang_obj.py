from pathlib import Path

from app.files_list import generate_multimap, generate_modules, generate_set, generate_multimap2
from app.language_python.py2or3 import python2or3
from app.language_python.decommenter import remove_comments_and_docstrings
from app.pathpreprocess import path_preprocess
from app.ast_test import get_imports
from app.language_python.pylint_parse import pylint_parser

import requests
import subprocess
import json
from pathlib import Path

import os
import shutil

import zipfile
import docker
import cgi
from app.models import User
from app import app

from shutil import copy

from app.language_interface import language_interface


class py_lang(language_interface):

    def temp_name(self, path):
        p_obj = Path(path)
        filename = p_obj.stem
        temp_filename = filename + '_temp.py'
        par = p_obj.parent
        temp_path = os.path.join(par, temp_filename)
        return temp_path

    def script_analysis(self, preprocess, dataverse_key='', doi='', data_folder='', user_pkg=''):
        if data_folder:  # if a set of scripts have been uploaded then its converted to a normal zip file format (ie. zip a folder)
            # zip_path = os.path.join(app.instance_path, 'datasets',
            #                         zip_file)  # instance_path -> key path in the server
            # unzip the zipped directory and keep the zip file
            # with open(zip_path) as zip_ref:
            dir_name = data_folder
            # zip_ref.extractall(os.path.join(app.instance_path, 'datasets', dir_name))

            # find name of unzipped directory
            dataset_dir = os.path.join(app.instance_path, 'datasets', dir_name)
            doi = dir_name
        else:
            #TODO suppot this or remove it
            dataset_dir = os.path.join(app.instance_path, 'datasets', self.doi_to_directory(doi),
                                       self.doi_to_directory(doi))
            success = self.download_dataset(doi=doi, dataverse_key=dataverse_key,
                                            destination=os.path.join(app.instance_path, 'datasets',
                                                                     self.doi_to_directory(doi)))
            dir_name = self.doi_to_directory(doi)
            if not success:
                self.clean_up_datasets()
                return {'current': 100, 'total': 100, 'status': ['Data download error.',
                                                                 [['Download error',
                                                                   'There was a problem downloading your data from ' + \
                                                                   'Dataverse. Please make sure the DOI is correct.']]]}
        pyfiles = generate_set(dataset_dir)

        py2 = False
        if preprocess:
            # try:
            # iterate through list of all python files to figure out if its python2 or python3
            hash = generate_multimap2(dataset_dir + "/data_set_content", dir_name)
            print(hash)
            for file in pyfiles:
                print(file)
                path_preprocess(file, "/home/datasets/" + dir_name + "/data_set_content", hash)
            # except:
            # pass

        user_defined_modules = generate_modules(dataset_dir + "/data_set_content")

        unknown_pkgs = set()
        docker_pkgs = set()
        pkgs_to_ask_user = set()
        temp_pyfiles = []

        for file in pyfiles:
            with open(file) as infile:
                inp = infile.read()
            new_inp = remove_comments_and_docstrings(inp)
            temp_filename = self.temp_name(file)

            temp_pyfiles.append(temp_filename)

            with open(temp_filename, 'w+') as outfile:
                outfile.write(new_inp)

            py3 = python2or3(temp_filename)

            if (py3 == False):
                py2 = True

        if (py2 == True):
            py3 = False

        for file in pyfiles:
            try:
                (unknown, dockerpkg) = get_imports(file, dir_name, user_defined_modules, py3)
            except Exception as e:
                p_ob = Path(file)
                strp = ''
                for i in e.args:
                    strp = strp + str(i) + ' '
                self.clean_up_datasets()
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [[
                                                                     'Error in AST generation of ' + p_ob.name,
                                                                     strp]]]}
            unknown_pkgs = unknown_pkgs.union(unknown)
            docker_pkgs = docker_pkgs.union(dockerpkg)

        for temp in temp_pyfiles:
            os.remove(temp)

        user_pkg_json = {}
        if (user_pkg != ''):
            user_pkg_json = json.loads(user_pkg)["pkg"]

        pkg_dict = {}
        for p in user_pkg_json:
            pkg_dict[p['pkg_name']] = p['installation_cmd']

        for pkgs in unknown_pkgs:
            if not (pkgs in pkg_dict):
                pkgs_to_ask_user.add(pkgs)

        if (len(pkgs_to_ask_user) != 0):
            missing_modules = ''
            for pkg in pkgs_to_ask_user:
                missing_modules += pkg + ','
            self.clean_up_datasets()
            return {'current': 100, 'total': 100, 'status': ['Modules not found.',
                                                             [[
                                                                 'Kindly mention the pypi package name of these unknown modules or upload these missing modules',
                                                                 missing_modules[:-1]]]]}

        # If even a single file contains python2 specific code then we take the entire dataset to be of python2
        if (py2):
            py3 = False

        for p in pyfiles:
            error, err_mesg = pylint_parser(p, py3)
            if (error):
                p_obj = Path(p)
                self.clean_up_datasets()
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [[
                                                                     'Error identified by static analysis of ' + p_obj.name,
                                                                     err_mesg]]]}
        return {"dir_name": dir_name, "docker_pkgs": docker_pkgs, "is_python_2": py2}

    def create_report(self, current_user_id, name, dir_name, time):
        client = docker.from_env()
        current_user_obj = User.query.get(current_user_id)
        # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        container = client.containers.run(image=repo_name + image_name,
                                          environment=["PASSWORD=" + repo_name + image_name],
                                          detach=True, command="tail -f /dev/null")

        container_packages = \
            json.loads(container.exec_run("cat /home/datasets/" +
                                          dir_name + "/data_set_content/script_info.json")[1].decode())
        installed_packages = \
            container.exec_run("cat /home/datasets/" + dir_name + "/data_set_content/listOfPackages.txt")[
                1].decode().split("\n")
        container.kill()
        report = {"Container Report": {}, "Individual Scripts": {}}
        # Finish out report generation
        report["Container Report"]["Installed Packages"] = installed_packages
        report["Individual Scripts"] = container_packages
        return report

    def build_docker_package_install(self, module):
        return "RUN pip install " + module + "\n"

    def build_docker_file(self, dir_name, docker_pkgs, additional_info, code_btw, run_instr):

        ext_pkgs = code_btw

        with open('app/language_python/run_instr.txt', 'w+') as out:
            for instr in run_instr:
                out.write(instr + '\n')

        docker_wrk_dir = '/home/datasets/' + dir_name + '/'
        docker_file_dir = '/home/datasets/' + dir_name + '/data_set_content/'
        docker_home = '/home/datasets/' + dir_name + '/'
        try:
            os.makedirs(os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content'))
        except:
            pass
        with open(os.path.join(app.instance_path, 'datasets', dir_name, 'Dockerfile'), 'w+') as new_docker:

            if additional_info["is_python_2"]:
                new_docker.write('FROM python:2\n')
                python_ver = 2
            else:
                new_docker.write('FROM python:3\n')
                python_ver = 3

            new_docker.write('WORKDIR /home/\n')
            new_docker.write('RUN git clone https://github.com/gems-uff/noworkflow.git\n')

            new_docker.write('WORKDIR /home/noworkflow/\n')
            new_docker.write('RUN git checkout 2.0-alpha\n')
            new_docker.write('RUN python' + str(python_ver) + ' -m pip install -e capture\n')
            # new_docker.write('WORKDIR /home/datasets/' + dir_name + '/\n')
            new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')
            # new_docker.write('ADD data_set_content /home/datasets/' + dir_name + '\n')
            new_docker.write('ADD data_set_content ' + docker_file_dir + '\n')
            copy("app/language_python/get_dataset_provenance.py", "instance/datasets/" + dir_name)
            copy("app/language_python/Parser_py.py", "instance/datasets/" + dir_name)
            copy("app/language_python/ReportGenerator.py", "instance/datasets/" + dir_name)
            copy("app/language_python/cmd_line.py", "instance/datasets/" + dir_name)
            copy("app/language_python/run_instr.txt", "instance/datasets/" + dir_name)
            # shutil.copytree("app/language_python/noworkflow","instance/datasets/"+dir_name+"/noworkflow/")
            # new_docker.write('COPY get_dataset_provenance.py /home/datasets/\n')
            new_docker.write('COPY get_dataset_provenance.py ' + docker_home + '\n')
            # new_docker.write('COPY cmd_line.py /home/datasets/\n')
            # new_docker.write('COPY Parser_py.py /home/datasets/\n')
            # new_docker.write('COPY ReportGenerator.py /home/datasets/\n')

            new_docker.write('COPY cmd_line.py ' + docker_home + '\n')
            new_docker.write('COPY Parser_py.py ' + docker_home + '\n')
            new_docker.write('COPY ReportGenerator.py ' + docker_home + '\n')
            new_docker.write('COPY run_instr.txt ' + docker_file_dir + '\n')

            # new_docker.write('RUN chmod a+rwx -R /home/datasets/' + dir_name + '\n')
            new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
            new_docker.write('WORKDIR ' + docker_file_dir + '\n')

            for mod in ext_pkgs:
                new_docker.write("RUN " + mod + "\n")
            if docker_pkgs:
                for module in docker_pkgs:
                    new_docker.write(self.build_docker_package_install(module))
            if(python_ver==2):
                new_docker.write('RUN pip install pathlib\n')

            # new_docker.write("RUN pip list > /home/datasets/" + dir_name + "/listOfPackages.txt \n")
            new_docker.write("RUN pip list > " + docker_file_dir + "listOfPackages.txt \n")

            # new_docker.write("RUN python3 " \
            #                     + "/home/datasets/get_dataset_provenance.py" + " /home/datasets/" +
            #                     dir_name + "/ " + allinstr +"\n")
            # if(allinstr==""):
            #    new_docker.write("RUN echo \"\" > run_instr.txt\n")
            # else:
            #    new_docker.write("RUN echo -e \"" + allinstr + "\" > run_instr.txt \n")

            new_docker.write("RUN python" + str(python_ver) + " " \
                             + docker_home + "get_dataset_provenance.py" + " " + docker_file_dir + "\n")

        return os.path.join(app.instance_path, 'datasets', dir_name)
