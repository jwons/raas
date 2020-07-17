from app import celery
from app.language_python.pyPlace import py_place


@celery.task(bind=True)
def start_raas(self, language, current_user_id, name, preprocess, dataverse_key='', doi='', data_folder='',
               run_instr='',
               user_pkgs='', sample_output=None, code_btw=None, prov=None):
    if language == "Python":
        language_obj = py_place()
    else:
        return {'current': 100, 'total': 100, 'status': ['Error in language.',
                                                         [[language + " is not supported"]]]}
    self.update_state(state='PROGRESS', meta={'current': 1, 'total': 10,
                                              'status': 'Preprocessing files for errors and ' + \
                                                        'collecting provenance data... ' + \
                                                        '(This may take several minutes or longer,' + \
                                                        ' depending on the complexity of your scripts)'})
    after_preprocess = language_obj.preprocessing(preprocess, dataverse_key, doi, data_folder, user_pkgs)
    print(str(after_preprocess))
    dir_name = after_preprocess["dir_name"]
    docker_pkgs = after_preprocess["docker_pkgs"]
    self.update_state(state='PROGRESS', meta={'current': 3, 'total': 10,
                                              'status': 'Generating Dockerfile... '})
    docker_file_dir = language_obj.build_docker_file(dir_name, docker_pkgs, after_preprocess, code_btw,run_instr)
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 10,
                                              'status': 'Building Docker image... '})
    language_obj.build_docker_img(docker_file_dir, current_user_id, name)
    self.update_state(state='PROGRESS', meta={'current': 7, 'total': 10,
                                              'status': 'Collecting container environment information... '})

    report = language_obj.create_report(current_user_id, name, dir_name)
    self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10,
                                              'status': 'Pushing Docker image to Dockerhub... '})

    language_obj.push_docker_img(dir_name, current_user_id, name, report)
    self.update_state(state='PROGRESS', meta={'current': 9, 'total': 10,
                                              'status': 'Cleaning up...'})
    language_obj.clean_up_datasets(dir_name)
    return {'current': 10, 'total': 10,
            'status': 'RAAS has finished! Your new image is accessible from the home page.',
            'result': 42, 'errors': 'No errors!'}
