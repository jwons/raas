import requests
import os
import shutil
import cgi
import zipfile
import subprocess
import sys
import json
import docker
import re

from glob import glob
from app import app, db
from app.language_interface import language_interface
from app.Parse import Parser as ProvParser
from app.models import User
from app.preproc_helpers import all_preproc
from shutil import copy

#Debugging
from celery.contrib import rdb


class r_lang(language_interface):

    def build_docker_package_install(self, package, version):
        """Outputs formatted dockerfile command to install a specific version
        of an R package into a docker image
        Parameters
        ----------
        package : string
                        Name of the R package to be installed
        version : string
                        Version number of the desired package
        """
        return 'RUN R -e \"require(\'devtools\');  {install_version(\'' + package + \
            '\', version=\'' + version + '\', repos=\'http://cran.rstudio.com\')}"\n'
       

    def build_docker_package_install_no_version(self, package):
        """Outputs formatted dockerfile command to install a specific version
        of an R package into a docker image
        Parameters
        ----------
        package : string
        """
        return 'if(!(\'' + package + '\'' \
		'%in% rownames(installed.packages()))){install.packages(\'' + package + '\')}\n' + \
        'if(!(\'' + package + '\'' \
		'%in% rownames(installed.packages()))){BiocManager::install(\'' + package + '\', update = F)}\n'

        '''
        return 'install.packages(\'' + \
            package + '\', repos=\'http://cran.rstudio.com\') \n'
        '''

    def script_analysis(self, preprocess, dataverse_key='', data_folder='', run_instr='', user_pkg=''):
        # This variable controls whether or not the container is built despite the existence
        # of errors detected in the script
        eval = True
  
        dir_name = data_folder
        # find name of unzipped directory
        dataset_dir = os.path.join(app.instance_path, 'datasets', dir_name)
        unzip_name = os.path.join(dataset_dir, "data_set_content", os.listdir(os.path.join(dataset_dir, "data_set_content"))[0])

        ########## Preprocessing ######################################################################
        src_ignore = []
        if(preprocess):
            r_files = [y for x in os.walk(os.path.join(unzip_name)) for y in glob(os.path.join(x[0], '*.R'))]
            sourced_files = []
            if not os.path.exists(os.path.join(unzip_name, "__original_scripts__")):
                os.makedirs(os.path.join(unzip_name, "__original_scripts__"))
            for r_file in r_files:
                r_file = os.path.split(r_file)
                sourced_files = all_preproc(r_file[1], r_file[0])
                copy(os.path.join(r_file[0], r_file[1]), os.path.join(unzip_name, "__original_scripts__", r_file[1]))
                src_ignore.append(os.path.join("/__original_scripts__", r_file[1]))
                src_ignore = src_ignore + sourced_files
                os.remove(os.path.join(r_file[0], r_file[1]))
        
            pre_files = [y for x in os.walk(os.path.join(unzip_name)) for y in glob(os.path.join(x[0], '*__preproc__.R'))]
            
            for pre_file in pre_files:
                pre_file = os.path.split(pre_file)
                filename = re.split('\__preproc__.[rR]$', pre_file[1])[0]
                os.rename(os.path.join(pre_file[0], pre_file[1]), os.path.join(pre_file[0], filename + ".R"))
                
        ########## RUNNING STATIC ANALYSIS ######################################################################
        subprocess.run(['bash', 'app/language_r/static_analysis.sh',
                        dataset_dir, "app/language_r/static_analysis.R"])
                
        ########## PARSING STATIC ANALYSIS ######################################################################

        # assemble a set of packages used and get system requirements
        sys_reqs = []
        used_packages = []
        with open(os.path.join(dataset_dir, 'static_analysis', "static_analysis.json")) as json_file:
            data = json.load(json_file)
            if(not eval):
                if data['errors']:
                    return {'current': 100, 'total': 100, 'status': ['Static analysis found errors in script.', data['errors']]}
            used_packages = data['packages']
            sys_reqs = data['sys_deps']
            
        sys_reqs.append("libjpeg-dev")

        return {"dir_name": dir_name, "docker_pkgs": used_packages, "sys_reqs": sys_reqs, "src_ignore" : list(set(src_ignore))}


    def build_docker_file(self, dir_name, docker_pkgs, additional_info, code_btw, run_instr):
        ext_pkgs = code_btw
        sys_reqs = additional_info["sys_reqs"]
        src_ignore = additional_info["src_ignore"]

        # TODO: equivalent for install_instructions, is there a difference for R/Python?
        special_packages = None
        special_install = None
        install_instructions = ''
        if (install_instructions is not ''):
            special_install = json.loads(install_instructions)
            special_packages = [special_install["packages"][key][0]
                            for key in special_install["packages"].keys()]


        # We need a different way of adding run instuctions that doesn't modify a folder
        # available to the whole program. 
        '''
        with open('app/language_r/run_instr.txt', 'w+') as out:
            for instr in run_instr:
                out.write(instr + '\n')
        '''

        try:
            os.makedirs(os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content'))
        except Exception as e:
            print('pass')
            pass

        docker_file_dir = os.path.join(app.instance_path, 'datasets', dir_name)
            
        try:
            os.makedirs(docker_file_dir)
        except Exception as e:
            pass
        
        if(len(src_ignore) > 0):
            with open(os.path.join(docker_file_dir, '.srcignore'), 'w') as src_ignore_file:
                for line in src_ignore:
                    src_ignore_file.write(line + "\n")
                src_ignore_file.write('\n')
        
        with open(os.path.join(docker_file_dir, 'install__packages.R'), 'w') as install_packs:
            install_packs.write('require(\'devtools\')\n')
            install_packs.write('require(\'BiocManager\')\n')
            # perform any pre-specified installs
            if special_packages:
                for key in special_install["packages"].keys():
                    instruction = special_install["packages"][key][1] + '"\n'
                    install_packs.write(instruction)

            # install packages
            docker_packages = list(set(docker_pkgs))
            if docker_packages:
                for package in docker_packages:
                    if(special_packages and (package not in special_packages)):
                        install_packs.write(self.build_docker_package_install_no_version(package))
                    if(special_packages is None):
                        install_packs.write(self.build_docker_package_install_no_version(package))


        with open(os.path.join(docker_file_dir, 'Dockerfile'), 'w') as new_docker:
            new_docker.write('FROM rocker/tidyverse:3.6.3\n')

            # install system requirements
            sysinstall = "RUN export DEBIAN_FRONTEND=noninteractive; apt-get -y update && apt-get install -y "
            if(len(sys_reqs) != 0):
                new_docker.write(sysinstall + ' '.join(sys_reqs) + '\n')

            # perform any pre-specified installs
            if(special_install):
                if("sys-libs" in special_install.keys()):
                    new_docker.write(sysinstall + ' '.join(special_install["sys-libs"]) + '\n')

            # copy the new directory and change permissions
            print(dir_name)

            # Install libraries
            new_docker.write('COPY install__packages.R /home/rstudio/\n')
            new_docker.write('RUN Rscript /home/rstudio/install__packages.R\n')
            
            #Add the dataset to the container
            new_docker.write('ADD data_set_content /home/rstudio/datasets/' + dir_name + '\n')

            # These scripts will execute the analyses and collect provenance. Copy them to the 
            # Dockerfile directory first since files copied to the image cannot be outside of it
            copy("app/language_r/get_prov_for_doi.sh", "instance/datasets/" + dir_name)
            copy("app/language_r/get_dataset_provenance.R", "instance/datasets/" + dir_name)
            copy("app/language_r/create_report.R", "instance/datasets/" + dir_name)
            new_docker.write('COPY get_prov_for_doi.sh /home/rstudio/datasets/\n')
            new_docker.write('COPY get_dataset_provenance.R /home/rstudio/datasets/\n')
            new_docker.write('COPY create_report.R /home/rstudio/datasets/\n')
            if(len(src_ignore) > 0):
                new_docker.write('COPY .srcignore /home/rstudio/\n')

            # Add permissions or the scripts will fail 
            new_docker.write('RUN chown -R  rstudio:rstudio /home/rstudio/\n')

            # Execute analysis and collect provenance
            new_docker.write('RUN /home/rstudio/datasets/get_prov_for_doi.sh /home/rstudio/datasets/' + dir_name +\
                '/' + os.listdir(os.path.join(app.instance_path, 'datasets', dir_name, "data_set_content"))[0] + \
                    ' ' + '/home/rstudio/datasets/get_dataset_provenance.R' + '\n')   

            # Collect installed package information for the report              
            new_docker.write("RUN Rscript /home/rstudio/datasets/create_report.R")
        return os.path.join(app.instance_path, 'datasets', dir_name)
    
    def create_report(self, current_user_id, name, dir_name, time):

        ########## Generate Report About Build Process ##########################################################
        # The report will have various information from the creation of the container
        # for the user

        # Reconstruct image name from user info
        client = docker.from_env()

        # to get report we need to run the container
        container = client.containers.run(image=self.get_container_tag(current_user_id, name),
                                        environment=["PASSWORD=pass"], detach=True)

        # Grab the files from inside the container and the filter to just JSON files
        report = json.loads(container.exec_run("cat /home/rstudio/report.json")[1].decode())
        report["Additional Information"] = {}
        report["Additional Information"]["Container Name"] = self.get_container_tag(current_user_id, name)
        report["Additional Information"]["Build Time"] = time

        # information from the container is no longer needed
        container.kill()

        return(report)
