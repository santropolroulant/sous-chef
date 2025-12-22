# How to package Sous-Chef

1. Modify the version in `setup.py` and commit the changes. Development versions should have the following pattern:

   ```
   1.3.1.dev1
   ```

   Production versions should follow semantic versionning:

   ```
   1.3.1
   ```

2. Stop your local development server:

   ```
   docker compose down
   ```

3. Remove the `build` directory to ensure a clean build (this is especially important when you made changes to setup.py or setup.cfg). Also remove previous builds from `dist`:

   ```
   rm -rf build dist
   ```

4. Build the assets, as explained in [DEVSETUP.md](DEVSETUP.md):

   ```
   rm -rf souschef/sous_chef/assets/*
   ./tools/compile_assets.sh
   ```

5. Then, use Docker to create the source package and the wheel archive:

   ```
   docker compose run web python3 -m build
   ```

   The `dist` directory should now contain a .whl and .tar.gz file.

6. If you have a development version, upload it to test PyPI:

   ```
   twine upload -r testpypi dist/*
   ```

   For production:

   ```
   twine upload dist/*
   ```

   These commands will only work if you have proper permissions to upload to the PyPI souschef project.
