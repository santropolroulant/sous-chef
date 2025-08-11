import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="souschef",
    version="2.0.0dev2",
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
        "django-filter==23.5",
        "django-formtools==2.5.1",
        "django-leaflet==0.29.1",
        "django-localflavor==4.0",
        "django==3.2.25",
        "factory_boy==3.3.0",
        "mysqlclient==2.2.4",
        "pypdf>=4.2,<5",
        "pylabels==1.2.1",
        "reportlab==4.1.0",
        "rules==3.3",
    ],
)
