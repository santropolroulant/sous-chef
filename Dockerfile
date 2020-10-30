FROM python:3.7
ENV PYTHONUNBUFFERED 1

# Install underlying Debian dependencies
RUN apt-get update && \
  apt-get install curl gettext -y && \
  apt-get clean
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN apt-get install nodejs build-essential binutils libproj-dev gdal-bin -y && \
  apt-get clean

RUN mkdir /code
WORKDIR /code
COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

ENV DJANGO_SETTINGS_MODULE="souschef.sous_chef.settings"
CMD pip3 install -e . && \
  python3 souschef/manage.py collectstatic --noinput && \
  /usr/local/bin/gunicorn souschef.sous_chef.wsgi:application -w 2 -b :8000
