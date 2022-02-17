import requests
import re
import os

def get_r_dois(save=False, print_status=False,
               api_url="https://dataverse.harvard.edu/api/search/", max_retries=5):
    """Get list of dois for all R files in a dataverse (defaulting to Harvard's)
    Parameters
    ----------
    dataverse_key : string 
                    containing user's dataverse API key
    save : boolean
           whether or not to save the result as a .txt file
    print_status : boolean
                   whether or not to print status messages
    api_url : string
              url pointing to the dataverse to get URLs for
    Returns
    -------
    r_dois : list of string
             dois containing r_files in Harvard dataverse
    """
    # defining some constants
    r_file_query = "fileContentType:type/x-r-syntax"

    # initialize variables to store current state of scraping
    page_num = 0
    r_dois = []
    failures = 0
    numfiles = 0

    #  keep requesting until the API returns fewer than 1000 results
    while True:
        if print_status:
            print("Requesting page {} from API...".format(page_num))
        try:
            # query the API for 1000 results
            myresults = requests.get(api_url,
                                     params= {"q": r_file_query, "type": "file",
                                     "start": str(1000 * page_num),
                                     "per_page": str(1000)}).json()['data']['items']

            if print_status:
                print("Parsing results from page {}...".format(page_num))
            
            # iterate through results, recording dataset_citations
            for myresult in myresults:
                # extract the DOI (if any) from the result
                doi_match = re.search("(doi:[^,]*)", myresult['dataset_persistent_id'])
                if doi_match:
                    r_dois.append(doi_match.group(1) + '\n')
        # retry if failed to pull data
        except:
            if print_status:
                print("Failed to fetch results for page {}. {} retries left".format(page_num,
                                                                                    max_retries - 1 - failures))
            if failures < max_retries:
                failures += 1
                continue
            else:
                break

        # if fewer than 1000 results were returned; we must have reached the end
        if len(myresults) < 1000:
            if print_status:
                print("Reached last page of results. Done.")
                print("Total Number of R Files: {}".format(numfiles + len(myresults)))
            break
        page_num += 1
        numfiles += 1000

    # remove duplicate DOIs
    r_dois = list(set(r_dois))

    # if save, then save as .txt file 
    if save:
        # remove old output file if one exists
        if os.path.exists('r_dois.txt'):   
            os.remove('r_dois.txt')

        # write dois to file, one-per-line
        with open('r_dois.txt', 'a') as myfile:
            for doi in r_dois:
                myfile.write(doi)
    return r_dois

if __name__ == "__main__":
    get_r_dois(save=True, print_status=True)