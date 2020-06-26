import subprocess
import json

def pylint_parser(filename,py3):
    if(py3):
        pylint_ver = 'pylint3'
    else:
        pylint_ver = 'pylint2'

    ans = subprocess.Popen('eval "$(conda shell.bash hook)" && conda activate '+pylint_ver+'&& pylint -d C,R,W,E0401 --output-format=json '+filename,shell=True, stdout=subprocess.PIPE)    
    temp = ans.communicate()[0]

    if(temp==b''):
        return (False,'')
    else:
        y = json.loads(temp)
        if(len(y)!=0):
            if(y[0]['message-id'][0] == 'E'):
                return (True,y[0]['message'])
                
            if(y[0]['message-id'][0] == 'F'):
                return (True,y[0]['message'])
        else:
            return (False,'')
