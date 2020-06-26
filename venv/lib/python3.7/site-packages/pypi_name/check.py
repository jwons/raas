import requests

def pypiName(packageName):
    URL = "https://pypi.org/pypi/" + packageName + "/json"
    
    r = requests.get(URL)
    
    if (r):
        return False
    else:
        return True
