# How to package Sous-Chef

Stop your local development server:

```
docker-compose down
```

Remove the build directory to ensure a clean build (this is especially important when you made changes to setup.py or setup.cfg):

```
rm -rf build
```

Build the assets, as explained in [INSTALL.md](INSTALL.md):

```
./tools/compile_assets.sh
```

Then, use Docker to create the source package and the wheel archive:

```
docker-compose run web python3 setup.py sdist
docker-compose run web python3 setup.py bdist_wheel
```
