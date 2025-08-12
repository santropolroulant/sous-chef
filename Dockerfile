FROM --platform=linux/amd64 python:3.11
ENV PYTHONUNBUFFERED 1

# Install underlying Debian dependencies
RUN apt-get update && \
  apt-get install curl gettext cron -y && \
  apt-get clean
RUN apt-get install nodejs build-essential binutils libproj-dev gdal-bin -y && \
  apt-get clean

# pyinotify is a development requirement to help with Django's runserver command.
RUN pip3 install --no-cache-dir pyinotify

RUN mkdir /code
WORKDIR /code

# We copy the strict minimum from the source code into the image so we can
# install the requirements and have that step cached by Docker.
COPY setup.py README.md /code/
RUN pip3 install -e .

# We add some development tool to make sure that contributors only need
# docker installed
COPY requirements-dev.txt /code/
RUN pip3 install -r requirements-dev.txt

# Add wait-for-it script for CI
# This script allow us to wait that DB is up&running before launching tests
COPY wait-for-it.sh /code/

ENV DJANGO_SETTINGS_MODULE="souschef.sous_chef.settings"
ENV SOUSCHEF_ENVIRONMENT_NAME="DEV"
CMD pip3 install -e . && \
  python3 souschef/manage.py collectstatic --noinput && \
  python3 souschef/manage.py runserver 0.0.0.0:8000
