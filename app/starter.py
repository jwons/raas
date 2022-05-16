import os

from app import celery
from app import app
from app.languageinterface import StaticAnalysisResults
from app.language_python.python_lang_obj import PyLang
from app.language_r.r_lang_obj import RLang
from timeit import default_timer as timer
from zipfile import ZipFile

# Debugging
from celery.contrib import rdb


# Used for eval
# @celery.task(bind=True, time_limit=3660, soft_time_limit = 3600)

@celery.task(bind=True, time_limit=18060, soft_time_limit=18000)
def start_raas(self, language, current_user_id, name, preprocess, data_folder, zip_filename,
               run_instr='', user_pkgs='', sample_output=None, code_btw=[],
               prov=None, upload=True, make_report=True):
    if language == "Python":
        language_obj = PyLang()
    elif language == "R":
        language_obj = RLang()
    else:
        return {'current': 100, 'total': 100, 'status': ['Error in language.',
                                                         [[language + " is not supported"]]]}

    self.update_state(state='PROGRESS', meta={'current': 1, 'total': 10,
                                              'status': 'Unzipping data'})
    language_obj.clean_up_datasets(data_folder)
    extract_zip(zip_filename, data_folder)

    self.update_state(state='PROGRESS', meta={'current': 2, 'total': 10,
                                              'status': 'Preprocessing files and ' + \
                                                        'collecting dependency information... ' + \
                                                        '(This may take several minutes or longer,' + \
                                                        ' depending on the complexity of your scripts)'})
    start_time = timer()
    static_results = language_obj.script_analysis(preprocess=preprocess, data_folder=data_folder, user_pkg=user_pkgs)

    if not isinstance(static_results, StaticAnalysisResults):
        return {'current': 100, 'total': 100, 'status': ['Error, static analysis feature is malformed.',
                                                         [["Returned " +
                                                           type(static_results) +
                                                           " instead of StaticAnalysisResults"]]]}

    self.update_state(state='PROGRESS', meta={'current': 3, 'total': 10,
                                              'status': 'Generating Dockerfile... '})

    language_obj.build_docker_file(data_folder, static_results, code_btw, run_instr)
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 10,
                                              'status': 'Building Docker image... '})
                                              
    language_obj.build_docker_img(language_obj.get_dockerfile_dir(data_folder), current_user_id, name)
    self.update_state(state='PROGRESS', meta={'current': 7, 'total': 10,
                                              'status': 'Collecting container environment information... '})

    report = None
    end_time = timer() - start_time
    if make_report:
        report = language_obj.create_report(current_user_id, name, data_folder, end_time)
    self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10,
                                              'status': 'Pushing Docker image to Dockerhub... '})

    if upload:
        language_obj.push_docker_img(current_user_id, name, report)
    self.update_state(state='PROGRESS', meta={'current': 9, 'total': 10,
                                              'status': 'Cleaning up...'})

    language_obj.clean_up_datasets(data_folder)
    return {'current': 10, 'total': 10,
            'status': 'RAAS has finished! Your new image is accessible from the home page.',
            'result': 42, 'errors': 'No errors!'}


def extract_zip(zip_file, name):
    with ZipFile(os.path.join(app.instance_path, 'datasets', zip_file), 'r') as zip_ref:
        if dir_as_root(zip_ref):
            zip_ref.extractall(os.path.join(app.instance_path, 'datasets', name))
        else:
            zip_ref.extractall(os.path.join(app.instance_path, 'datasets', name, "dataset"))
    os.remove(os.path.join(app.instance_path, 'datasets', zip_file))


def dir_as_root(zip_ref):
    if any(len(zip_content.split("/")) == 1 for zip_content in zip_ref.namelist()):
        return False
    root_dirs = [zip_content for zip_content in zip_ref.namelist() if
                 len(zip_content.split("/")) == 2 and zip_content.split("/")[1] == '']
    if len(root_dirs) == 1:
        return True
    else:
        return False
