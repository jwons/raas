# Reproducibility as a Service (RaaS)
A website that automatically creates Docker images from user-uploaded directories containing a computational analysis. 
This service supports multiple languages including R, Python, and Julia (to varying degrees). 

For detailed set up instructions and other information visit the [wiki](https://github.com/jwons/raas/wiki).
For a detailed view into the architecture and evaluation of the system refer to my [master's thesis at the UBC Library](http://hdl.handle.net/2429/78501).

## Running RaaS with Docker (recommended)
Make sure to "install" RaaS first and set up the environment as specified in the [wiki](https://github.com/jwons/raas/wiki).
This should be a simple process of building the environment image first and initializing the RaaS database
in a persistent volume. 

Navigate to the raas directory in a terminal run 
```{bash}
docker-compose up --build
```

In your browser navigate to localhost:5000, and you are ready to start using RaaS!

For instructions on how to run RaaS locally from source code visit the [wiki](https://github.com/jwons/raas/wiki).

## Instructions for using RaaS

From the build image page users can upload a zip file. 
When choosing a name for the dataset, the name *must* be in all-lowercase. 

### Important Notes for Use

- Dataset names should be all-lowercase when uploaded. 
Docker will return an error if a name is not all lowercase that may not be clear to the user. 
- RaaS will attempt to determine and install all necessary language packages and system libraries. 
- However, it is not perfect and some may be missed, especially if a script is uploaded that never explicitly calls 'library' or 'import.'

### Headless Mode

Included currently in RaaS is a ''headless'' mode. 
This is a method of interfacing almost directly with the service from the command line. 
This should be used for __debugging and testing purposes only__ as it bypasses login information and allows someone to 
just provide a user ID as a parameter. 
It is also only available from within the host running the service. 
To use it, run the headless_raas.py script on the same machine a RaaS instance is running. 
Some dataset must be specificed, either zip or doi, and a dataset name. 
Optional parameters include port number for containR, whether to preprocess, and a user ID. 
For more information run `python headless_raas.py -h`.

__________________________________________________
### How to support another language?


There are 3 steps you need to follow to support a new language:


1.Create a new object that implement the ```language_interface```. Our standard style is to include a 
new directory in the ```app``` folder with the name ```language_*lang name*```, e.g. ```language_r```. 
The new object should go in a file in this directory, and any other files that might be needed
for *this language specifically*. 
The methods you would need to implement from the ```language_interface``` are 
  
     script_analysis

     build_docker_file
       
     create_report

The ```script_analysis``` function should return a ```StaticAnalysisResults``` object as defined
in the ```languageinterface.py``` script. It should have a list of language packages and list of 
system libraries to install. Anything else that might be needed when writing the dockerfile should 
be in the lang_specific variable. 

2.In the app/starter.py add an if condition to call your language object

3.In the app/forms.py add your language name to the front end selection box

If you are stuck and confused about any of these steps, check the existing implementations for R
and Python as a reference. 
