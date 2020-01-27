# containr
A website that automatically rstudio docker images from user-uploaded directories containing R code.

Dependencies:
Listed in requirements.txt.
Run: pip install -r requirements.txt

run in Python 3.6.1 virtual environment using virtualenv. 

Additionally:
Uses, Celery, redis, and flask. 
Docker credentials set in environment variable. 
For development, a sqlite database locally. app.db in root folder.
Run celery worker at the same time as website. 

to start site: set FLASK_APP. flask run. 

TODO: visualizing probably can't handle multiple users rn.  
