# This Dockerfile is the first of two. This file creates
# the environment necessary to run raas. Since that process takes
# a while and is largely static, it is a separate build. The second
# will simply load the code and start the service.
FROM ubuntu:20.04
#LABEL maintainer="Joe"

# Used for miniconda installation
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"

# Prevent system library installs from failing due to lack of user input
ARG DEBIAN_FRONTEND=noninteractive

# The yml files in this directory are used to correctly install the three python
# virtual environments used in RaaS. For the raas env, the python packages are pip
# installed rather than described in the yml since they are not all able to be installed 
# through conda. The R script installs the necessary R packages. 
COPY *.yml ./
COPY r_dependencies.R .
COPY requirements.txt requirements.txt

# This variable specifices the system packages needed to be installed for RaaS
ENV BUILD_DEPS="build-essential libcurl4-gnutls-dev libxml2-dev libssl-dev libgit2-dev dirmngr" \
    APP_DEPS="curl libpq-dev python3-pip python3 wget apt-transport-https ca-certificates gnupg-agent software-properties-common"

# Install previously defined system libraries
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y ${BUILD_DEPS} ${APP_DEPS} --no-install-recommends 

# Install R (dirmngr is required for this process, so goes after previous bulk install)
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9  \
    && add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu focal-cran40/' \
    && apt update \
    && apt install -y r-base r-base-core r-recommended r-base-dev

# Install docker for containerizing scripts
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - \
    && add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable" \
   && apt-get update \
   && apt-get install docker-ce docker-ce-cli containerd.io -y

# Install miniconda and create virtual environments. We need two separate ones 
# for static analysis since python 3 code cannot analyze python 2 and vice versa.
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh \
    && conda env create -f raas-env.yml \
    && conda env create -f pylint2-env.yml \
    && conda env create -f pylint3-env.yml 

# RUN Commands executed after this will be within the raas virtual env
SHELL ["conda", "run", "--no-capture-output", "-n", "raas", "/bin/bash", "-c"]

# Install language packages
RUN pip install -r requirements.txt  \
&& Rscript r_dependencies.R


