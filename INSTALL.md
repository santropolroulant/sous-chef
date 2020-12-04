# Installing Sous-Chef

These instructions document how to install Sous-Chef on Debian 10.

1. Install required dependencies

Become root, then install the dependencies.

```
apt install mariadb-server nginx gdal-bin python3 python3-pip libmariadb-dev-compat
# Invoke pip with 'python3 -m pip' to avoid a warning about a wrapper script
python3 -m pip install -U pip
python3 -m pip install gunicorn
python3 -m pip install souschef
```

To install a development version of Sous-Chef from the PyPI test index, run:
```
python3 -m pip install --extra-index-url https://test.pypi.org/simple/ souschef==1.3.0.dev2
```

2. Configure the database

Secure mariadb:

```
mysql_secure_installation
# When prompted for the current password for root, press the enter key (since no password is defined).
# Then answer yes to all questions (and provide asked information):
# -> Set root password
# -> Remove anonymous users
# -> Disallow root login remotely
# -> Remove test database and access to it
# -> Reload privilege tables now
```

Create the database and the souschef user.

```
mariadb -u root -p
MariaDB [(none)]> CREATE DATABASE souschefdb CHARACTER SET utf8;
MariaDB [(none)]> CREATE USER souschefuser@localhost IDENTIFIED BY '...strong password here...';
MariaDB [(none)]> GRANT SELECT, INSERT, UPDATE, DELETE ON souschefdb.* TO souschefuser@localhost;
MariaDB [(none)]> FLUSH PRIVILEGES;
MariaDB [(none)]> quit
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

```
cd /usr/local/lib/python3.7/dist-packages/souschef

# Export the Sous-Chef configuration variables, so Django's
# manage.py may work.
for line in `cat /etc/souschef.conf`; do export $line; done

# Collect the static files. To be done after installation and after each
# version upgrade.
python3 manage.py collectstatic --noinput

# Create the tables. When run after a version upgade it ensures the database
# schema is up to date.
# Database migration needs to run as the root user and not as souschefdb.
export SOUSCHEF_DJANGO_DB_USER=root
export SOUSCHEF_DJANGO_DB_PASSWORD=...password...
python3 manage.py migrate

# Create a user with administrator privileges.
# To be done once only.
python3 manage.py createsuperuser
```

4. Configure the nginx server

This server will serve the static files and redirect all other requests to the gunicorn backend.

First copy the content of [`configsamples/nginx.conf`](configsamples/nginx.conf) to `/etc/nginx/sites-available/souschef`, then:

```
# Remove the default site configuration, which is a symbolic link to `/etc/nginx/sites-available/default`
rm /etc/nginx/sites-enabled/default
# Enable souschef's configuration
ln -s /etc/nginx/sites-available/souschef /etc/nginx/sites-enabled/souschef
systemctl restart nginx
```

5. Create the Sous-Chef service

Put the content of [`configsamples/souschef.service`](configsamples/souschef.service) in `/etc/systemd/system/souschef.service`, then ask systemctl to read the new configuration:

```
systemctl daemon-reload
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

## Debugging Sous-Chef

If you get an error 400 and need to debug Sous-Chef, you can set the following in `/etc/souschef.conf`:

```
SOUSCHEF_ENVIRONMENT_NAME=DEV
```

Then restart the service:

```
systemctl start souschef
```

Django will then provide a detailed stack trace, enabling the debugging of the installation. Do not forget to turn off debugging once you fixed the issues as debugging creates a security risk and takes more memory.
