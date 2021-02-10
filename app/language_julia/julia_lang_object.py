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

# print(read_project())
class julia_lang(language_interface):

    def read_manifest(self, loc): 

        file = open(loc+'/'+'Manifest.toml')

        package_list = {}
        # package_vs = set()
        project = file.readlines()
        n = len(project)
        for i in range(n):
            project[i] = project[i].strip()

        # print(project)
        current_package = ""
        for line in project:
            if (line==""):
                continue
            if (line[0:2]=="[["):
                dep = line[2:-2]
                package_list[dep] = '"-1"'
                current_package = dep
            elif (line[:7]=="version"):
                if ('+' in line[11:]):
                    line1 = line[11:].split('+')
                    ver = line1[0]
                    if (ver[0]!='"'):
                        ver = '"'+ver
                    package_list[current_package] = ver+'"'
                else:
                    package_list[current_package] = '"'+line[11:-1]+'"'
            else:
                pass

        return (package_list)

    def read_project(self, loc):

        file = open(loc+'/''Project.toml')

        package_list = {}
        # package_vs = set()
        project = file.readlines()
        n = len(project)
        for i in range(n):
            project[i] = project[i].strip()

        # print(project)
        flag = 0
        for line in project:
            if (line==""):
                continue
            if (line=="[deps]" or line=="[extras]"):
                flag = 1
            elif (line=="[compat]"):
                flag = 2
            elif (line[0]=="[" and line[-1]=="]"):
                flag = 0
            else:
                if (flag==1):
                    line1 = line.split()
                    if (line1[0] not in package_list):
                        package_list[line1[0]] = '"-1"' # -1 stands for default version
                if (flag==2):
                    line1 = line.split()
                    ver = line1[-1]
                    if (ver[0]!='"'):
                        ver = '"'+ver
                    package_list[line1[0]] = ver


        return (package_list)

    def script_analysis(self, preprocess = False, dataverse_key='', doi='', data_folder='', user_pkg=''):

        if data_folder:  
            dir_name = data_folder
            # find name of unzipped directory
            dataset_dir = os.path.join(app.instance_path, 'datasets', dir_name)
            doi = dir_name
        else:
            #TODO support this or remove it #Taken from python_lang_object
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

        manifest = ''
        project = ''
        dir_path = dataset_dir
        for root, dirs, files in os.walk(dir_path): 
            for file1 in files:  
                if file1.endswith('Manifest.toml'): #can maybe use find_file function from helpers in place of this
                    manifest = root
                    break
            else:
                continue
            break

        dir_path = dataset_dir
        for root, dirs, files in os.walk(dir_path): 
            for file1 in files:  
                if file1.endswith('Project.toml'): 
                    project = root
                    break
            else:
                continue
            break

        pkgs1 = {}
        pkgs2 = {}
        if (manifest!=''):
            pkgs1 = self.read_manifest(manifest)
        if (project!=''):
            pkgs2 = self.read_project(project)

        # print (pkgs1)
        # print (pkgs2)
        for i in pkgs1:
            if i not in pkgs2:
                pkgs2[i] = pkgs1[i] #how to resolve conflicts in versions, current strategy - prefer project.toml version
            # else:
                # print ("kaka")
                # print (i)
                # if (semver.compare(pkgs1[i][1:-1],pkgs2[i][1:-1])==-1): #in case actual comparison between packkages is reqd
                #     # print ("lala")
                #     pkgs1[i] = pkgs2[i]
        
        user_pkg_json = {}
        if (user_pkg != ''):
            user_pkg_json = json.loads(user_pkg)["pkg"]

        for p in user_pkg_json:
            pkgs2[p['pkg_name']] = p['pkg_name'] #for Julia, ask user to enter package name and reqd version, command is same. Default package entry is "-1" *with the apostrophes, needed for text analysis
            #this has not been coded yet, make fixes with proper interfacing with routes.py line 130

        return {"dir_name": dir_name, "docker_pkgs": pkgs1}

    def build_docker_file(self, dir_name, docker_pkgs, additional_info, code_btw = None, run_instr=None):
        pkgs = docker_pkgs
        ext_pkgs = code_btw
        julia_ver = 'latest'
        if ('julia' in pkgs and pkgs['julia']!='"-1"'):
            if (pkgs['julia'][1]=='0'):
                julia_ver = pkgs['julia'][1:-1]
            del pkgs['julia']

        if (run_instr!=None):
             with open('app/language_python/run_instr.txt', 'w+') as out:
                for instr in run_instr:
                    out.write(instr + '\n')

        docker_wrk_dir = '/home/datasets/' + dir_name + '/'
        docker_file_dir = '/home/datasets/' + dir_name + '/data_set_content/'
        try:
            os.makedirs(os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content'))
        except:
            pass
        dataset_path = os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content')
        # print (dataset_path)
        with open(os.path.join(app.instance_path, 'datasets', dir_name, 'package_installs.jl'), 'w+') as pkg_file:
            pkg_file.write('using Pkg;\n')
            pkg_file.write('\n')
            for pkg in pkgs:
                if (pkgs[pkg]!='"-1"'):
                    pkg_file.write('Pkg.add(Pkg.PackageSpec(name="'+pkg+'",version='+pkgs[pkg]+'))\n')
                else:
                    pkg_file.write('Pkg.add("'+pkg+'")\n')

        #Installing a specific version of package differs between Julia versions 1.0+ and those before, add custom support later
        with open(os.path.join(app.instance_path, 'datasets', dir_name, 'Dockerfile'), 'w+') as new_docker:

            new_docker.write('FROM julia:'+julia_ver+'\n')

            new_docker.write('WORKDIR /home/\n')
            new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')
            new_docker.write('ADD data_set_content/ ' + docker_file_dir + '\n')

            copy("app/language_julia/run_instr.txt", "instance/datasets/" + dir_name)

            new_docker.write('COPY run_instr.txt ' + docker_file_dir + '\n')

            new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
            new_docker.write('WORKDIR ' + docker_file_dir + '\n')

            if ext_pkgs:
                for mod in ext_pkgs:
                    new_docker.write("RUN " + mod + "\n")

            new_docker.write('ADD package_installs.jl ' + docker_file_dir + '\n')
            new_docker.write('RUN julia ' + docker_file_dir + 'package_installs.jl\n')

            #Missing provenance collection tool for Julia

        return os.path.join(app.instance_path, 'datasets', dir_name)


    def create_report(self, current_user_id, name, dir_name, time):
        report = {"Container Report": {}, "Individual Scripts": {}}
        return report
        #Fix report
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
            container.exec_run("cat /home/datasets/" + dir_name + "/data_set_content/package_installs.jl")[
                1].decode().split("\n")
        container.kill()
        # Finish out report generation
        report["Container Report"]["Installed Packages"] = installed_packages
        report["Individual Scripts"] = container_packages
        return report