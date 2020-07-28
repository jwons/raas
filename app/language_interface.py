import sys
from abc import abstractmethod, ABCMeta
import docker
import os

from app import db

from app.models import User, Dataset




class language_interface(object):
    client = docker.from_env()
    __metaclass__ = ABCMeta

    @abstractmethod
    def preprocessing(self, preprocess, dataverse_key='', doi='', zip_file='', user_pkg=''):
        pass

    @abstractmethod
    def build_docker_file(self, dir_name, docker_pkgs, addtional_info,ode_btw, run_instr):
        pass

    @abstractmethod
    def create_report(self, current_user_id, name, dir_name):
        pass

    @abstractmethod
    def clean_up_datasets(self, dir):
        pass

    def build_docker_img(self, docker_file_dir, current_user_id, name):
        # create docker client instance

        # build a docker image using docker file
        self.client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))
        # name for docker image
        current_user_obj = User.query.get(current_user_id)
        # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        self.client.images.build(path=docker_file_dir, tag=repo_name + image_name)

        ########## PUSHING IMG ######################################################################
    def push_docker_img(self, dir_name,current_user_id, name, report):
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        print(self.client.images.push(repository=repo_name + image_name), file=sys.stderr)

        ########## UPDATING DB ######################################################################

        # add dataset to database
        new_dataset = Dataset(url="https://hub.docker.com/r/" + repo_name + image_name + "/",
                              author=current_user_obj,
                              name=name,
                              report=report)
        db.session.add(new_dataset)
        db.session.commit()

        ########## CLEANING UP ######################################################################

        self.clean_up_datasets(dir_name)
        print("Returning")
