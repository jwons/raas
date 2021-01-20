import argparse
import requests
import time



def headless_raas(name, lang, user = 1, preproc = "0", doi = "", zip_path = "", port = "5000" ):
    
    if(doi == "" and zip_path == ""):
        print("Must supply either zip or doi")
        return(False)

    request = "http://127.0.0.1:" + port + "/api/build_image?preprocess=" +\
         preproc + "&userID=" + str(user) + "&name=" + name + "&language=" + lang

    
    if(zip_path is not ""):
        request = request + "&zipFile=" + zip_path
    else:
        request = request + "&doi=" + doi

    print(request)

    result = requests.get(request)
    task_id = result.json()["task_id"]

    status_request = "http://127.0.0.1:" + port + "/status/" + task_id

    while(True):
        task_status = requests.get(status_request).json()
        print(task_status)
        if(task_status["current"] == 10):
            print("Build Complete")
            break
        if(task_status["state"] == "FAILURE"):
            print("Build probably failed moving on")
            break
        time.sleep(5)

    print(result.json())

    return (True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A command-line interface to containR\'s web API.')

    parser.add_argument('--name', type=str, required=True, help=\
        'a dataset name, must be all lowercase with no spaces or special characters other than "-" ')

    parser.add_argument('--user', type=int, default=1, help=\
        'a user\'s ID, by default 1')

    parser.add_argument('--preprocess', type=bool, default=False, help=\
        'Whether or not to preprocess the code')

    parser.add_argument('--doi', type=str, help=\
        'A doi in string format that identifies a dataset from Harvard\'s Dataverse')

    parser.add_argument('--zip', type=str, help=\
        'A filepath to a zip file that contains scripts and data')

    parser.add_argument('--lang', type=str, required=True, help=\
        'Which language the code is in, options are R and Python')

    parser.add_argument('--port', type=str, default="5000", help=\
        'The port number containR is running on, by default 5000')    

    args = parser.parse_args()

    to_pre = "0"
    req_doi = None
    req_zip = None

    if args.preprocess == True:
        to_pre = "1"
    
    if args.doi:
        headless_raas(name=args.name, lang = args.lang, preproc=to_pre, doi=args.doi)
    elif args.zip:
        headless_raas(name=args.name, lang = args.lang, preproc=to_pre, zip_path=args.zip)

    else:
        print("Provide at least a zip or doi")
        quit()
