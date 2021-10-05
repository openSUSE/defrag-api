import os
from setuptools import setup

setup(
    name = "defrag-api",
    version = "0.1",
    author = "KaratekHD, why-not-try-calmer",
    author_email = "karatekhd@opensuse.org, nycticorax@opensuse.org",
    description = ("REST Api for the openSUSE infrastructure"),
    license = "GPL3",
    keywords = "openSUSE REST fastapi",
    url = "https://github.com/openSUSE/defrag-api",
    packages=['defrag', 'defrag.modules', 'defrag.profiling', 'defrag.tests', 'defrag.modules.helpers', 'defrag.modules.db', 'opengm', 'opengm.plugins'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
)

