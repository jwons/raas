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

## Configure Docker Authentication

Set DOCKER_USERNAME and DOCKER_PASSWORD to the correct credentials to connect to Docker. 

```{bash}
export DOCKER_USERNAME="username"
export DOCKER_PASSWORD="password" 
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
