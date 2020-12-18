# Installing Sous-Chef for Developpement

## Editor Setup

To enforce some basic standards in the Sous-Chef source files we use an [EditorConfig](https://editorconfig.org/) configuration. You may find a plugin to your favorite source code editor [here](https://editorconfig.org/#download).

## Installing Docker

We suggest using Docker for developping Sous-Chef as it simplifies the setup a great deal.

### On Linux

Install the following dependencies:

1. **docker-engine**: https://docs.docker.com/engine/install/
2. **docker-compose**: https://docs.docker.com/compose/install/

On Debian systems, the following commands can be used to install Docker:

    sudo apt install docker-compose

### OS X

Install **Docker For Mac**: https://docs.docker.com/docker-for-mac/install/

### Windows

For Windows 10, it is recommended to use **Docker For Windows**: https://docs.docker.com/docker-for-windows/install/ (**notice**: Hyper-V must be enabled. Follow the instructions during installation.) Make sure that Docker icon appears in task tray and prompts "Docker is running". You can then use `cmd` or `PowerShell` to run the following commands.

For older Windows versions, you may have to use **Docker Toolbox** (https://www.docker.com/toolbox) and you must run commands from the **docker quickstart terminal** (a shortcut on desktop).

## Getting the source code

Clone the Sous-Chef repository:

```
git clone https://github.com/santropolroulant/sous-chef
cd sous-chef
```

## Building the assets

To build the assets, or rebuild them when the assets changes, run the following command:

```
./tools/compile_assets.sh
```

If you have issues with running this command it might be because you have run `npm` from your host machine to install the dependencies. Delete the `node_modules` directory and try again:

```
rm -rf tools/gulp/node_modules
```

[gulp](http://gulpjs.com/) is a JavasSript-based build system.
We use it to compile and optimize files from `souschef/frontend/` to `souschef/sous_chef/assets/`.
We specifically use it to compile SCSS to CSS, JavasSript to minified JavaScript, and images to further-compressed images.

## Building the Docker image and starting Sous-Chef

Running these commands will build the Docker image and start Sous-Chef:

```
docker-compose build
docker-compose up
```

Sous-Chef will then be accessible at [http://localhost:8000](http://localhost:8000). If this is the first time you run Sous-Chef, keep-on reading, as there are a few more steps required.

## Django initialization

Unfortunately, the bulk of the Django configuration cannot happen until the containers are already built
and running, because it needs to talk to the database which is in a different container, managed by docker-compose.
So after you do the first build, you need to manually do some more steps.

In your console:

```
docker-compose exec web bash
```

Then you should be inside a container as you can see, e.g., `root@d157a3f57426:/code#`. Then run:

```
cd souschef

# Run existing migrations
python3 manage.py migrate

# Create a user with administrator privileges
python3 manage.py createsuperuser

# Optional: Load the initial data set
python3 manage.py loaddata sample_data
```

## How to change the JavaScript code

You first need to know that Sous-Chef's JavaScript code placed in `souschef/frontend/js`. Be careful: the JavaScript files you will find in `souschef/sous_chef/assets/js` and `souschef/static/js` are (respectively) the result of running the `gulp` command and Django's copy of the assets, and are not part of the source code nor should be committed in Git. (As a reminder, the `gulp` command is ran when you execute the `./tools/compile_assets.sh` script, and the copy of the assets is made by the `manage.py collectstatic` command in the `Dockerfile`.)

So the proper and formal way to change the JavaScript code is the following:

1. Edit the JavaScript code in `souschef/frontend/js`.
2. Rebuild the assets by running:

    `./tools/compile_assets.sh`.

3. Copy the assets to Django's static directory by running:

    `docker-compose run web python3 /code/souschef/manage.py collectstatic --noinput`

4. Refresh your page. The new JavaScript files should be downloaded and executed by the browser.

## Troubleshooting

### Issues starting Sous-Chef

In case of persistent issues with starting Sous-Chef, try removing the Docker volume (which holds the database):

```
docker-compose down
docker volume rm sous-chef_souschef_data
docker-compose up --build
```

Then, redo the "Django initialization" step above.

Note: it happens that Sous-Chef cannot connect to the database, especially the first time you launch it. Simply stop the Docker processes with CTRL-C and relaunch `docker-compose up` to fix the issue.

### JavaScript served as minified file when developping

Sous-Chef will only serve non-minified JavaScript files when the IP address of the requester is listed in the INTERNAL_IPS variable in `souschef/sous_chef/settings.py`. The IPs listed in the configuration are already adjusted to using Docker Compose. If you are receiving a minified version of Sous-Chef's JavaScript code here's how to configure your development environment.

First, you need to figure-out the requester IP as seen by Django. In `souschef/page/views.py` add the following (don't commit this code though!):

```python
# Some code omitted
class HomeView:

    def get_context_data(self, **kwargs):
        # Add this print here
        print(f"REMOTE_ADDR is: {self.request.META.get('REMOTE_ADDR')}")
```

Then, refresh Sous-Chef's home page. In the logs (in the terminal where you started `docker-compose up`), you should see a message like this:

```
web_1  | REMOTE_ADDR is: 172.22.0.1
```

Add this IP to the INTERNAL_IPS variable in `souschef/sous_chef/settings.py`, but don't commit your changes.

## Connection to application

A Django development server is automatically started unless you have run with production settings. It is accessible at `http://localhost:8000`.

## Backup and restore database

The database content is stored in a Docker named volume that is not directly accessible.

**For backup**, running:

```
docker run --rm --volumes-from souschef_db_1 -v $(pwd):/backup ubuntu tar cvf /backup/backup.tar /var/lib/mysql
```

In Windows console, running:

```
docker run --rm --volumes-from souschef_db_1 -v %cd%:/backup ubuntu tar cvf /backup/backup.tar /var/lib/mysql
```

`souschef_db_1` is the container's name that can be found by running `docker ps`. This command creates a temporary Ubuntu container, connects it with both the volume that `souschef_db_1` uses and current directory on host machine. You will find `backup.tar` in current directory after this command.

**For restoring**:

```
docker run --rm --volumes-from souschef_db_1 -v $(pwd):/backup ubuntu bash -c "cd /var/lib/mysql && tar xvf /backup/backup.tar --strip 1"
```

In Windows console:

```
docker run --rm --volumes-from souschef_db_1 -v %cd%:/backup ubuntu bash -c "cd /var/lib/mysql && tar xvf /backup/backup.tar --strip 1"
```

Refs: https://docs.docker.com/engine/tutorials/dockervolumes/#backup-restore-or-migrate-data-volumes

## Troubleshooting

1. ```TERM environment not set```: https://github.com/dockerfile/mariadb/issues/3
2. ```listen tcp 0.0.0.0:8000: bind: address already in use```: another application already uses the 8000 port. Vagrant applications often use the same port for instance. Locate the application and shut it down, or select an other port.
3. ```Web server is up and running, but no answer after Django initialization```: restart your container.
4. ```Static files fails to load when using Nginx server in development mode (docker-compose up)```: run ```docker-compose exec web python3 souschef/manage.py collectstatic```
