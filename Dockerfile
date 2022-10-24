FROM python:3.7
ENV PYTHONUNBUFFERED 1

# Install underlying Debian dependencies
RUN apt-get update && \
  apt-get install curl gettext cron -y && \
  apt-get clean
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
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

ENV DJANGO_SETTINGS_MODULE="souschef.sous_chef.settings"
ENV SOUSCHEF_ENVIRONMENT_NAME="DEV"
CMD pip3 install -e . && \
  python3 souschef/manage.py collectstatic --noinput && \
  python3 souschef/manage.py runserver 0.0.0.0:8000
