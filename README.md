# Reproducibility as a Service (RaaS)
A website that automatically creates Docker images from user-uploaded directories containing a computational analysis. This service supports multiple languages including R, Python, and Julia. 

For detailed set up instructions and other information visit the [wiki](https://github.com/jwons/raas/wiki).

## Running RaaS with Docker (recommended)
Make sure to install RaaS first and set up the environment as specified in the [wiki](https://github.com/jwons/raas/wiki).

Navigate to the raas directory in a terminal run 
```{bash}
docker-compose up --build
```

In your browser navigate to localhost:5000 and you are ready to start using RaaS!

For instructions on how to run RaaS locally from source code visit the wiki. 

## Instructions for using RaaS

From the build image page it is possible to either upload a zip file or enter a Harvard Dataverse DOI which it will then try to download. When choosing a name for the dataset, the name *must* be in all-lowercase. 

### Important Notes for Use

- Dataset names should be all-lowercase when uploaded. Docker will return an error if a name is not all lowercase that may not be clear to the user. 
- RaaS will attempt to determine and install all necessary language packages and system libraries. However, it is not perfect and some may be missed, especially if a script is uploaded that never explicitly calls 'library' or 'import.'

### Headless Mode

Included currently in RaaS is a ''headless'' mode. This is a method of interfacing almost directly with the service from the command line. Currently this should be used for __debugging purposes only__ as it bypasses login information and allows someone to just provide a user ID as a parameter. It is also only available from within the host running the service. To use it, run the headless_raas.py script on the same machine a RaaS instance is running. Some dataset must be specificed, either zip or doi, and a dataset name. Optional parameters include port number for containR, whether to preprocess, and a user ID. For more information run `python headless_raas.py -h`.

__________________________________________________
### How to support another language?


There are 3 steps you need to follow to support a new language:


1.Create a new object that implement the "language_interface".  
The method you would need to implement are 
  
     script_analysis

     build_docker_file
       
     create_report
     

2.In the app/starter.py add an if condition to call your language object


3.In the app/forms.py add your language name to the front end selection box
