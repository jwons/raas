import sys
from abc import abstractmethod, ABCMeta
import docker
import os

from app import db, celery

from app.models import User, Dataset




class language_interface(object):
    __metaclass__ = ABCMeta  # 指定这是一个抽象类

    @abstractmethod
    def preprocessing(self, preprocess, dataverse_key='', doi='', zip_file='', run_instr='', user_pkg=''):
        pass

    @abstractmethod  # 抽象方法
    def build_docker_file(self, dir_name, docker_pkgs, addtional_info):
        pass

    @abstractmethod  # 抽象方法
    def create_report(self, current_user_id, name, dir_name):
        pass

    @abstractmethod  # 抽象方法
    def clean_up_datasets(self, dir):
        pass

    def build_docker_img(self, docker_file_dir, current_user_id, name):
        # create docker client instance
        client = docker.from_env()
        # build a docker image using docker file
        client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))
        # name for docker image
        current_user_obj = User.query.get(current_user_id)
        # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        client.images.build(path=docker_file_dir, tag=repo_name + image_name)

        ########## PUSHING IMG ######################################################################
    def push_docker_img(self, dir_name,current_user_id, name, report):
        client = docker.from_env()
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        repo_name = os.environ.get('DOCKER_REPO') + '/'
        print(client.images.push(repository=repo_name + image_name), file=sys.stderr)

        ########## UPDATING DB ######################################################################

        # add dataset to database
        new_dataset = Dataset(url="https://hub.docker.com/raas/" + repo_name + image_name + "/",
                              author=current_user_obj,
                              name=name,
                              report=report)
        db.session.add(new_dataset)
        db.session.commit()

        ########## CLEANING UP ######################################################################

        self.clean_up_datasets(dir_name)
        print("Returning")
