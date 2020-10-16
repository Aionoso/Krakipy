from setuptools import find_packages, setup
from src.krakipy.version import __version__

def read(fname):
    with open(fname, "r") as f:
        text = f.read()
    return text
      
setup(name = "krakipy", 
    version = __version__,
    description = "A Python REST-API for the Kraken exchange", 
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_dir={"": "src"},
    keywords="kraken api rest cryptocurrency broker finance",
    classifiers=[
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent"
    ],
    install_requires=["pandas", "requests"],
    python_requires='>=3.3',
    url="https://github.com/Aionoso/Krakipy",
    author="Hubertus Wilisch",
    author_email="aionoso-software@outlook.de",
    include_package_data=True,
    zip_safe=False,
    )