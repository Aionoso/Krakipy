from setuptools import find_packages, setup
from src.krakipy.version import __version__, __url__

def read(fname):
    with open(fname, "r") as f:
        text = f.read()
    return text

setup(name = "krakipy", 
    version = __version__,
    description = "Complete API To The Kraken Crypto Exchange (NEW Staking Methods)", 
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_dir={"": "src"},
    keywords="kraken api crypto finance bitcoin tor",
    classifiers=[
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Utilities",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent"
    ],
    install_requires=["pandas", "requests", "pyotp", "torpy"],
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
