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

import logging
from typing import Any, Dict, List
from fastapi import FastAPI
from pydantic import BaseSettings
from functools import lru_cache
import configparser


class Settings(BaseSettings):
    """
    Automatically set by `python-dotenv` upon reading a ./.env file
    (if any)
    """
    admin_emails: List[str] = [
        "karatekhd@opensuse.org", "nycticorax@opensuse.org"]
    app_name: str = "defrag-api"
    app_port: str
    app_host: int
    bugzilla_user: str
    bugzilla_password: str
    mongo_pwd: str
    mongo_name: str
    profile_stats_output_dir: str
    redis_prod_test_host: str
    redis_prod_test_port: int
    redis_prod_test_pwd: str
    redis_host: str
    redis_port: int
    redis_pwd: str
    telegram_bot_token: str
    telegram_host: str
    telegram_path: str
    twitter_consumer_key: str
    twitter_consumer_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    redis_host: str
    redis_port: int
    redis_pwd: str

    class Config:
        env_file = ".env"

    @staticmethod
    @lru_cache()
    def get_settings() -> Dict[str, Any]:
        """
        Cached with lru_cache to avoid reading the disk multiple times.
        """
        if settings := Settings().dict():
            return settings
        else:
            config = configparser.ConfigParser()
            config.read("config.ini")
            return {
                "redis_host": config["REDIS"]["REDIS_HOST"],
                "redis_port": int(config["REDIS"]["REDIS_PORT"]),
                "redis_pwd": config["REDIS"]["REDIS_PWD"],
                "bugzilla_user": config["BUGZILLA"]["BUGZILLA_USER"],
                "bugzilla_password": config["BUGZILLA"]["BUGZILLA_PASSWORD"],
                "twitter_consumer_key": config["TWITTER"]["TWITTER_CONSUMER_KEY"],
                "twitter_consumer_secret": config["TWITTER"]["TWITTER_CONSUMER_SECRET"],
                "twitter_access_token": config["TWITTER"]["TWITTER_ACCESS_TOKEN"],
                "twitter_access_token_secret": config["TWITTER"]["TWITTER_ACCESS_TOKEN_SECRET"],
            }


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
# Initialize app
app = FastAPI(docs_url=None, redoc_url=None)
