import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="souschef",
    version="1.3.5",
    license="AGPL-3.0",
    author="Santropol Roulant and Savoir Faire Linux",
    author_email="info@santropolroulant.org",
    description="Webapp used to manage orders for meals-on-wheel delivery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sous-chef",
    packages=setuptools.find_packages(),
    include_package_data=True,
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
    keywords="meals-on-wheel",
    python_requires='>=3.7',
    install_requires=[
        'django-annoying>=0.10,<0.10.999',
        'django-avatar>=4.0,<4.0.999',
        'django-crontab>=0.7.1,<0.7.999',
        'django-extra-views>=0.9,<0.9.999',
        'django-filter>=1.0,<1.0.999',
        'django-formtools>=2.0,<2.0.999',
        'django-leaflet>=0.22,<0.22.999',
        'django-localflavor>=1.5,<1.5.999',
        'django-template-i18n-lint>=1.2,<1.2.999',
        'django>=1.11,<1.11.999',
        'factory_boy>=2.8,<2.8.999',
        'mysqlclient>=1.3,<1.3.999',
        'pylabels>=1.2,<1.2.999',
        'reportlab>=3.4,<3.4.999',
        'rules>=1.2,<1.2.999',
        'transifex-client>=0.12,<0.12.999',
    ],
)
