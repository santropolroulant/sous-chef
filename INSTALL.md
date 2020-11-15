# Installing Sous-Chef

These instructions document how to install Sous-Chef on Debian 10.

1. Install required dependencies

```
apt install mariadb-server nginx gdal-bin python3 python3-pip libmariadb-dev-compat
# Invoke pip with 'python3 -m pip' to avoid a warning about a wrapper script
python3 -m pip install -U pip
python3 -m pip install souschef gunicorn
```

2. Configure the database

```
mysql_secure_installation
mariadb -u root -p <<< "CREATE DATABASE souschefdb CHARACTER SET utf8;"
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
```

Note: `SOUSCHEF_DJANGO_ALLOWED_HOSTS` is a list of coma-separated public name(s) or IP(s) of the server hosting sous-chef.

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
python3 manage.py migrate

# Create a user with administrator privileges.
# To be done once only.
python3 manage.py createsuperuser

# Optional: for testing Sous-Chef, you may want to load
# some fixture data.
python3 manage.py loaddata sample_data
```

4. Configure the nginx server

This server will serve the static files and redirect all other requests to the gunicorn backend.

First copy the content of [sampleconfig/nginx.conf](sampleconfig/nginx.conf) to `/etc/nginx/sites-available/souschef`, then:

```
# Remove the default site configuration, which is a symbolic link to `/etc/nginx/sites-available/default`
rm /etc/nginx/sites-enabled/default
# Enable souschef's configuration
ln -s /etc/nginx/sites-available/souschef /etc/nginx/sites-enabled/souschef
systemctl restart nginx
```

5. Create the Sous-Chef service

Put the following in `/etc/systemd/system/souschef.service`:

```
[Unit]
Description=Sous-Chef gunicorn backend
Documentation=https://github.com/santropolroulant/sous-chef
After=network.target
Wants=mariadb.service

[Install]
WantedBy=multi-user.target
Alias=souschef.service

[Service]
Type=simple
User=www-data
Group=www-data
EnvironmentFile=/etc/souschef.conf
ExecStart=/usr/local/bin/gunicorn souschef.sous_chef.wsgi:application -w 4 -b :8000
KillSignal=SIGTERM
```

Ask systemctl to read the new configuration:

```
systemctl daemon-reload
```

Then start the Sous-Chef gunicorn backend:

```
systemctl start souschef
systemctl status souschef
```

To view the logs:

```
journalctl -u souschef
```

Sous-Chef should now be accessible at the server's address!
