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


class LanguageInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def script_analysis(self, preprocess=False, data_folder='', run_instr='', user_pkg=''):
        pass

    @abstractmethod
    def build_docker_file(self, dir_name, static_results, code_btw, run_instr):
        pass

    @abstractmethod
    def create_report(self, current_user_id, name, dir_name, time):
        pass

    # Since we modify the passed in name with .lower, and we use the container tag in multiple places, we 
    # will abstract to this method so that anywhere we need the tag we can use this method and have a consistent tag
    @staticmethod
    def get_container_tag(current_user_id, name):
        current_user_obj = User.query.get(current_user_id)
        image_name = current_user_obj.username + '-' + name
        return image_name.lower()

    @staticmethod
    def get_dockerfile_dir(name):
        return os.path.join(app.instance_path, 'datasets', name)

    def build_docker_img(self, docker_file_dir, current_user_id, name):
        # Use low-level api client so we can print output from build process.
        '''
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        generator = client.build(path=docker_file_dir, tag=self.get_container_tag(current_user_id, name))

        for chunk in generator:
            if 'stream' in chunk.decode():
                for line in json.loads(chunk.decode().replace("\r\n", "\n"))["stream"].splitlines():
                    print(line)
        '''

        cli = docker.from_env()
        response = cli.api.build(path=docker_file_dir, tag=self.get_container_tag(current_user_id, name), decode=True)
        for line in response:
            if 'stream' in line.keys() or 'error' in line.keys():
                value = [*line.values()][0].strip()
                if value:
                    print(value)

    def push_docker_img(self, current_user_id, name, report):
        current_user_obj = User.query.get(current_user_id)

        # Not pushing to Docker Hub at the moment.
        # print(self.client.images.push(repository=self.get_container_tag(current_user_id, name)), file=sys.stderr)

        # add dataset to database
        image_tag = self.get_container_tag(current_user_id, name)
        new_dataset = Dataset(url="https://hub.docker.com/r/" + self.get_container_tag(current_user_id, name) + "/",
                              author=current_user_obj,
                              name=name,
                              report=report)
        db.session.add(new_dataset)
        db.session.commit()

        print("Returning")

    def clean_up_datasets(self, name):
        # delete any stored data
        try:
            shutil.rmtree(self.get_dockerfile_dir(name))
        except Exception as e:
            print("Can't delete dataset")
            print(e)
            pass


class StaticAnalysisResults:

    def __init__(self, lang_packages, sys_libs, lang_specific={}):
        self.lang_packages = lang_packages
        self.sys_libs = sys_libs
        self.lang_specific = lang_specific
