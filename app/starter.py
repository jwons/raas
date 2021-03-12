import os
from app import celery
from app.language_python.python_lang_obj import py_lang
from app.language_r.r_lang_obj import r_lang
from app.language_julia.julia_lang_obj import julia_lang
from app.language_matlab.matlab_lang_obj import matlab_lang
from timeit import default_timer as timer

from app import app

#Debugging
from celery.contrib import rdb

@celery.task(bind=True)
def start_raas(self, language, current_user_id, name, preprocess, data_folder='',
               run_instr='', user_pkgs='', sample_output=None, code_btw=None, 
               prov=None, upload = True, make_report = True):

    if language == "Python":
        language_obj = py_lang()
    elif language == "R":
        language_obj = r_lang()
    elif language == "Julia":
        language_obj = julia_lang()
    elif language == "Matlab":
        language_obj = matlab_lang()
    else:
        return {'current': 100, 'total': 100, 'status': ['Error in language.',
                                                         [[language + " is not supported"]]]}
    try:
        self.update_state(state='PROGRESS', meta={'current': 1, 'total': 10,
                                                  'status': 'Preprocessing files for errors and ' + \
                                                            'collecting provenance data... ' + \
                                                            '(This may take several minutes or longer,' + \
                                                            ' depending on the complexity of your scripts)'})
        start_time = timer()
        after_analysis = language_obj.script_analysis(preprocess = preprocess, data_folder= data_folder, user_pkg= user_pkgs)

        # Some error found by analysis
        if(not ('dir_name' in after_analysis)):
            return after_analysis

        dir_name = after_analysis["dir_name"]
        docker_pkgs = after_analysis["docker_pkgs"]
        self.update_state(state='PROGRESS', meta={'current': 3, 'total': 10,
                                                  'status': 'Generating Dockerfile... '})
        docker_file_dir = language_obj.build_docker_file(dir_name, docker_pkgs, after_analysis, code_btw, run_instr)

        self.update_state(state='PROGRESS', meta={'current': 4, 'total': 10,
                                                  'status': 'Building Docker image... '})

        language_obj.build_docker_img(docker_file_dir, current_user_id, name)
        self.update_state(state='PROGRESS', meta={'current': 7, 'total': 10,
                                                  'status': 'Collecting container environment information... '})
        report = None
        end_time = timer() - start_time
        if(make_report): report = language_obj.create_report(current_user_id, name, dir_name, end_time)
        self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10,
                                                'status': 'Pushing Docker image to Dockerhub... '})
        if(upload): language_obj.push_docker_img(dir_name, current_user_id, name, report)
        self.update_state(state='PROGRESS', meta={'current': 9, 'total': 10,
                                                  'status': 'Cleaning up...'})
        language_obj.clean_up_datasets(data_folder)
        return {'current': 10, 'total': 10,
                'status': 'RAAS has finished! Your new image is accessible from the home page.',
                'result': 42, 'errors': 'No errors!'}
    except:
        language_obj.clean_up_datasets(data_folder)
        raise
