# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from fastapi import FastAPI
from dotenv import dotenv_values
import logging
import configparser

LOGGER = logging.getLogger(__name__)
# TODO: Change the logformat so that it fits uvicorn
LOGFORMAT = "[%(asctime)s | %(levelname)s] %(message)s"
DEBUG = True
if DEBUG:
    logging.basicConfig(
        format=LOGFORMAT,
        level=logging.DEBUG)
else:
    logging.basicConfig(
        format=LOGFORMAT,
        level=logging.INFO)

LOAD = []

config = dotenv_values(".env")

if not config:
    config = configparser.ConfigParser()
    config.read(["config.ini", "opengm.ini", "opensuse.ini"])
    REDIS_HOST = config["REDIS"]["REDIS_HOST"] 
    REDIS_PORT = int(config["REDIS"]["REDIS_PORT"])
    REDIS_PWD = config["REDIS"]["REDIS_PWD"]
    BUGZILLA_USER = config["BUGZILLA"]["BUGZILLA_USER"]
    BUGZILLA_PASSWORD = config["BUGZILLA"]["BUGZILLA_PASSWORD"]
    TWITTER_CONSUMER_KEY = config["TWITTER"]["TWITTER_CONSUMER_KEY"]
    TWITTER_CONSUMER_SECRET = config["TWITTER"]["TWITTER_CONSUMER_SECRET"]
    TWITTER_ACCESS_TOKEN = config["TWITTER"]["TWITTER_ACCESS_TOKEN"]
    TWITTER_ACCESS_TOKEN_SECRET = config["TWITTER"]["TWITTER_ACCESS_TOKEN_SECRET"]

# Initialize app
app = FastAPI(docs_url=None, redoc_url=None)

def run() -> None:
    pass
