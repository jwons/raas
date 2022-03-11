# This Dockerfile is the second of two. The first, which this pulls from, creates
# the environment in the container necessary to run raas. Since that process takes
# a while and is largely static, it is a separate build. This file will simply load
# in the current version of the code and start the service. 
FROM raas-env

WORKDIR /raas

# RUN Commands executed after this will be within the raas virtual env
# This is needed since all our python packages used for raas are in that env
SHELL ["conda", "run", "--no-capture-output", "-n", "raas", "/bin/bash", "-c"]

# Copy over all the source code (minus what is in the .dockerignore)
COPY . .

# Information for flask and raas execution. They are declared here and not
# in the docker-compose.yml because multiple containers use them, and this
# way they can be declared only once. 
ARG FLASK_ENV="development"
ENV FLASK_ENV="${FLASK_ENV}" \
    PYTHONUNBUFFERED="true"

ENV FLASK_APP="raas.py"

# We will be exposing port 5000, the actual command to do this is in the docker-compose
EXPOSE 5000

# When running flask make sure to do it from the correct env, 
# as the SHELL command does not apply here
CMD ["conda", "run", "--no-capture-output", "-n", "raas", "/bin/bash", "-c", "flask run --host 0.0.0.0"]
