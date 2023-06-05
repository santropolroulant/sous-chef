# Installing Sous-Chef

These instructions document how to install Sous-Chef on Ubuntu 22.04.

To update an existing installation, see [UPDATE.md](UPDATE.md).

1. Install required dependencies

Become root, then install the dependencies.

```
sudo su -
apt install --no-install-recommends mariadb-server nginx libnginx-mod-http-fancyindex gdal-bin python3 \
    python3-pip libmariadb-dev-compat build-essential

# Install python 3.7 (old version)
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install --no-install-recommends python3.7 python3.7-distutils python3.7-dev
wget https://bootstrap.pypa.io/get-pip.py
python3.7 get-pip.py

# Invoke pip with 'python3 -m pip' to avoid a warning about a wrapper script
python3.7 -m pip install -U pip certifi
python3.7 -m pip install gunicorn
python3.7 -m pip install souschef

# PLEASE TEMPORARY USE THIS SPECIFIC VERSION
# todo: we need to update or create a pip-freeze
python3.7 -m pip install pytz==2022.7.1
```

To install a development version of Sous-Chef from the PyPI test index, run:
```
python3.7 -m pip install --extra-index-url https://test.pypi.org/simple/ souschef==1.3.0.dev2
```

2. Configure the database

Secure mariadb:

```
mysql_secure_installation
# When prompted for the current password for root, press the enter key (since no password is defined).
# Then answer yes to all questions (and provide asked information):
# -> Switch to unix_socket authentication -> Yes
# -> Change root password -> Yes
# -> Remove anonymous users -> Yes
# -> Disallow root login remotely -> Yes
# -> Remove test database and access to it -> Yes
# -> Reload privilege tables now -> Yes
```

Create the database and the souschef user.

```
mariadb -u root -p
MariaDB [(none)]> CREATE DATABASE souschefdb CHARACTER SET utf8;
MariaDB [(none)]> CREATE USER souschefuser@localhost IDENTIFIED BY '...strong password here...';
MariaDB [(none)]> GRANT ALL ON souschefdb.* TO souschefuser@localhost;
MariaDB [(none)]> FLUSH PRIVILEGES;
MariaDB [(none)]> quit
```

If you need to restore the Sous-Chef database from a backup, you can do so using the following command:
```
mysql -p souschefdb < backupfile.sql
```

3. Export environment varibles

These variables are required for the 'manage.py' script and for running the gunicorn server. Put them in the following file: `/etc/souschef.conf`

```
DJANGO_SETTINGS_MODULE=souschef.sous_chef.settings
SOUSCHEF_DJANGO_SECRET_KEY=...generate a random key here, at least 60 characters ...
SOUSCHEF_ENVIRONMENT_NAME=PROD
SOUSCHEF_DJANGO_ALLOWED_HOSTS=...servername.domain...
SOUSCHEF_DJANGO_DB_HOST=localhost
SOUSCHEF_DJANGO_DB_NAME=souschefdb
SOUSCHEF_DJANGO_DB_USER=souschefuser
SOUSCHEF_DJANGO_DB_PASSWORD=...password ...
SOUSCHEF_GENERATED_DOCS_DIR=/var/local/souschef
```

Note: `SOUSCHEF_DJANGO_ALLOWED_HOSTS` is a list of coma-separated public name(s) or IP(s) of the server hosting sous-chef.

3. Create required directories

Sous-Chef needs a writable directory to generate PDF documents.

```
mkdir /var/local/souschef
chown www-data:www-data /var/local/souschef
```

3. Initialize Sous-Chef

```bash
cd /usr/local/lib/python3.7/dist-packages/souschef

# Export the Sous-Chef configuration variables, so Django's
# manage.py may work.
for line in `cat /etc/souschef.conf`; do export $line; done

# Collect the static files. To be done after installation and after each
# version upgrade.
python3.7 manage.py collectstatic --noinput

# Create a user with administrator privileges.
# To be done once only.
python3.7 manage.py createsuperuser

# You will be asked to set a default git user, set your
# personal info or the one of your organization
```

4. Configure the nginx server

This server will serve the static files and redirect all other requests to the gunicorn backend.

Copy the content of [`souschef/configsamples/nginx.conf`](souschef/configsamples/nginx.conf) to `/etc/nginx/sites-available/souschef` and activate nginx:

```bash
cp /usr/local/lib/python3.7/dist-packages/souschef/configsamples/nginx.conf /etc/nginx/sites-available/souschef

# Remove the default site configuration, which is a symbolic link to `/etc/nginx/sites-available/default`
rm /etc/nginx/sites-enabled/default

# Enable souschef's configuration
ln -s /etc/nginx/sites-available/souschef /etc/nginx/sites-enabled/souschef
systemctl restart nginx
```

5. Create the Sous-Chef service

Put the content of [`souschef/configsamples/souschef.service`](souschef/configsamples/souschef.service) to `/lib/systemd/system/souschef.service`, then ask systemctl to read the new configuration:

```
cp /usr/local/lib/python3.7/dist-packages/souschef/configsamples/souschef.service /lib/systemd/system/souschef.service
systemctl daemon-reload
```

Also make sure Sous-Chef will start at boot:
```
systemctl enable souschef
```

Start the Sous-Chef gunicorn backend:

```
systemctl start souschef
systemctl status souschef
```

To view the logs:

```
journalctl -u souschef
```

Sous-Chef should now be accessible at the server's address!

6. Setup the Sous-Chef cron job

Sous-Chef needs a cron job to be executed daily in order to correcly process orders. In order to activate the cronjob, set the following symlink:

```
cd /etc/cron.daily
ln -s /usr/local/lib/python3.7/dist-packages/souschef/cronscripts/souschef_daily.sh souschef_daily
```

7. Managing souschef crons

To a add all crons configured in the settings of the souschef app:
```
python manage.py crontab add
```

To show all crons added by souschef:
```
python manage.py crontab show
```

To remove all crons added by souschef:
```
python manage.py crontab remove
```

## Debugging Sous-Chef

If you get an error 400 and need to debug Sous-Chef, you can set the following in `/etc/souschef.conf`:

```
SOUSCHEF_ENVIRONMENT_NAME=DEV
```

Then restart the service:

```
systemctl restart souschef
```

Django will then provide a detailed stack trace, enabling the debugging of the installation. Do not forget to turn off debugging once you fixed the issues as debugging creates a security risk and takes more memory.
