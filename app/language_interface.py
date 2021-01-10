import shutil
import sys
from abc import abstractmethod, ABCMeta
from io import BytesIO
from docker import APIClient
import docker
import os
from app import db, app
import json

from app.models import User, Dataset




class language_interface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def script_analysis(self, preprocess, dataverse_key='', doi='', zip_file='', user_pkg=''):
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

    def build_docker_img(self, docker_file_dir, current_user_id, name):

        '''
        self.client.images.build(path=docker_file_dir, tag=repo_name + image_name)
        '''
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        generator = client.build(path=docker_file_dir, tag=self.get_container_tag(current_user_id, name))

        for chunk in generator:
            if 'stream' in chunk.decode():
                for line in json.loads(chunk.decode())["stream"].splitlines():
                    print(line)

        ########## PUSHING IMG ######################################################################
    def push_docker_img(self, dir_name,current_user_id, name, report):
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
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

        self.clean_up_datasets()
        print("Returning")
    def clean_up_datasets(self):
        # delete any stored data
        try:
            del_list = os.listdir(os.path.join(app.instance_path,"datasets"))
            for f in del_list:
                file_path = os.path.join(app.instance_path,"datasets", f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        except:
            pass
