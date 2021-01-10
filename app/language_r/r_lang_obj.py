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
    '''
    def clean_up_datasets():
        # delete any stored data
        for dataset_directory in os.listdir(os.path.join(app.instance_path, 'datasets')):
            try:
                shutil.rmtree(os.path.join(app.instance_path, 'datasets', dataset_directory))
            except:
                try:
                    os.remove(os.path.join(app.instance_path, 'datasets', dataset_directory))
                except:
                    pass
'''
    def doi_to_directory(self, doi):
        """Converts a doi string to a more directory-friendly name
        Parameters
        ----------
        doi : string
          doi

        Returns
        -------
        doi : string
          doi with "/" and ":" replaced by "-" and "--" respectively
        """
        return doi.replace("/", "-").replace(":", "--")

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
        # return 'RUN R -e \"require(\'devtools\');install_version(\'' +\
        #		package + '\', version=\'' + version + '\', repos=\'http://cran.rstudio.com\')\"\n'


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


    def download_dataset(self, doi, destination, dataverse_key,
                         api_url="https://dataverse.harvard.edu/api/"):
        """Download doi to the destination directory
        Parameters
         ----------
        doi : string
          doi of the dataset to be downloaded
        destination : string
                  path to the destination in which to store the downloaded directory
        dataverse_key : string
                    dataverse api key to use for completing the download
        api_url : string
              URL of the dataverse API to download the dataset from
        Returns
        -------
        bool
        whether the dataset was successfully downloaded to the destination
        """
        api_url = api_url.strip("/")
        # make a new directory to store the dataset
        # (if one doesn't exist)
        if not os.path.exists(destination):
            os.makedirs(destination)

        try:
            # query the dataverse API for all the files in a dataverse
            files = requests.get(api_url + "/datasets/:persistentId",
                                 params={"persistentId": doi}) \
                .json()['data']['latestVersion']['files']

        except:
            return False

        # convert DOI into a friendly directory name by replacing slashes and colons
        doi_direct = destination + '/' + self.doi_to_directory(doi)

        # make a new directory to store the dataset
        if not os.path.exists(doi_direct):
            os.makedirs(doi_direct)
        # for each file result
        for file in files:
            try:
                # parse the filename and fileid
                # filename = file['dataFile']['filename']
                fileid = file['dataFile']['id']
                contentType = file['dataFile']['contentType']

                if (contentType == 'type/x-r-syntax'):
                    # query the API for the file contents
                    response = requests.get(
                        api_url + "/access/datafile/" + str(fileid))
                else:
                    # query the API for the file contents
                    response = requests.get(api_url + "/access/datafile/" + str(fileid),
                                            params={"format": "original", "key": dataverse_key})

                value, params = cgi.parse_header(
                    response.headers['Content-disposition'])
                if 'filename*' in params:
                    filename = params['filename*'].split("'")[-1]
                else:
                    filename = params['filename']

                # write the response to correctly-named file in the dataset directory
                with open(doi_direct + "/" + filename, 'wb') as handle:
                    handle.write(response.content)
            except:
                return False
        return True

    def script_analysis(self, preprocess, dataverse_key='', doi='', data_folder='', run_instr='', user_pkg=''):
        # This variable controls whether or not the container is built despite the existence
        # of errors detected in the script
        eval = True
        if data_folder:  
            # if a set of scripts have been uploaded then its converted to a normal zip file format (ie. zip a folder)
            # zip_path = os.path.join(app.instance_path, 'datasets',
            #                         zip_file)  # instance_path -> key path in the server
            # unzip the zipped directory and keep the zip file
            # with open(zip_path) as zip_ref:
            dir_name = data_folder
            # zip_ref.extractall(os.path.join(app.instance_path, 'datasets', dir_name))

            # find name of unzipped directory
            dataset_dir = os.path.join(app.instance_path, 'datasets', dir_name)
            unzip_name = os.path.join(dataset_dir, "data_set_content", os.listdir(os.path.join(dataset_dir, "data_set_content"))[0])
            doi = dir_name

        else:
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
        # # if a set of scripts have been uploaded then its converted to a normal zip file format (ie. zip a folder)
        # if zip_file:
        #     zip_path = os.path.join(app.instance_path, 'py_datasets',
        #                             zip_file)  # instance_path -> key path in the server
        #     # unzip the zipped directory and keep the zip file
        #     with zipfile.ZipFile(zip_path) as zip_ref:
        #         dir_name = zip_ref.namelist()[0].strip('/').split('/')[0]
        #         zip_ref.extractall(os.path.join(
        #             app.instance_path, 'py_datasets', dir_name))

        #     # find name of unzipped directory
        #     dataset_dir = os.path.join(
        #         app.instance_path, 'py_datasets', dir_name)
        #     doi = dir_name
        # else:
        #     dataset_dir = os.path.join(app.instance_path, 'py_datasets', self.doi_to_directory(doi),
        #                                self.doi_to_directory(doi))
        #     success = self.download_dataset(doi=doi, dataverse_key=dataverse_key,
        #                                     destination=os.path.join(app.instance_path, 'py_datasets',
        #                                                              self.doi_to_directory(doi)))
        #     dir_name = self.self.doi_to_directory(doi)
        #     if not success:
        #         self.clean_up_datasets(self.self.doi_to_directory(doi))
        #         return {'current': 100, 'total': 100, 'status': ['Data download error.',
        #                                                          [['Download error',
        #                                                            'There was a problem downloading your data from ' +
        #                                                            'Dataverse. Please make sure the DOI is correct.']]]}

        ########## Preprocessing ######################################################################
        src_ignore = []
        if(preprocess):
            r_files = [y for x in os.walk(os.path.join(unzip_name)) for y in glob(os.path.join(x[0], '*.R'))]

            if not os.path.exists(os.path.join(unzip_name, "__original_scripts__")):
                os.makedirs(os.path.join(unzip_name, "__original_scripts__"))
        
            for r_file in r_files:
                r_file = os.path.split(r_file)
                all_preproc(r_file[1], r_file[0])
                copy(os.path.join(r_file[0], r_file[1]), os.path.join(unzip_name, "__original_scripts__", r_file[1]))
                src_ignore.append(os.path.join("/__original_scripts__", r_file[1]))
                os.remove(os.path.join(r_file[0], r_file[1]))
        
            pre_files = [y for x in os.walk(os.path.join(unzip_name)) for y in glob(os.path.join(x[0], '*__preproc__.R'))]
            
            for pre_file in pre_files:
                pre_file = os.path.split(pre_file)
                filename = re.split('\__preproc__.[rR]$', pre_file[1])[0]
                os.rename(os.path.join(pre_file[0], pre_file[1]), os.path.join(pre_file[0], filename + ".R"))
        ########## RUNNING STATIC ANALYSIS ######################################################################
        subprocess.run(['bash', 'app/language_r/static_analysis.sh',
                        dataset_dir, "app/language_r/static_analysis.R"])


        ########## CHECKING FOR STATIC ANALYSIS ERRORS ##########################################################
        # get list of json files
        #TODO There should only be one of these....
        jsons = [my_file for my_file in os.listdir(os.path.join(dataset_dir, 'static_analysis'))
                 if my_file.endswith('.json')]    
                
        ########## PARSING STATIC ANALYSIS ######################################################################

        # assemble a set of packages used and get system requirements
        sys_reqs = []
        used_packages = []

        for json_obj in jsons:
            print(json_obj, file=sys.stderr)
            with open(os.path.join(dataset_dir, 'static_analysis', json_obj)) as json_file:
                data = json.load(json_file)
                if(not eval):
                    if data['errors']:
                        return {'current': 100, 'total': 100, 'status': ['Static analysis found errors in script.', data['errors']]}
                for p in data['packages']:
                    used_packages.append(p)
                sys_reqs = data['sys_deps']
        sys_reqs.append("libjpeg-dev")
        print(used_packages, file=sys.stderr)

        return {"dir_name": dir_name, "docker_pkgs": used_packages, "sys_reqs": sys_reqs, "src_ignore" : src_ignore}


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

        docker_wrk_dir = '/home/datasets/' + dir_name + '/'
        docker_file_dir = '/home/datasets/' + dir_name + '/data_set_content/'
        docker_home = '/home/datasets/' + dir_name + '/'
       # docker_file_dir is where Dockerfile will be written to
       # docker_file_dir = os.path.join(app.instance_path, 'datasets', dir_name)

        try:
            #os.makedirs(docker_file_dir)
            os.makedirs(os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content'))
        except:
            print('pass')
            pass

        docker_file_dir = os.path.join(app.instance_path, 'datasets', dir_name)
            
        try:
            os.makedirs(docker_file_dir)
        except:
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
      #  with open(os.path.join(app.instance_path, 'datasets', dir_name, 'Dockerfile'), 'w+') as new_docker:
            new_docker.write('FROM rocker/tidyverse:3.6.3\n')

            # install system requirements
            sysinstall = "RUN export DEBIAN_FRONTEND=noninteractive; apt-get -y update && apt-get install -y "
            if(len(sys_reqs) != 0):
                new_docker.write(sysinstall + ' '.join(sys_reqs) + '\n')

            # perform any pre-specified installs
            if(special_install):
                if("sys-libs" in special_install.keys()):
                    new_docker.write(sysinstall + ' '.join(special_install["sys-libs"]) + '\n')
            '''
            if special_packages:
                for key in special_install["packages"].keys():
                    instruction = 'RUN R -e \"require(\'devtools\');' + \
                        special_install["packages"][key][1] + '"\n'
                    new_docker.write(instruction)

            # install packages
            docker_packages = list(set(docker_pkgs))
            if docker_packages:
                for package in docker_packages:
                    if(special_packages and (package not in special_packages)):
                        new_docker.write(self.build_docker_package_install_no_version(package))
                    if(special_packages is None):
                        new_docker.write(self.build_docker_package_install_no_version(package))
            '''
            

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
            new_docker.write('RUN chmod a+rwx -R /home/rstudio/\n')

            # Execute analysis and collect provenance
            new_docker.write('RUN /home/rstudio/datasets/get_prov_for_doi.sh /home/rstudio/datasets/' + dir_name +\
                '/' + os.listdir(os.path.join(app.instance_path, 'datasets', dir_name, "data_set_content"))[0] + \
                    ' ' + '/home/rstudio/datasets/get_dataset_provenance.R' + '\n')   

            # Collect installed package information for the report              
            new_docker.write("RUN Rscript /home/rstudio/datasets/create_report.R")
        return os.path.join(app.instance_path, 'datasets', dir_name)
    
    def create_report(self, current_user_id, name, dir_name):

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
        report["Container Name"] = self.get_container_tag(current_user_id, name)
        
        # information from the container is no longer needed
        container.kill()

        return(report)
