import os
import requests
import cgi
import shutil
import docker
import json
import threading
import sqlite3
import pandas as pd

from urllib3.exceptions import ReadTimeoutError
from sqlalchemy import create_engine
from io import StringIO
from docker import APIClient

def doi_to_directory(doi):
    """Converts a doi string to a more directory-friendly name
    Parameters
    ----------
    doi : string
          doi

    Returns
    -------
    doi : string
          doi with "/" and ":" replaced by "-" and "-" respectively
    """
    return doi.replace("/", "-").replace(":", "-")

def download_dataset(doi, destination,
                     api_url="https://dataverse.harvard.edu/api/"):
    """Download doi to the destination directory
    Parameters
    ----------
    doi : string
          doi of the dataset to be downloaded
    destination : string
                  path to the destination in which to store the downloaded directory
    dataverse_key : string
                    dataverse api key to use for completing the download
    api_url : string
              URL of the dataverse API to download the dataset from
    Returns
    -------
    bool
    whether the dataset was successfully downloaded to the destination
    """
    api_url = api_url.strip("/")
    # make a new directory to store the dataset
    # (if one doesn't exist)


    try:
        # query the dataverse API for all the files in a dataverse
        files = requests.get(api_url + "/datasets/:persistentId",
                             params={"persistentId": doi}) \
            .json()['data']['latestVersion']['files']

    except:
        return False

    # convert DOI into a friendly directory name by replacing slashes and colons
    doi_direct = destination + '/' + doi_to_directory(doi)
    # make a new directory to store the dataset
    if not os.path.exists(doi_direct):
        os.makedirs(doi_direct)

    # for each file result
        for file in files:
            try:
                # parse the filename and fileid
                # filename = file['dataFile']['filename']
                fileid = file['dataFile']['id']
                contentType = file['dataFile']['contentType']
                timeout_duration = 5
                timeout_limit = 3
                attempts = 0
                if (contentType == 'type/x-r-syntax'):
                    while (attempts < timeout_limit):
                        try:
                            # query the API for the file contents
                            response = requests.get(
                                api_url + "/access/datafile/" + str(fileid), timeout = timeout_duration)
                        except Exception:
                            attempts += 1
                            if(attempts == timeout_limit):
                                print("Timed-out too many times. Check internet connection?")
                                exit(1)
                            else:    
                                print("Timeout hit trying again")
                            continue
                        break
                else:
                    
                    while (attempts < timeout_limit):
                        try:
                            # query the API for the file contents
                            if("originalFileFormat" in file["dataFile"].keys()):
                                response = requests.get(api_url + "/access/datafile/" + str(fileid),
                                                    params={"format": "original"}, timeout = timeout_duration)
                            else:
                                response = requests.get(api_url + "/access/datafile/" + str(fileid), timeout = timeout_duration)
                        except Exception:
                            attempts += 1
                            if(attempts == timeout_limit):
                                print("Timed-out too many times. Check internet connection?")
                                exit(1)
                            else:    
                                print("Timeout hit trying again")
                            continue
                        break
                value, params = cgi.parse_header(
                    response.headers['Content-disposition'])
                if 'filename*' in params:
                    filename = params['filename*'].split("'")[-1]
                else:
                    filename = params['filename']

                # write the response to correctly-named file in the dataset directory
                with open(doi_direct + "/" + filename, 'wb') as handle:
                    handle.write(response.content)
            except:
                return False
        #shutil.make_archive(doi_direct, 'zip', doi_direct)
        #shutil.rmtree(doi_direct)
    else:
        print("Repeat Dataset")
        doi_direct = False
    
    return doi_direct

# This function takes a list of directories, puts each directory into an r-base container 
# and then attempts to execute all of the R scripts inside the dataset and records all
# the errors that may occur within them. These results are saved to a database and this function
# is executed asynchronously 
def batch_run(datadirs):
    run_logs = []
    skipped = []
    for datadir in datadirs:
        # A dockerfile is written for each directory specifying how to build the image
        # Running the R scripts is part of the build process
        with open(os.path.join("datasets", 'Dockerfile'), 'w') as new_docker:
            new_docker.write("FROM r-base:3.6.3\n")
            new_docker.write("ADD " + os.path.basename(datadir) + " /home/docker/" + os.path.basename(datadir) + "\n")
            new_docker.write("COPY get_dataset_results.R /home/get_dataset_results.R\n")
            new_docker.write("RUN Rscript /home/get_dataset_results.R /home/docker\n")
        
        # Connect to docker to build the image
        client = docker.APIClient(base_url='unix://var/run/docker.sock')

        # Tags cannot have uppercase characters, and it is better to not have double special characters either
        tag = os.path.basename(datadir).replace(".", "-").lower()

        try:
            generator = client.build(path="datasets", tag=tag, timeout=3600)

            # This will build the image, uncomment the print statement to get output from build 
            for chunk in generator:
                if 'stream' in chunk.decode():
                    for line in json.loads(chunk.decode())["stream"].splitlines():
                        #print(line)
                        pass
        except ReadTimeoutError:
            print(datadir + " timed-out and was skipped")
            skipped.append(datadir)

        # To collect the results from the container we need to run the container just to get the run_log.csv
        # which is where the results are kept
        client = docker.from_env() 

        # Collect log, specify sep, engine, and escapechar to prevent pandas parsing errors
        run_log = client.containers.run(tag, "cat /home/docker/prov_data/run_log.csv").decode()
        log_df = pd.read_csv(StringIO(run_log), sep=",", engine='python', escapechar="\\")

        # remove containers, images, and dir to keep storage costs down
        client.containers.prune()
        client.images.remove(tag)
        shutil.rmtree(datadir)

        # record results
        run_logs.append(log_df)
        

    # Clear up dataset dir
    if os.path.exists("datasets/Dockerfile"):
        os.remove("datasets/Dockerfile")

    # create one big dataframe so it can be inserted into database
    run_logs = pd.concat(run_logs)
    engine = create_engine('sqlite:///results.db', echo=False)
    run_logs.to_sql('results', con=engine, if_exists='append', index=False)

    if(len(skipped) is not 0):
        with open("timed_out.txt", "a+") as timed_out:
            for datadir in skipped:
                timed_out.write(datadir)
    
if __name__ == "__main__":

    # this file is created by the get_r_dois.py script
    with open('r_dois.txt') as doi_file:
        dois = doi_file.readlines()
    
    dois = dois[0:8]
    start = 0
    end = 2
    increment_by = 2
    if not os.path.exists("datasets"):
        os.makedirs("datasets")
    shutil.copy("get_dataset_results.R", "datasets/get_dataset_results.R")
    batch_thread = None
    batch_counter = 0
    while(True):
        data_dirs_chunk = []
        for data_index in range(start, end):
            print("Downloading dataset " + str(data_index) + ": " + dois[data_index])
            datadir = download_dataset(dois[data_index].strip("\n"), "datasets")
            data_dirs_chunk.append(datadir)
        data_dirs_chunk = list(set(data_dirs_chunk))

        if(False in data_dirs_chunk):
            data_dirs_chunk.remove(False)
        
        if batch_thread is not None:
            batch_thread.join()
            print("Batch " + str(batch_counter) + " completed.")
            batch_counter += 1
        batch_thread = threading.Thread(target=batch_run, args=(data_dirs_chunk,), daemon=True)
        batch_thread.start()

        if(end == len(dois)):
            break

        start += increment_by
        end += increment_by
        if (end > len(dois)):
            end = len(dois)

    batch_thread.join()
