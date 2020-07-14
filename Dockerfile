FROM python:3.6-alpine
LABEL maintainer="gilboa.nir@gmail.com"

EXPOSE 8000

# The enviroment variable ensures that the python output is set straight
# to the terminal with out buffering it first
ENV PYTHONUNBUFFERED 1

RUN apk add build-base
RUN apk add --no-cache bash
RUN apk add --no-cache git

# create root directory for our project in the container
RUN mkdir /app
RUN chmod 777 /app

# Copy the current directory contents into the container at /app
ADD . /app/

# Set the working directory to /app
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install -e .  --force-reinstall
RUN pip install gunicorn==20.0

