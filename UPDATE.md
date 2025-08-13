# Updating an existing Sous-Chef installation

1. Stop Sous-Chef:

   ```
   systemctl stop souschef
   ```

2. Uninstall the Python package:

   ```
   pipx uninject --global gunicorn souschef
   ```

3. Clear remaining files in `dist-packages`. This step is to make sure assets removed from source code are also removed on the server.

   ```
   rm -rf /opt/pipx/venvs/gunicorn/lib/python3.11/site-packages/souschef
   ```

4. Install the latest Sous-Chef version:

   ```
   pipx inject --global gunicorn certifi souschef
   ```

   or provide a specific version:

   ```
   pipx inject --global gunicorn souschef==2.0.0dev4 --pip-args='--extra-index-url=https://test.pypi.org/simple/'
   ```

5. Collect the static files and upgrade the database:

   ```bash
   cd /opt/pipx/venvs/gunicorn/lib/python3.11/site-packages/souschef

   # Export the Sous-Chef configuration variables, so Django's
   # manage.py may work.
   for line in `cat /etc/souschef.conf`; do export $line; done

   # Collect the static files. To be done after installation and after each
   # version upgrade.
   /opt/pipx/venvs/gunicorn/bin/python manage.py collectstatic --noinput

   # Create the tables. When run after a version upgade it ensures the database
   # schema is up to date.
   # Database migration needs to run as the root user and not as souschefdb.
   # Note: the database password here is the one from the `mysql_secure_installation` step.
   env SOUSCHEF_DJANGO_DB_USER=root SOUSCHEF_DJANGO_DB_PASSWORD=...password... /opt/pipx/venvs/gunicorn/bin/python manage.py migrate
   ```

6. Start Sous-Chef:

   ```
   systemctl start souschef
   ```
