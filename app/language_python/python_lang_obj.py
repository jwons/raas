from app.language_python.files_list import generate_modules, generate_set, generate_multimap2
from app.language_python.py2or3 import python2or3
from app.language_python.decommenter import remove_comments_and_docstrings
from app.language_python.pathpreprocess import path_preprocess
from app.language_python.ast_test import get_imports
from app.language_python.pylint_parse import pylint_parser

import json
from pathlib import Path

import os

import docker
from app.models import User
from app import app

from shutil import copy

from app.languageinterface import LanguageInterface
from app.languageinterface import StaticAnalysisResults


class PyLang(LanguageInterface):

    def __init__(self):
        self.dataset_dir = None

    @staticmethod
    def temp_name(path):
        p_obj = Path(path)
        filename = p_obj.stem
        temp_filename = filename + '_temp.py'
        par = p_obj.parent
        temp_path = os.path.join(par, temp_filename)
        return temp_path

    def script_analysis(self, preprocess=False, data_folder='', run_instr='', user_pkg=''):
        dockerfile_dir = self.get_dockerfile_dir(data_folder)
        self.dataset_dir = os.path.join(dockerfile_dir, os.listdir(dockerfile_dir)[0])

        pyfiles = generate_set(self.dataset_dir)

        py2 = False
        py3 = False
        if preprocess:
            # try:
            # iterate through list of all python files to figure out if its python2 or python3
            hash_multimap = generate_multimap2(self.dataset_dir + "/data_set_content", data_folder)
            print(hash_multimap)
            for file in pyfiles:
                print(file)
                path_preprocess(file, "/home/datasets/" + data_folder + "/data_set_content", hash_multimap)

        user_defined_modules = generate_modules(self.dataset_dir)

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

            if not py3:
                py2 = True

        if py2:
            py3 = False

        for file in pyfiles:
            try:
                (unknown, docker_pkg) = get_imports(file, data_folder, user_defined_modules, py3)
            except Exception as e:
                p_ob = Path(file)
                strp = ''
                for i in e.args:
                    strp = strp + str(i) + ' '
                self.clean_up_datasets(data_folder)
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [[
                                                                     'Error in AST generation of ' + p_ob.name,
                                                                     strp]]]}
            unknown_pkgs = unknown_pkgs.union(unknown)
            docker_pkgs = docker_pkgs.union(docker_pkg)

        for temp in temp_pyfiles:
            os.remove(temp)

        user_pkg_json = {}
        if user_pkg != '':
            user_pkg_json = json.loads(user_pkg)["pkg"]

        pkg_dict = {}
        for p in user_pkg_json:
            pkg_dict[p['pkg_name']] = p['installation_cmd']

        for pkgs in unknown_pkgs:
            if not (pkgs in pkg_dict):
                pkgs_to_ask_user.add(pkgs)

        if len(pkgs_to_ask_user) != 0:
            missing_modules = ''
            for pkg in pkgs_to_ask_user:
                missing_modules += pkg + ','
            self.clean_up_datasets(data_folder)
            return {'current': 100, 'total': 100, 'status': ['Modules not found.',
                                                             [[
                                                                 'Kindly mention the pypi package name of these '
                                                                 'unknown modules or upload these missing modules',
                                                                 missing_modules[:-1]]]]}

        # If even a single file contains python2 specific code then we take the entire dataset to be of python2
        if py2:
            py3 = False

        for p in pyfiles:
            error, err_message = pylint_parser(p, py3)
            if error:
                p_obj = Path(p)
                self.clean_up_datasets(data_folder)
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [['Error identified by static analysis of '
                                                                   + p_obj.name,
                                                                   err_message]]]}

        return StaticAnalysisResults(lang_packages=docker_pkgs, sys_libs=None, lang_specific={"is_python_2": py2})

    def build_docker_file(self, dir_name, static_results, code_btw, run_instr):

        ext_pkgs = code_btw

        with open('app/language_python/run_instr.txt', 'w+') as out:
            for instr in run_instr:
                out.write(instr + '\n')

        container_workdir = '/home/' + dir_name + '/'
        container_dataset_dir = container_workdir + os.path.split(self.dataset_dir)[1]

        dockerfile_dir = self.get_dockerfile_dir(dir_name)

        with open(os.path.join(dockerfile_dir, 'Dockerfile'), 'w+') as new_docker:

            if static_results.lang_specific["is_python_2"]:
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
            new_docker.write('WORKDIR ' + container_workdir + '\n')
            new_docker.write('COPY ' + os.path.split(self.dataset_dir)[1] + ' ./' + os.path.split(self.dataset_dir)[1]
                             + ' \n')

            copy("app/language_python/get_dataset_provenance.py", "instance/datasets/" + dir_name)
            copy("app/language_python/ParserPy.py", "instance/datasets/" + dir_name)
            copy("app/language_python/cmd_line.py", "instance/datasets/" + dir_name)
            copy("app/language_python/run_instr.txt", "instance/datasets/" + dir_name)

            new_docker.write('COPY get_dataset_provenance.py ' + container_workdir + '\n')
            new_docker.write('COPY cmd_line.py ' + container_workdir + '\n')
            new_docker.write('COPY ParserPy.py ' + container_workdir + '\n')
            new_docker.write('COPY run_instr.txt ' + container_workdir + '\n')
            new_docker.write('RUN chmod a+rwx -R ' + container_workdir + '\n')
            new_docker.write('WORKDIR ' + container_workdir + '\n')

            for mod in ext_pkgs:
                new_docker.write("RUN " + mod + "\n")
            if static_results.lang_packages:
                for module in static_results.lang_packages:
                    new_docker.write(self.build_docker_package_install(module))
            if python_ver == 2:
                new_docker.write('RUN pip install pathlib\n')

            new_docker.write("RUN pip list > " + container_workdir + "listOfPackages.txt \n")

            new_docker.write("RUN python" + str(python_ver) + " "
                             + container_workdir + "get_dataset_provenance.py" + " " +
                             container_dataset_dir + " " + container_workdir + "\n")

        return os.path.join(app.instance_path, 'datasets', dir_name)

    def create_report(self, current_user_id, name, dir_name, time):
        client = docker.from_env()

        image_name = self.get_container_tag(current_user_id, name)
        container = client.containers.run(image=image_name,
                                          environment=["PASSWORD=pass"],
                                          detach=True, command="tail -f /dev/null")

        container_packages = \
            json.loads(container.exec_run("cat /home/" + dir_name + "/script_info.json")[1].decode())

        # remove the first two lines because they are the "Package | Version" header with line as row separator
        installed_packages = \
            container.exec_run("cat /home/" + dir_name + "/listOfPackages.txt")[
                1].decode().split("\n")[2:]

        python_version = container.exec_run("python -VV")[1].decode().strip("\n").replace("Python ", "")

        system_packages = container.exec_run("apt list --installed")[1].decode().split("\n")

        container.kill()

        system_packages.remove('WARNING: apt does not have a stable CLI interface. Use with caution in scripts.')
        system_packages.remove('Listing...')
        system_packages = [package_tuple.split()[0:2] for package_tuple in system_packages if package_tuple if not '']

        # Split lines output from terminal in list of lists format defined for report
        installed_packages = [package_tuple.split() for package_tuple in installed_packages if package_tuple is not '']

        report = {"Container Information": {}, "Individual Scripts": {}, "Additional Information": {}}

        # Finish out report generation
        report["Container Information"]["Language Packages"] = installed_packages
        report["Container Information"]["System Libraries"] = system_packages
        report["Container Information"]["Language Version"] = python_version
        report["Individual Scripts"] = container_packages
        report["Additional Information"]["Container Name"] = image_name
        report["Additional Information"]["Build Time"] = time
        return report

    @staticmethod
    def build_docker_package_install(module):
        return "RUN pip install " + module + "\n"
