These installation instructions were created by installing containR on an Ubuntu 19.10 laptop. 

## Description of the software used in this tutorial
- Ubuntu 19.10 (has also been done on 19.04)
- Python 3.6.1 (Used through the virtualenv)
- Redis Server 5.0.5
- Docker 19.03.2
- R 3.6.1


## Installation Instructions
It is important to follow these instructions in the order they are presented as some of them rely on the things installed beforehand. 

### Download containR

clone this repository
```{bash}
git clone <copy and paste repository name here>
```

### Set up Python Virtual Environment

Your environment can be setup in whatever your preffered virtual environment is. containR has been run from a conda and virtualenv environment. However, personal choice, conda tends to be easy to work with. Once a virtual environment is created, whether it be through conda or virtualenv (or venv which is not in this tutorial) make sure it is always activated when doing anything with containR. 

To use conda run:

```{bash}
conda create --name containr python=3.6

conda activate containr
```
When installing packages in the virtual environment in the next section, make sure to use ```pip install``` not ```conda install```.

To set up the environment in virtualenv ensure Python 3.6.1 is installed on the system as either the default or alternative installation. By default the Python 3 version Ubuntu uses is 3.7.5. If necessary install Python 3.6.1 first, then from pip install virtualenv. 

With the correct version of python installed, create a new virtual environment and the activate it.
```{bash}
virtualenv --python=python3.6 .containrPy

source .containrPy/bin/activate
```

When you want to deactivate your virtual environment run ```deactivate```. However, after this point in the tutorial, assume any terminal started is also running the python virtual environment. 

### Install Python Requirements

Make sure pip is up to date
 
```{bash}
python -m pip install --upgrade pip
```

Then to install the required Python packages, navigate to the containr repo if not there already and run
```{bash}
pip install -r requirements.txt
```

### ProvDebug
ContainR uses a package written to parse this type of provenance. It is not available from pip but must be installed from GitHub. 

Before installing ensure you have your python virtual environment activated. 
```{bash}
git clone https://github.com/jwons/MultilingualProvenanceDebugger

cd MultilingualProvenanceDebugger

python setup.py install
```

### Redis

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


### Install R 

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

### Install rdtLite and devtools
To install rdtLite you will need the devtools R package which allows you to install packages from GitHub.
In case you don't already have them, install these dependencies first:

```{bash}
sudo apt install build-essential libcurl4-gnutls-dev libxml2-dev libcurl4-openssl-dev
```

There may be additional dependencies not captured here, or you may already have these. Watch during the installation of devtools for any mention of missing requirements, a lot may show up on the screen and they could get lost. If there are any, the installation will finish with a note saying it had a non-zero exit status. 

Then from an R console run:
```{r}
install.packages("devtools") # This could take a few minutes
```
Once that has finished run the following devtools command:

```{r}
devtools::install_github("End-to-end-provenance/rdtLite")
```
For more information on rdtLite visit the [GitHub repo](https://github.com/End-to-end-provenance/RDataTracker).

### Install Docker

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


### Configure Docker Authentication

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


