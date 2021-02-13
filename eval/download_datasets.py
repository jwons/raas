import os
import requests
import cgi
import shutil

from run_eval import batch_raas
from headless_raas import headless_raas

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
    if not os.path.exists(destination):
        os.makedirs(destination)

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

                if (contentType == 'type/x-r-syntax'):
                    # query the API for the file contents
                    response = requests.get(
                        api_url + "/access/datafile/" + str(fileid))
                else:
                    # query the API for the file contents
                    if("originalFileFormat" in file["dataFile"].keys()):
                        response = requests.get(api_url + "/access/datafile/" + str(fileid),
                                            params={"format": "original"})
                    else:
                        response = requests.get(api_url + "/access/datafile/" + str(fileid))

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

if __name__ == "__main__":

    with open('r_dois.txt') as doi_file:

        dois = doi_file.readlines()
    
    dois = dois[0:1]
    start = 0
    end = 10
    while(True):
        data_dirs_chunk = []
        for data_index in range(start, end):
            print("Downloading dataset " + str(data_index) + ": " + dois[data_index])
            datadir = download_dataset(dois[data_index].strip("\n"), "datasets")
            data_dirs_chunk.append(datadir)
        data_dirs_chunk = list(set(data_dirs_chunk))
        print(data_dirs_chunk)
        start += 10
        end += 10
        if(end == len(dois)):
            break
        elif (end > len(dois)):
            end = len(dois)
