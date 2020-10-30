import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="souschef",
    version="1.2dev",
    author="Santropol Roulant and Savoir Faire Linux",
    author_email="info@santropolroulant.org",
    description="Webapp used to manage orders for meals-on-wheel delivery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sous-chef",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta ",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System",
    ],
    python_requires='>=3.7',
)
