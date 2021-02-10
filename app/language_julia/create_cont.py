from read_project import read_project
from read_manifest import read_manifest
import os
import shutil
import semver
import zipfile
import docker
import cgi

# print(read_project())
def script_analysis(file):

    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(file[:-4])

    manifest = ''
    project = ''
    dir_path = file[:-4]
    for root, dirs, files in os.walk(dir_path): 
        for file1 in files:  
            if file1.endswith('Manifest.toml'): 
                manifest = root
                break
        else:
            continue
        break

    dir_path = file[:-4]
    for root, dirs, files in os.walk(dir_path): 
        for file1 in files:  
            if file1.endswith('Project.toml'): 
                project = root
                break
        else:
            continue
        break


    # print ("Manifest = ", manifest)
    # print ("Project = ", project)
    pkgs1 = {}
    pkgs2 = {}
    if (manifest!=''):
        pkgs1 = read_manifest(manifest)
    if (project!=''):
        pkgs2 = read_project(project)

    # print (pkgs1)
    # print (pkgs2)
    for i in pkgs2:
        if i not in pkgs1:
            pkgs1[i] = pkgs2[i]
        # else:
            # print ("kaka")
            # print (i)
            # if (semver.compare(pkgs1[i][1:-1],pkgs2[i][1:-1])==-1):
            #     # print ("lala")
            #     pkgs1[i] = pkgs2[i]

    return pkgs1

def build_docker_file(pkgs, dir_name, docker_pkgs, additional_info, code_btw = None, run_instr=None):

    ext_pkgs = code_btw
    julia_ver = 'latest'
    if ('julia' in pkgs and pkgs['julia']!='"-1"'):
        if (pkgs['julia'][1]=='0'):
            julia_ver = pkgs['julia'][1:-1]

    del pkgs['julia']

    if (run_instr!=None):
        with open('run_instr.txt', 'w+') as out:
            for instr in run_instr:
                out.write(instr + '\n')

    docker_wrk_dir = '/home/datasets/' + dir_name + '/'
    # docker_file_dir = '/home/datasets/' + dir_name + '/data_set_content/'
    # docker_home = '/home/datasets/' + dir_name + '/'
    # try:
    #     os.makedirs(os.path.join(app.instance_path, 'datasets', dir_name, 'data_set_content'))
    # except:
    #     pass
    with open('package_installs.jl', 'w+') as pkg_file:
        pkg_file.write('using Pkg;\n')
        pkg_file.write('\n')
        for pkg in pkgs:
            if (pkgs[pkg]!='"-1"'):
                pkg_file.write('Pkg.add(Pkg.PackageSpec(name="'+pkg+'",version='+pkgs[pkg]+'))\n')
            else:
                pkg_file.write('Pkg.add("'+pkg+'")\n')

#         pkg_file.write('for package=metadata_packages\n \tif (package[2]!='"-1"')\n \t\tPkg.add(name=package[1], version=package[2])\n \
# \telse\n \t\tPkg.add(package[1])\nend\n')

    #Installing a specific version of package doffers between Julia versions 1.0+ and those before, add custom support later
    with open('Dockerfile', 'w+') as new_docker:

        new_docker.write('FROM julia:'+julia_ver+'\n')

        new_docker.write('ADD package_installs.jl /tmp/package_installs.jl\n')
        new_docker.write('RUN julia /tmp/package_installs.jl\n')

        new_docker.write('WORKDIR /home/\n')
        new_docker.write('COPY ' +dir_name+'/ ' + docker_wrk_dir + '\n')
        new_docker.write('COPY run_instr.txt ' + docker_wrk_dir + '\n')

        new_docker.write('RUN chmod a+rwx -R ' + docker_wrk_dir + '\n')
        new_docker.write('WORKDIR ' + docker_wrk_dir + '\n')

        if ext_pkgs:
            for mod in ext_pkgs:
                new_docker.write("RUN " + mod + "\n")
        if docker_pkgs:
            for module in docker_pkgs:
                new_docker.write(self.build_docker_package_install(module))

    # os.system('docker build -t julia-test2 .')

        # new_docker.write("RUN pip list > /home/datasets/" + dir_name + "/listOfPackages.txt \n")
        # new_docker.write("RUN pip list > " + docker_file_dir + "listOfPackages.txt \n")

        # new_docker.write("RUN python" + str(python_ver) + " " \
        #                  + docker_home + "get_dataset_provenance.py" + " " + docker_file_dir + "\n")

    # return os.path.join(app.instance_path, 'datasets', dir_name)
    return

# def build_docker_img(docker_file_dir, name):
#         # create docker client instance

#         # build a docker image using docker file
#         self.client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))
#         # name for docker image
#         # current_user_obj = User.query.get(current_user_id)
#         # image_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
#         image_name = 'prakhar'
#         repo_name = os.environ.get('DOCKER_REPO') + '/'
#         self.client.images.build(path=docker_file_dir, tag=repo_name + image_name)

file = 'ClimateMachine.jl-master.zip'
# file = 'NLreg.jl-master.zip'
pkgs = (script_analysis(file))
print(pkgs)
build_docker_file(pkgs, file[:-4], None, None)