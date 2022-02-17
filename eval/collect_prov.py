import pandas

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

    except Exception as e:
        print("Could not get dataset info from dataverse")
        print(e)
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

r_dois = []
with open("r_dois_by_time.csv", "r") as r_doi_file:
        r_dois = r_doi_file.readlines()

r_dois = [x.strip("\n") for x in r_dois]

