from pathlib import Path

from app.files_list import generate_multimap, generate_modules, generate_set
from app.language_python.py2or3 import python2or3
from app.pathpreprocess import path_preprocess
from app.ast_test import get_imports
from app.language_python.pylint_parse import pylint_parser

import requests
import json

import os
import shutil

import zipfile
import docker
import cgi
from app.models import User
from app import app

from shutil import copy

from app.language_interface import language_interface


class py_place(language_interface):
    def clean_up_datasets(self, dataset_directory):
        # delete any stored data
        try:
            shutil.rmtree(os.path.join(app.instance_path, 'py_datasets', dataset_directory))
        except:
            try:
                os.remove(os.path.join(app.instance_path, 'py_datasets', dataset_directory))
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

    def download_dataset(doi, destination, dataverse_key, api_url="https://dataverse.harvard.edu/api/"):
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

                # query the API for the file contents
                # In Dataverse, tabular data are converted to non-propietary formats for
                # archival purposes. These files we will need to specifically request for
                # the original file because the scripts will break otherwise. If the files
                # have metadata denoting their original file size, they *should* be a file
                # that was changed so we would need to grab the original
                if "originalFileSize" in file["dataFile"]:
                    response = requests.get(api_url + "/access/datafile/" + str(fileid),
                                            params={"format": "original", "key": dataverse_key})
                else:
                    response = requests.get(api_url + "/access/datafile/" + str(fileid))

                value, params = cgi.parse_header(response.headers['Content-disposition'])
                if 'filename*' in params:
                    filename = params['filename*'].split("'")[-1]
                else:
                    filename = params['filename']

                # write the response to correctly-named file in the dataset directory
                with open(doi_direct + "/" + filename, 'wb') as handle:
                    handle.write(response.content)
            except:
                return False
        return files

    def preprocessing(self, preprocess, dataverse_key='', doi='', zip_file='', user_pkg=''):
        if zip_file:  # if a set of scripts have been uploaded then its converted to a normal zip file format (ie. zip a folder)
            # zip_path = os.path.join(app.instance_path, 'py_datasets',
            #                         zip_file)  # instance_path -> key path in the server
            # unzip the zipped directory and keep the zip file
            # with open(zip_path) as zip_ref:
            dir_name = zip_file
            # zip_ref.extractall(os.path.join(app.instance_path, 'py_datasets', dir_name))

            # find name of unzipped directory
            dataset_dir = os.path.join(app.instance_path, 'py_datasets', dir_name)
            doi = dir_name
        else:
            dataset_dir = os.path.join(app.instance_path, 'py_datasets', self.doi_to_directory(doi),
                                       self.doi_to_directory(doi))
            success = self.download_dataset(doi=doi, dataverse_key=dataverse_key,
                                            destination=os.path.join(app.instance_path, 'py_datasets',
                                                                     self.doi_to_directory(doi)))
            dir_name = self.self.doi_to_directory(doi)
            if not success:
                self.clean_up_datasets(self.self.doi_to_directory(doi))
                return {'current': 100, 'total': 100, 'status': ['Data download error.',
                                                                 [['Download error',
                                                                   'There was a problem downloading your data from ' + \
                                                                   'Dataverse. Please make sure the DOI is correct.']]]}

        pyfiles = generate_set(dataset_dir)
        py2 = False
        if preprocess:
            try:

                # iterate through list of all python files to figure out if its python2 or python3
                hash = generate_multimap(dataset_dir + "/data_set_content")
                for file in pyfiles:
                    path_preprocess(file, dataset_dir + "/data_set_content", hash)
            except:
                pass

        user_defined_modules = generate_modules(dataset_dir + "/data_set_content")

        unknown_pkgs = set()
        docker_pkgs = set()
        pkgs_to_ask_user = set()

        for file in pyfiles:
            py3 = python2or3(file)
            # Commented out by Albert, but why, maybe buggy
            try:
                (unknown, dockerpkg) = get_imports(file, dir_name, user_defined_modules)
            except Exception as e:
                p_ob = Path(file)
                strp = ''
                for i in e.args:
                    strp = strp + str(i) + ' '
                self.clean_up_datasets(dir_name)
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [[
                                                                     'Error in AST generation of ' + p_ob.name,
                                                                     strp]]]}

            unknown_pkgs = unknown_pkgs.union(unknown)
            docker_pkgs = docker_pkgs.union(dockerpkg)
            if (py3 == False):
                py2 = True

        user_pkg_json = {}
        if (user_pkg != ''):
            user_pkg_json = json.loads(user_pkg)["pkg"]

        pkg_dict = {}
        for p in user_pkg_json:
            pkg_dict[p['pkg_name']] = p['PypI_name']

        for pkgs in unknown_pkgs:
            if not (pkgs in pkg_dict):
                pkgs_to_ask_user.add(pkgs)

        if (len(pkgs_to_ask_user) != 0):
            missing_modules = ''
            for pkg in pkgs_to_ask_user:
                missing_modules += pkg + ','
            self.clean_up_datasets(dir_name)
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
                self.clean_up_datasets(dir_name)
                return {'current': 100, 'total': 100, 'status': ['Error in code.',
                                                                 [[
                                                                     'Error identified by static analysis of ' + p_obj.name,
                                                                     err_mesg]]]}
        return {"dir_name": dir_name, "docker_pkgs": docker_pkgs, "is_python_2": py2}

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
        container.exec_run("cat /home/py_datasets/" + dir_name + "/data_set_content/script_info.json")[1].decode()
        installed_packages = \
        container.exec_run("cat /home/py_datasets/" + dir_name + "/data_set_content/listOfPackages.txt")[
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
        allinstr = ""
        ext_pkgs = code_btw
        for instr in run_instr:
            allinstr = allinstr + instr + r"\n"

        docker_wrk_dir = '/home/py_datasets/' + dir_name + '/'
        docker_file_dir = '/home/py_datasets/' + dir_name + '/data_set_content/'
        docker_home = '/home/py_datasets/' + dir_name + '/'
        try:
            os.makedirs(os.path.join(app.instance_path, 'py_datasets', dir_name, 'data_set_content'))
        except:
            pass
        with open(os.path.join(app.instance_path, 'py_datasets', dir_name, 'Dockerfile'), 'w+') as new_docker:

            if additional_info["is_python_2"]:
                new_docker.write('FROM python:2\n')
            else:
                new_docker.write('FROM python:3\n')

            # Some changes due to nature of path preprocessing by AkashS

            # new_docker.write('WORKDIR /home/py_datasets/' + dir_name + '/\n')
            new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')
            # new_docker.write('ADD data_set_content /home/py_datasets/' + dir_name + '\n')
            new_docker.write('ADD data_set_content ' + docker_wrk_dir + '\n')
            copy("app/language_python/get_dataset_provenance.py", "instance/py_datasets/" + dir_name)
            copy("app/language_python/Parser_py.py", "instance/py_datasets/" + dir_name)
            copy("app/language_python/ReportGenerator.py", "instance/py_datasets/" + dir_name)
            copy("app/language_python/cmd_line.py", "instance/py_datasets/" + dir_name)
            # new_docker.write('COPY get_dataset_provenance.py /home/py_datasets/\n')
            new_docker.write('COPY get_dataset_provenance.py ' + docker_home + '\n')
            # new_docker.write('COPY cmd_line.py /home/py_datasets/\n')
            # new_docker.write('COPY Parser_py.py /home/py_datasets/\n')
            # new_docker.write('COPY ReportGenerator.py /home/py_datasets/\n')

            new_docker.write('COPY cmd_line.py ' + docker_home + '\n')
            new_docker.write('COPY Parser_py.py ' + docker_home + '\n')
            new_docker.write('COPY ReportGenerator.py ' + docker_home + '\n')

            # new_docker.write('RUN chmod a+rwx -R /home/py_datasets/' + dir_name + '\n')
            new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
            new_docker.write('WORKDIR /home/\n')
            new_docker.write('RUN git clone https://github.com/gems-uff/noworkflow.git\n')
            new_docker.write('WORKDIR /home/noworkflow/\n')
            new_docker.write('RUN git checkout 2.0-alpha\n')
            new_docker.write('RUN python3 -m pip install -e capture\n')
            # new_docker.write('WORKDIR /home/py_datasets/' + dir_name + '/\n')
            new_docker.write('WORKDIR ' + docker_file_dir + '\n')

            for mod in ext_pkgs:
                new_docker.write("RUN " + mod + "\n")
            if docker_pkgs:
                for module in docker_pkgs:
                    new_docker.write(self.build_docker_package_install(module))

            # new_docker.write("RUN pip list > /home/py_datasets/" + dir_name + "/listOfPackages.txt \n")
            new_docker.write("RUN pip list > " + docker_file_dir + "listOfPackages.txt \n")

            # new_docker.write("RUN python3 " \
            #                     + "/home/py_datasets/get_dataset_provenance.py" + " /home/py_datasets/" +
            #                     dir_name + "/ " + allinstr +"\n")
            new_docker.write("RUN echo -e \"" + allinstr + "\" >> run_instr.txt \n")
            new_docker.write("RUN python3 " \
                             + docker_home + "get_dataset_provenance.py" + " " + docker_wrk_dir + "\n")

        return os.path.join(app.instance_path,'py_datasets', dir_name)
