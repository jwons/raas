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


class r_lang(language_interface):
    def clean_up_datasets(self, dataset_directory):
        # delete any stored data
        try:
            shutil.rmtree(os.path.join(app.instance_path,
                                       'r_datasets', dataset_directory))
        except:
            try:
                os.remove(os.path.join(app.instance_path,
                                       'r_datasets', dataset_directory))
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

    def preprocessing(self, preprocess, dataverse_key='', doi='', zip_file='', run_instr='', user_pkg=''):
        # if a set of scripts have been uploaded then its converted to a normal zip file format (ie. zip a folder)
        if zip_file:
            zip_path = os.path.join(app.instance_path, 'py_datasets',
                                    zip_file)  # instance_path -> key path in the server
            # unzip the zipped directory and keep the zip file
            with zipfile.ZipFile(zip_path) as zip_ref:
                dir_name = zip_ref.namelist()[0].strip('/').split('/')[0]
                zip_ref.extractall(os.path.join(
                    app.instance_path, 'py_datasets', dir_name))

            # find name of unzipped directory
            dataset_dir = os.path.join(
                app.instance_path, 'py_datasets', dir_name)
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
                                                                   'There was a problem downloading your data from ' +
                                                                   'Dataverse. Please make sure the DOI is correct.']]]}
        ########## RUNNING STATIC ANALYSIS ##########################################################

        subprocess.run(['bash', 'app/static_analysis.sh',
                        dataset_dir, "app/static_analysis.R"])

    ########## CHECKING FOR STATIC ANALYSIS ERRORS ##########################################################

    # get list of json files
        jsons = [my_file for my_file in os.listdir(os.path.join(dataset_dir, 'static_analysis'))
                 if my_file.endswith('.json')]

        for json_obj in jsons:
            with open(os.path.join(dataset_dir, 'static_analysis', json_obj)) as json_file:
                data = json.load(json_file)
                if data['errors']:
                    clean_up_datasets()
                    return {'current': 100, 'total': 100, 'status': ['Static analysis found errors in script.',
                                                                     data['errors']]}

        ########## PARSING STATIC ANALYSIS ######################################################################

        # assemble a set of packages used and get system requirements
        sysreqs = []
        used_packages = []

        for json_obj in jsons:
            print(json_obj, file=sys.stderr)
            with open(os.path.join(dataset_dir, 'static_analysis', json_obj)) as json_file:
                data = json.load(json_file)
                for p in data['packages']:
                    print(p)
                    used_packages.append(p)
                sysreqs = data['sys_deps']

        print(used_packages, file=sys.stderr)

        return {"dir_name": dir_name, "docker_pkgs": used_packages, "sysreqs": sysreqs}

    def create_report(self, current_user_id, name, dir_name):
        client = docker.from_env()
        current_user_obj = User.query.get(current_user_id)
        # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        container = client.containers.run(image=repo_name + image_name,
                                          environment=[
                                              "PASSWORD=" + repo_name + image_name],
                                          detach=True, command="tail -f /dev/null")
