These installation instructions were created by installing containR on an Ubuntu 19.10 laptop. 

## Description of the software used in this tutorial
Ubuntu 19.10 (has also been done on 19.04)
Python 3.6.1 (Used through the virtualenv)


## Download containR

clone this repository
```{bash}
git clone <copy and paste repository name here>
```

## Set up Python Virtual Environment

To set up the environment ensure Python 3.6.1 is installed on the system as either the default or alternative installation. By default the Python 3 version Ubuntu uses is 3.7.5. If necessary install Python 3.6.5 first, then from pip install virtualenv. 

With the correct version of python installed, create a new virtual environment and the activate it.
```{bash}
virtualenv --python=python3.6 .containrPy

source .containrPy/bin/activate
```

When you want to deactivate the virtual environment run ```deactivate```.

## Install Python Requirements

Make sure pip is up to date
 
```{bash}
python -m pip install --upgrade pip
```

Then to install the required Python packages, navigate to the containr repo if not there already and run
```{bash}
pip install -r requirements.txt
```

## ProvDebug
ContainR uses a package written to parse this type of provenance. It is not available from pip but must be installed from GitHub. 

Before installing ensure you have your python virtual environment activated. 
```{bash}
git clone https://github.com/jwons/MultilingualProvenanceDebugger

cd MultilingualProvenanceDebugger

python setup.py install
```

## Redis

ContainR uses Redis, a key-value store. It must be installed and run.
https://tecadmin.net/install-redis-ubuntu/


```{bash}
sudo apt install redis-server

#From link above
#Next is to enable Redis to start on system boot. Also restart Redis service once.
sudo systemctl enable redis-server.service
```

To ensure everything up to this point is installed open a terminal, activate the python virtual environment and run the following line from the containR directory:
```{bash}
celery -A app.celery worker
```


## Install R 

To install R, run the following command
```{bash}
sudo apt update
sudo apt install r-base
```

This will put R on your system, __please note__ that while the R base is installed, researchers' scripts downloaded from the internet may require other packages AND other non-R dependencies. 


Helpful but not necessary: download R Studio Desktop.
https://rstudio.com/products/rstudio/download/

Download the RStduio Ubuntu deb that matches your system best. In this case I chose "Ubuntu 18/Debian 10 	rstudio-1.2.5033-amd64.deb"

Install with
```{bash}
sudo dpkg -i rstudio-1.2.5033-amd64.deb

```
(I had to run a `sudo apt --fix-broken install` before RStudio would install)

# Install Docker

Install docker with 
```{bash}
sudo apt install docker.io

sudo systemctl start docker
sudo systemctl enable docker
```

To check to make sure it is installed correctly run
```{bash}
docker --version
```
and it should return something like ```Docker version 19.03.2, build 6a30dfca03```


## Configure Docker Authentication

To ensure docker can connect to Docker hub we need to add a new group and add the user to it. 

```{bash}
sudo groupadd docker
sudo usermod -aG docker $USER
```

The group may already exist, but once these commands are run restart and try ```docker run hello-world``` and ensure it can be run without sudo. Additionally, run ```docker login``` to ensure you can authenticate. For authentication consider generating a token on the docker website instead of using your password. 

Set DOCKER_REPO, DOCKER_USERNAME, DOCKER_PASSWORD environment variables to the correct credentials to connect to Docker. The docker repo will be the account pushing to. It seems username and repo will likely be identical.  

```{bash}
export DOCKER_USERNAME="username"
export DOCKER_PASSWORD="password" 
export DOCKER_REPO="repo name, probably same as username"
```

## Running ContainR

Navigate to the containr directory in two terminals with the python virtual environment activated. 

In the first terminal run 
```{bash}
celery -A app.celery worker
```

```{bash}
export FLASK_APP=containr.py

flask run
```

## Instructions for using ContainR

From the build image page it is possible to either upload a zip file *of a directory* or enter a Harvard Dataverse DOI which it will then try to scrape. When choosing a name for the dataset, the name *must* be in all-lowercase. 
