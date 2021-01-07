import argparse
import requests
import time

def headless_raas():
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
    dataverse_key=''
    to_pre = "0"
    if not args.name:
        print("You must provide a name")
        quit()
    if args.preprocess == True:
        to_pre = "1"
    request = "http://127.0.0.1:" + args.port + "/api/build_image?preprocess=" +\
         to_pre + "&userID=" + str(args.user) + "&"
    if args.doi:
        request = request + "doi=" + args.doi + "&"
    elif args.zip:
        request = request + "zipFile=" + args.zip + "&"
    else:
        print("Provide at least a zip or doi")
        quit()

    request = request + "name=" + args.name + "&language=" + args.lang

    print(request)

    result = requests.get(request)
    task_id = result.json()["task_id"]

    status_request = "http://127.0.0.1:" + args.port + "/status/" + task_id

    while(True):
        task_status = requests.get(status_request).json()
        print(task_status)
        if(task_status["current"] == 10):
            print("Build Complete")
            break
        if(task_status["state"] != "PROGRESS"):
            print("Build probably failed moving on")
            break
        time.sleep(5)

    print(result.json())

    return (True)

if __name__ == "__main__":
    headless_raas()