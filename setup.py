from setuptools import find_packages, setup
from src.krakipy.version import __version__, __url__

def read(fname):
    with open(fname, "r") as f:
        text = f.read()
    return text

setup(name = "krakipy", 
    version = __version__,
    description = "A well-documented Python API for the Kraken Cryptocurrency Exchange", 
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_dir={"": "src"},
    keywords="kraken api crypto finance bitcoin tor mit",
    classifiers=[
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Utilities",
        "Topic :: Documentation :: Sphinx",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    install_requires=["pandas>=0.17.0", "requests", "pyotp", "torpy"],
    python_requires='>=3.3',
    url=__url__,
    project_urls={
        "Source": "https://github.com/Aionoso/Krakipy",
    },
    author="Hubertus Wilisch",
    author_email="aionoso-software@outlook.de",
    include_package_data=True,
    zip_safe=False,
    )