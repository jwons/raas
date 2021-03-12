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


class matlab_lang(language_interface):
    #
    # def temp_name(self, path):
    #     p_obj = Path(path)
    #     filename = p_obj.stem
    #     temp_filename = filename + '_temp.py'
    #     par = p_obj.parent
    #     temp_path = os.path.join(par, temp_filename)
    #     return temp_path
    #
    def preprocessing(self, preprocess, dataverse_key='', doi='', data_folder='', user_pkg=''):

        return {"dir_name": data_folder, "docker_pkgs": {}}

    def create_report(self, current_user_id, name, dir_name):
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
            # Using an image with  matlab_runtime installed, should be moved to
            # RAAS docker account in the future
            new_docker.write('FROM albert5544/matlab_runtime\n')

            new_docker.write('WORKDIR /home/\n')
            new_docker.write('RUN git clone -b ml-sqlite https://github.com/DataONEorg/matlab-dataone.git\n')

            new_docker.write('WORKDIR /home/matlab-dataone/\n')
            new_docker.write('RUN matlab -nodesktoop -nosplash t-r  install_matlab_dataone\n')
            # new_docker.write('WORKDIR /home/datasets/' + dir_name + '/\n')
            new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')
            # new_docker.write('ADD data_set_content /home/datasets/' + dir_name + '\n')
            new_docker.write('ADD data_set_content ' + docker_file_dir + '\n')
            copy("app/language_matlab/get_dataset_provenance", "instance/datasets/" + dir_name)
            # copy("app/language_python/Parser_py.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/ReportGenerator.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/cmd_line.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/run_instr.txt", "instance/datasets/" + dir_name)
            # shutil.copytree("app/language_python/noworkflow","instance/datasets/"+dir_name+"/noworkflow/")
            #new_docker.write('COPY get_dataset_provenance /home/datasets/\n')
            new_docker.write('COPY get_dataset_provenance ' + docker_home + '\n')
            new_docker.write('RUN ./get_dataset_provenance /usr/local/MATLAB/MATLAB_Runtime/v98/')
            # new_docker.write('COPY cmd_line.py /home/datasets/\n')
            # new_docker.write('COPY Parser_py.py /home/datasets/\n')
            # new_docker.write('COPY ReportGenerator.py /home/datasets/\n')

            # new_docker.write('COPY cmd_line.py ' + docker_home + '\n')
            # new_docker.write('COPY Parser_py.py ' + docker_home + '\n')
            # new_docker.write('COPY ReportGenerator.py ' + docker_home + '\n')
            # new_docker.write('COPY run_instr.txt ' + docker_file_dir + '\n')

            # new_docker.write('RUN chmod a+rwx -R /home/datasets/' + dir_name + '\n')
            # new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
            # new_docker.write('WORKDIR ' + docker_file_dir + '\n')

            # new_docker.write("RUN pip list > /home/datasets/" + dir_name + "/listOfPackages.txt \n")
            # new_docker.write("RUN pip list > " + docker_file_dir + "listOfPackages.txt \n")

            # new_docker.write("RUN ./home/datasets/get_dataset_provenance" + " /home/datasets/" +
            #                   dir_name + "/ " + allinstr +"\n")
            # if(allinstr==""):
            #    new_docker.write("RUN echo \"\" > run_instr.txt\n")
            # else:
            #    new_docker.write("RUN echo -e \"" + allinstr + "\" > run_instr.txt \n")


        return os.path.join(app.instance_path, 'datasets', dir_name)
