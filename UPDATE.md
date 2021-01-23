# Updating an existing Sous-Chef installation

1. Stop Sous-Chef:

    ```
    systemctl stop souschef
    ```

2. Uninstall the Python package:

    ```
    python3 -m pip uninstall souschef
    ```

3. Clear remaining files in `dist-packages`:

    ```
    rm -rf /usr/local/lib/python3.7/dist-packages/souschef
    ```

    This step is to make sure assets removed from source code are also removed on the server. You may otherwise move the directory somewhere else if you want to be safe:

    ```
    mv /usr/local/lib/python3.7/dist-packages/souschef /tmp/souschef-old-installation
    ```

4. Install the latest Sous-Chef version:

    ```
    python3 -m pip install souschef
    ```

    or provide a specific version:

    ```
    python3 -m pip install souschef==1.x.x
    ```

5. Collect the static files and upgrade the database:

    ```bash
    cd /usr/local/lib/python3.7/dist-packages/souschef

    # Export the Sous-Chef configuration variables, so Django's
    # manage.py may work.
    for line in `cat /etc/souschef.conf`; do export $line; done

    # Collect the static files.
    python3 manage.py collectstatic --noinput

    # Migrate the database.
    # Needs to run as the root user and not as souschefdb.
    SOUSCHEF_DJANGO_DB_USER=root SOUSCHEF_DJANGO_DB_PASSWORD=...password... python3 manage.py migrate
    ```

6. Start Sous-Chef:

    ```
    systemctl start souschef
    ```
