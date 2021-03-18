import shutil
import sys
import docker
import os
import json

from abc import abstractmethod, ABCMeta
from io import BytesIO
from docker import APIClient

from app import db, app
from app.models import User, Dataset
from celery.contrib import rdb


class language_interface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def script_analysis(self, preprocess = False, data_folder='', run_instr='', user_pkg=''):
        pass

    @abstractmethod
    def build_docker_file(self, dir_name, docker_pkgs, addtional_info, code_btw, run_instr):
        pass

    @abstractmethod
    def create_report(self, current_user_id, name, dir_name, time):
        pass

    # Since we modify the passed in name with .lower, and we use the container tag in multiple places, we 
    # will abstract to this method so that anywhere we need the tag we can use this method and have a consistent tag
    def get_container_tag(self, current_user_id, name):
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        return(repo_name.lower() + image_name.lower())
    
    def get_dockerfile_dir(self, name):
        return(os.path.join(app.instance_path, 'datasets', name))

    def build_docker_img(self, docker_file_dir, current_user_id, name):
        # Use low-level api client so we can print output from build process.
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        generator = client.build(path=docker_file_dir, tag=self.get_container_tag(current_user_id, name))

        for chunk in generator:
            if 'stream' in chunk.decode():
                for line in json.loads(chunk.decode())["stream"].splitlines():
                    print(line)

        ########## PUSHING IMG ######################################################################
    def push_docker_img(self, dir_name, current_user_id, name, report):
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        # Not pushing to Docke Hub at the moment.
        #print(self.client.images.push(repository=repo_name + image_name), file=sys.stderr)

        ########## UPDATING DB ######################################################################

        # add dataset to database
        new_dataset = Dataset(url="https://hub.docker.com/r/" + repo_name + image_name + "/",
                              author=current_user_obj,
                              name=name,
                              report=report)
        db.session.add(new_dataset)
        db.session.commit()

        ########## CLEANING UP ######################################################################

        self.clean_up_datasets(name)
        print("Returning")

    def clean_up_datasets(self, name):
        # delete any stored data
        try:
            shutil.rmtree(self.get_dockerfile_dir(name))
        except Exception as e:
            print("Can't delete dataset")
            print(e)
            pass
