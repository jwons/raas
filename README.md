# containR
A website that automatically creates RStudio Docker images from user-uploaded directories containing R code.

For detailed set up instructions and other information visit the [wiki](https://github.com/jwons/containr/wiki).

## Running ContainR

Navigate to the containR directory in two terminals with the python virtual environment activated. 

In the first terminal run 
```{bash}
celery -A app.celery worker
```

In the second terminal run the following code. For more information on flask apps check out [their website](https://flask.palletsprojects.com/en/1.1.x/)
```{bash}
export FLASK_APP=containr.py

flask run
```

## Instructions for using containR

From the build image page it is possible to either upload a zip file *of a directory* or enter a Harvard Dataverse DOI which it will then try to scrape. When choosing a name for the dataset, the name *must* be in all-lowercase. 

## Important Notes about using containR

- Dataset names should be all-lowercase when uploaded. Docker Hub will return an error if a name is not all lowercase that may not be clear to the user. 
- While containR will install R packages that are necessary for a script to run, it cannot install external dependencies. For example if you install an R package that works as an interface for a specific type of database, but that type of database is not installed on the computer the script will not run correctly even if the package can install correctly.  
