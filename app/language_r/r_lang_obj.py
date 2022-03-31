import os
import subprocess
import json
import docker
import re

from glob import glob
from app.languageinterface import LanguageInterface
from app.languageinterface import StaticAnalysisResults
from app.language_r.preproc_helpers import all_preproc
from shutil import copy

# Debugging
from celery.contrib import rdb


class RLang(LanguageInterface):

    def __init__(self):
        self.dataset_dir = None

    @staticmethod
    def build_docker_package_install(package, version):
        """Outputs formatted dockerfile command to install a specific version
        of an R package into a docker image
        Parameters
        ----------
        package : string
                        Name of the R package to be installed
        version : string
                        Version number of the desired package
        """
        return 'RUN R -e \"require(\'devtools\');  {install_version(\'' + package + \
               '\', version=\'' + version + '\', repos=\'http://cran.rstudio.com\')}"\n'

    @staticmethod
    def build_docker_package_install_no_version(package):
        """Outputs formatted dockerfile command to install a specific version
        of an R package into a docker image
        Parameters
        ----------
        package : string
        """
        return 'if(!(\'' + package + '\'' \
                                     '%in% rownames(installed.packages()))){install.packages(\'' + package + '\')}\n' + \
               'if(!(\'' + package + '\'' \
                                     '%in% rownames(installed.packages()))){BiocManager::install(\'' + package + \
               '\', update = F)}\n'

    def script_analysis(self, preprocess, dataverse_key='', data_folder='', run_instr='', user_pkg=''):
        # This variable controls whether the container is built despite the existence
        # of errors detected in the script
        build_with_errors = False

        dockerfile_dir = self.get_dockerfile_dir(data_folder)
        self.dataset_dir = os.path.join(dockerfile_dir, os.listdir(dockerfile_dir)[0])
        original_scripts_dir = os.path.join(dockerfile_dir, "__original_scripts__")
        static_analysis_dir = os.path.join(dockerfile_dir, "static_analysis")

        # ---------- Preprocessing ------------
        src_ignore = []
        if preprocess:
            r_files = [y for x in os.walk(os.path.join(self.dataset_dir)) for y in glob(os.path.join(x[0], '*.R'))]

            if not os.path.exists(original_scripts_dir):
                os.makedirs(original_scripts_dir)

            for r_file in r_files:
                r_file = os.path.split(r_file)
                sourced_files = all_preproc(r_file[1], r_file[0])
                copy(os.path.join(r_file[0], r_file[1]), os.path.join(original_scripts_dir, r_file[1]))
                src_ignore.append(os.path.join("/__original_scripts__", r_file[1]))
                src_ignore = src_ignore + sourced_files
                os.remove(os.path.join(r_file[0], r_file[1]))

            pre_files = [y for x in os.walk(os.path.join(self.dataset_dir)) for y in
                         glob(os.path.join(x[0], '*__preproc__.R'))]

            for pre_file in pre_files:
                pre_file = os.path.split(pre_file)
                filename = re.split('\__preproc__.[rR]$', pre_file[1])[0]
                os.rename(os.path.join(pre_file[0], pre_file[1]), os.path.join(pre_file[0], filename + ".R"))

        # ---------- STATIC ANALYSIS ----------
        subprocess.run(['bash', 'app/language_r/static_analysis.sh', self.dataset_dir, static_analysis_dir])

        # ---------- PARSING STATIC ANALYSIS ----------

        # assemble a set of packages used and get system requirements
        sys_reqs = []
        used_packages = []
        with open(os.path.join(static_analysis_dir, "static_analysis.json")) as json_file:
            data = json.load(json_file)
            if not build_with_errors:
                if data['errors']:
                    return {'current': 100, 'total': 100,
                            'status': ['Static analysis found errors in script.', data['errors']]}
            used_packages = data['packages']
            sys_reqs = data['sys_deps']

        sys_reqs.append("libjpeg-dev")
        sys_reqs.append("libxt6")

        return StaticAnalysisResults(lang_packages=used_packages, sys_libs=sys_reqs, lang_specific={"src_ignore":
                                                                                                    src_ignore})

    def build_docker_file(self, dir_name, static_results, code_btw, run_instr):
        ext_pkgs = code_btw

        # TODO: equivalent for install_instructions, is there a difference for R/Python?
        special_packages = None
        special_install = None
        install_instructions = ''
        if install_instructions is not '':
            special_install = json.loads(install_instructions)
            special_packages = [special_install["packages"][key][0]
                                for key in special_install["packages"].keys()]

        docker_file_dir = self.get_dockerfile_dir(dir_name)

        if not os.path.exists(docker_file_dir):
            return {'current': 100, 'total': 100, 'status': 'Directory missing.'}

        if len(static_results.lang_specific["src_ignore"]) > 0:
            with open(os.path.join(docker_file_dir, '.srcignore'), 'w') as src_ignore_file:
                for line in static_results.lang_specific["src_ignore"]:
                    src_ignore_file.write(line + "\n")
                src_ignore_file.write('\n')
        backup_install_packages = 'backup_install_packages.R'
        with open(os.path.join(docker_file_dir, backup_install_packages), 'w') as install_packs:
            install_packs.write('if(file.exists("/home/rstudio/.Renviron")){q(save = "no")}\n')
            install_packs.write('require(\'devtools\')\n')
            install_packs.write('require(\'BiocManager\')\n')
            install_rdt = """
devtools::install_github("End-to-end-provenance/provParseR")
devtools::install_github("End-to-end-provenance/provViz")
devtools::install_github("End-to-end-provenance/provSummarizeR")
devtools::install_github("End-to-end-provenance/rdtLite")                   
"""
            # install_packs.write(install_rdt)
            # perform any pre-specified installs
            if special_packages:
                for key in special_install["packages"].keys():
                    instruction = special_install["packages"][key][1] + '"\n'
                    install_packs.write(instruction)

            # install packages
            docker_packages = list(set(static_results.lang_packages))
            if docker_packages:
                for package in docker_packages:
                    if special_packages and (package not in special_packages):
                        install_packs.write(self.build_docker_package_install_no_version(package))
                    if special_packages is None:
                        install_packs.write(self.build_docker_package_install_no_version(package))

        with open(os.path.join(docker_file_dir, 'Dockerfile'), 'w') as new_docker:
            new_docker.write('FROM rocker/tidyverse:latest\n')

            # install system requirements
            sysinstall = "RUN export DEBIAN_FRONTEND=noninteractive; apt-get -y --allow-releaseinfo-change update && apt-get install -y "
            if len(static_results.sys_libs) != 0:
                new_docker.write(sysinstall + ' '.join(static_results.sys_libs) + '\n')

            # perform any pre-specified installs
            if special_install:
                if "sys-libs" in special_install.keys():
                    new_docker.write(sysinstall + ' '.join(special_install["sys-libs"]) + '\n')

            # Install libraries
            copy("app/language_r/install_packages.R", docker_file_dir)
            new_docker.write('COPY install_packages.R /home/rstudio/\n')
            new_docker.write('COPY ' + backup_install_packages + ' /home/rstudio/\n')
            new_docker.write('RUN Rscript /home/rstudio/install_packages.R ' + " ".join(docker_packages) + '\n')
            new_docker.write('RUN Rscript /home/rstudio/' + backup_install_packages + '\n')


            # These scripts will execute the analyses and collect provenance. Copy them to the
            # Dockerfile directory first since files copied to the image cannot be outside it
            copy("app/language_r/get_prov_for_doi.sh", docker_file_dir)
            copy("app/language_r/get_dataset_provenance.R", docker_file_dir)
            copy("app/language_r/create_report.R", docker_file_dir)

            # Add the dataset to the container
            new_docker.write('COPY . /home/rstudio/' + dir_name + '\n')

            # Add permissions or the scripts will fail
            new_docker.write('RUN chown -R  rstudio:rstudio /home/rstudio/\n')

            # Execute analysis and collect provenance
            new_docker.write('RUN /home/rstudio/' + dir_name + '/get_prov_for_doi.sh /home/rstudio/' + \
                             dir_name + '/get_dataset_provenance.R ' + '/home/rstudio/' + dir_name + \
                             '/' + os.path.basename(self.dataset_dir) + '\n')

            # Collect installed package information for the report              
            new_docker.write("RUN Rscript /home/rstudio/" + dir_name + "/create_report.R /home/rstudio/" + dir_name +
                             "/prov_data \n")

            # Add permissions or the scripts will fail
            new_docker.write('RUN chown -R  rstudio:rstudio /home/rstudio/\n')

    def create_report(self, current_user_id, name, dir_name, time):

        # ---------- Generate Report About Build Process ----------
        # The report will have various information from the creation of the container
        # for the user

        # Reconstruct image name from user info
        client = docker.from_env()

        # to get report we need to run the container
        container = client.containers.run(image=self.get_container_tag(current_user_id, name),
                                          environment=["PASSWORD=pass"], detach=True)

        # Grab the files from inside the container and the filter to just JSON files
        report = json.loads(container.exec_run("cat /home/rstudio/report.json")[1].decode())
        report["Additional Information"] = {}
        report["Additional Information"]["Container Name"] = self.get_container_tag(current_user_id, name)
        report["Additional Information"]["Build Time"] = time

        # information from the container is no longer needed
        container.kill()

        return report
