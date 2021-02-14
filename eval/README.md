# How to perform the evaluation

This readme describes the steps necessary to perform the RaaS evaluation. 
A python environment capable of running RaaS is necessary to execute these scripts. 

## Evaluating dataverse as-is without RaaS

Collect datasets first using the get_r_dois.py script. 
This script will collect all of the R scripts that exist on Harvard's Dataverse at the time you run the script. 
It will identify each dataset that the scripts belong to, find the unique doi for each one, and then write those dois to a file r_dois.txt.
To be clear: the dois returned by this script are for datasets NOT R scripts. 
Therefore number of lines in r_dois.txt == number of datasets to evaluate. 
The script will also print the number of R scripts found. 

Next run the eval_no_raas.py script. 
These results will be saved to a database results.db. 
This database needs to be created before the script is executed. 
The schema is described below.
This will download each dataset in batches determine by the variables start, end, and increment_by.
Once it completes downloading it will call a function to asynchronously run those datasets in a r-base 3.6.3 environment.
During this asynchronous execution it will begin to download the next batch. 
This script will collect any errors (if any) that occur when the R scripts are executed in the r-base environment. '

The schema is:
CREATE TABLE results (
ID INTEGER PRIMARY KEY NOT NULL,
filename TEXT NOT NULL,
error TEXT NOT NULL
);

