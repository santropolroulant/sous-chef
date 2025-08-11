import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="souschef",
    version="2.0.0dev1",
    license="AGPL-3.0",
    author="Santropol Roulant and Savoir Faire Linux",
    author_email="info@santropolroulant.org",
    description="Webapp used to manage orders for meals-on-wheel delivery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/santropolroulant/sous-chef",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System",
    ],
    keywords="meals-on-wheel",
    python_requires=">=3.9",
    install_requires=[
        "django-annoying==0.10.6",
        "django-crontab==0.7.1",
        "django-extra-views==0.16.0",
        "django-filter==21.1",
        "django-formtools==2.3",
        "django-leaflet==0.28.3",
        "django-localflavor==3.1",
        "django==2.2.28",
        "factory_boy==3.2.1",
        "mysqlclient==2.1.1",
        "pypdf>=4.2,<5",
        "pylabels==1.2.1",
        "reportlab==3.6.13",
        "rules==3.3",
    ],
)
