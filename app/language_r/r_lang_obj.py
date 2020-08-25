import requests
import os
import shutil
import cgi
import zipfile
import subprocess
import sys
import json
import docker

from app import app, db

from app.language_interface import language_interface
from app.language_r.Parse import Parser as ProvParser
from app.models import User
from shutil import copy


class r_lang_obj(language_interface):
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
        return 'RUN R -e \"require(\'devtools\');install.packages(\'' +\
            package + '\', repos=\'http://cran.rstudio.com\')\"\n'

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
        doi_direct = destination + '/' + doi_to_directory(doi)

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

    def preprocessing(self, preprocess, dataverse_key='', doi='', data_folder='', run_instr='', user_pkg=''):
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

        ########## RUNNING STATIC ANALYSIS ######################################################################

        subprocess.run(['bash', 'app/language_r/static_analysis.sh',
                        dataset_dir, "app//language_r/static_analysis.R"])

        ########## CHECKING FOR STATIC ANALYSIS ERRORS ##########################################################

        # get list of json files
        jsons = [my_file for my_file in os.listdir(os.path.join(dataset_dir, 'static_analysis'))
                 if my_file.endswith('.json')]

        for json_obj in jsons:
            with open(os.path.join(dataset_dir, 'static_analysis', json_obj)) as json_file:
                data = json.load(json_file)
                if data['errors']:
                    
                    
                    ()
                    return {'current': 100, 'total': 100, 'status': ['Static analysis found errors in script.', data['errors']]}
                

        ########## PARSING STATIC ANALYSIS ######################################################################

        # assemble a set of packages used and get system requirements
        sys_reqs = []
        used_packages = []

        for json_obj in jsons:
            print(json_obj, file=sys.stderr)
            with open(os.path.join(dataset_dir, 'static_analysis', json_obj)) as json_file:
                data = json.load(json_file)
                for p in data['packages']:
                    used_packages.append(p)
                sys_reqs = data['sys_deps']

        print(used_packages, file=sys.stderr)

        return {"dir_name": dir_name, "docker_pkgs": used_packages, "sys_reqs": sys_reqs}


    def build_docker_file(self, dir_name, docker_pkgs, sys_reqs, additional_info, code_btw, run_instr):
        # Variable Information from containR needed for build process:
        # dir_name is the dataset name 
        # docker_pkgs is the packages required
        # docker_file_dir is where the Dockerfile will be written to
        # dataset_dir is a directory in the docker_file_dir named after the dataset.
        # used_packages contains a list of tuples. Each tuple is a package AND its version
        # current_user_id is the user's ID in the database
        # name is what the user chose to be the name of the image, although their user name will be appended to the front

        ext_pkgs = code_btw

        # TODO: equivalent for install_instructions, is there a difference for R/Python?
        special_packages = None
        special_install = None
        install_instructions = ''
        if (install_instructions is not ''):
            special_install = json.loads(install_instructions)
            special_packages = [special_install["packages"][key][0]
                            for key in special_install["packages"].keys()]


        with open('app/language_r/run_instr.txt', 'w+') as out:
            for instr in run_instr:
                out.write(instr + '\n')


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

        with open(os.path.join(docker_file_dir, 'Dockerfile'), 'w') as new_docker:
      #  with open(os.path.join(app.instance_path, 'datasets', dir_name, 'Dockerfile'), 'w+') as new_docker:
            new_docker.write('FROM rocker/tidyverse:3.6.3\n')

            # install system requirements
            sysinstall = "RUN export DEBIAN_FRONTEND=noninteractive; apt-get -y update && apt-get install -y "
            if(len(sys_reqs) != 0):
                for req in sys_reqs:
                    new_docker.write(sysinstall + req + '\n')

            # perform any special installs
            if(special_install):
                if("sys-libs" in special_install.keys()):
                    new_docker.write(sysinstall + ' '.join(special_install["sys-libs"]) + '\n')
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

            # copy the new directory and change permissions
            print(dir_name)
           # new_docker.write('ADD ' + dir_name + ' /home/datasets/' + dir_name + '\n')

            new_docker.write('ADD data_set_content /home/datasets/' + dir_name + '\n')
            new_docker.write('ADD data_set_content ' + docker_file_dir + '\n')

            copy("app/language_r/get_prov_for_doi.sh", "instance/datasets/" + dir_name)
            copy("app/language_r/get_dataset_provenance.R", "instance/datasets/" + dir_name)
           # new_docker.write('COPY get_prov_for_doi.sh \home/datasets/\n')
            new_docker.write('COPY get_prov_for_doi.sh /home/datasets/\n')
           # new_docker.write('COPY get_dataset_provenance.R /home/datasets/\n')
            new_docker.write('COPY get_dataset_provenance.R /home/datasets/\n')
           # new_docker.write('COPY .srcignore /home/rstudio/\n')
            print(docker_home)
            # new_docker.write('RUN chmod a+rwx -R /home/rstudio/' + dir_name + '\n')
            new_docker.write('RUN chmod a+rwx -R /home/datasets/' + dir_name + '\n')
           # new_docker.write("RUN /home/datasets/get_prov_for_doi.sh "
            #                + "/home/datasets/" + dir_name + " /home/datasets/get_dataset_provenance.R\n")
            new_docker.write('RUN /home/datasets/get_prov_for_doi.sh ' + docker_file_dir + ' ' + 'home/datasets/get_dataset_provenance.R' + '\n')                
            new_docker.write("RUN R -e 'write(paste(as.data.frame(installed.packages(),"
                            + "stringsAsFactors = F)$Package, collapse =\"\\n\"), \"./listOfPackages.txt\")'\n")


            # from pyPlace
            # new_docker.write('WORKDIR /home/\n')
            # new_docker.write('RUN git clone https://github.com/gems-uff/noworkflow.git\n')

            # new_docker.write('WORKDIR /home/noworkflow/\n')
            # new_docker.write('RUN git checkout 2.0-alpha\n')
            # new_docker.write('RUN python' + str(python_ver) + ' -m pip install -e capture\n')
            # # new_docker.write('WORKDIR /home/datasets/' + dir_name + '/\n')
            # new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')
            # # new_docker.write('ADD data_set_content /home/datasets/' + dir_name + '\n')
            # new_docker.write('ADD data_set_content ' + docker_file_dir + '\n')
            # copy("app/language_python/get_dataset_provenance.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/Parser_py.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/ReportGenerator.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/cmd_line.py", "instance/datasets/" + dir_name)
            # copy("app/language_python/run_instr.txt", "instance/datasets/" + dir_name)
            # # shutil.copytree("app/language_python/noworkflow","instance/datasets/"+dir_name+"/noworkflow/")
            # # new_docker.write('COPY get_dataset_provenance.py /home/datasets/\n')
            # new_docker.write('COPY get_dataset_provenance.py ' + docker_home + '\n')
            # # new_docker.write('COPY cmd_line.py /home/datasets/\n')
            # # new_docker.write('COPY Parser_py.py /home/datasets/\n')
            # # new_docker.write('COPY ReportGenerator.py /home/datasets/\n')

            # new_docker.write('COPY cmd_line.py ' + docker_home + '\n')
            # new_docker.write('COPY Parser_py.py ' + docker_home + '\n')
            # new_docker.write('COPY ReportGenerator.py ' + docker_home + '\n')
            # new_docker.write('COPY run_instr.txt ' + docker_file_dir + '\n')

            # # new_docker.write('RUN chmod a+rwx -R /home/datasets/' + dir_name + '\n')
            # new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
            # new_docker.write('WORKDIR ' + docker_file_dir + '\n')

            # for mod in ext_pkgs:
            #     new_docker.write("RUN " + mod + "\n")
            # if docker_pkgs:
            #     for module in docker_pkgs:
            #         new_docker.write(self.build_docker_package_install(module))
            # if(python_ver==2):
            #     new_docker.write('RUN pip install pathlib\n')

            # # new_docker.write("RUN pip list > /home/datasets/" + dir_name + "/listOfPackages.txt \n")
            # new_docker.write("RUN pip list > " + docker_file_dir + "listOfPackages.txt \n")

            # # new_docker.write("RUN python3 " \
            # #                     + "/home/datasets/get_dataset_provenance.py" + " /home/datasets/" +
            # #                     dir_name + "/ " + allinstr +"\n")
            # # if(allinstr==""):
            # #    new_docker.write("RUN echo \"\" > run_instr.txt\n")
            # # else:
            # #    new_docker.write("RUN echo -e \"" + allinstr + "\" > run_instr.txt \n")

            # new_docker.write("RUN python" + str(python_ver) + " " \
            #                  + docker_home + "get_dataset_provenance.py" + " " + docker_file_dir + "\n")

        return os.path.join(app.instance_path, 'datasets', dir_name)
    
    def create_report(self, current_user_id, name, dir_name):

        ########## Generate Report About Build Process ##########################################################
        # The report will have various information from the creation of the container
        # for the user
        report = {}
        report["Container Report"] = {}
        report["Individual Scripts"] = {}

        client = docker.from_env()
        current_user_obj = User.query.get(current_user_id)
        # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'

        # There is provenance and other information from the analyses in the container.
        # to get it we need to run the container
        container = client.containers.run(image=repo_name + image_name,
                                        environment=["PASSWORD=" + repo_name + image_name], detach=True)

        # Grab the files from inside the container and the filter to just JSON files
        json_files = container.exec_run("find /home/datasets/" + self.doi_to_directory(
            dir_name) + "/prov_data -name prov.json")[1].decode().split("\n")

        print(json_files)

        # Each json file will represent one execution so we need to grab the information from each.
        # Begin populating the report with information from the analysis and scripts
        container_packages = []
        for json_file in json_files:
            if(json_file == ''):
                continue
            report["Individual Scripts"][json_file] = {}
            prov_from_container = container.exec_run("cat " + json_file)[1].decode()
            prov_from_container = ProvParser(prov_from_container, isFile=False)
            container_packages += get_pkgs_from_prov_json(prov_from_container)
            report["Individual Scripts"][json_file]["Input Files"] = list(
                set(prov_from_container.getInputFiles()["name"].values.tolist()))
            report["Individual Scripts"][json_file]["Output Files"] = list(
                set(prov_from_container.getOutputFiles()["name"].values.tolist()))
            dataNodes = prov_from_container.getDataNodes()
            dataNodes = dataNodes.loc[dataNodes["type"] == "Exception"]
            dataNodes = dataNodes.loc[dataNodes["name"] == "warning.msg"]
            report["Individual Scripts"][json_file]["Warnings"] = dataNodes["value"].values.tolist()
            for json_file in json_files:
                if(json_file == ''):
                    continue
                report["Individual Scripts"][json_file] = {}
            prov_from_container = container.exec_run(
                "cat " + json_file)[1].decode()
            prov_from_container = ProvParser(prov_from_container, isFile=False)
            container_packages += get_pkgs_from_prov_json(prov_from_container)
            report["Individual Scripts"][json_file]["Input Files"] = list(
                set(prov_from_container.getInputFiles()["name"].values.tolist()))
            report["Individual Scripts"][json_file]["Output Files"] = list(
                set(prov_from_container.getOutputFiles()["name"].values.tolist()))
            dataNodes = prov_from_container.getDataNodes()
            dataNodes = dataNodes.loc[dataNodes["type"] == "Exception"]
            dataNodes = dataNodes.loc[dataNodes["name"] == "warning.msg"]
            report["Individual Scripts"][json_file]["Warnings"] = dataNodes["value"].values.tolist()

        # There should be a file written to the container's system that
        # lists the installed packages from when the analyses were run
        installed_packages = container.exec_run("cat listOfPackages.txt")[
        1].decode().split("\n")

        # The run log will show us any errors in execution
        # this will be used after report generation to check for errors when the script was
        # run inside the container
        run_log_path_in_container = "/home/datasets/" + \
            doi_to_directory(doi) + "/prov_data/run_log.csv"
        run_log_from_container = container.exec_run("cat " + run_log_path_in_container)

        # information from the container is no longer needed
        container.kill()

        # Finish out report generation
        report["Container Report"]["Installed Packages"] = installed_packages
        # [list(package_pair) for package_pair in container_packages]
        report["Container Report"]["Packages Called In Analysis"] = container_packages
        report["Container Report"]["System Dependencies Installed"] = sysreqs[0].split(" ")