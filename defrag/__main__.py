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

from defrag.modules.db.redis import RedisPool
import uvicorn
import importlib
from defrag import app, LOGGER, pretty_log
from defrag.modules import ALL_MODULES
from defrag.modules.helpers import Query
from defrag.modules.helpers.caching import CacheStrategy, RedisCacheStrategy
from defrag.modules.helpers.services_manager import Run, ServiceTemplate, ServicesManager

IMPORTED = {}


def main() -> None:
    for module_name in ALL_MODULES:
        imported_module = importlib.import_module(
            "defrag.modules." + module_name)
        if not hasattr(imported_module, "__mod_name__"):
            imported_module.__mod_name__ = imported_module.__name__
        LOGGER.debug("Loaded Module {}".format(imported_module.__mod_name__))
        if not imported_module.__mod_name__.lower() in IMPORTED:
            IMPORTED[imported_module.__mod_name__.lower()] = imported_module
        else:
            # NO_TWO_MODULES
            raise Exception(
                "Can't have two modules with the same name! Please change one")


@app.on_event("startup")
async def startup() -> None:
    with RedisPool() as conn:
        conn.flushall()
    reddit_strategy = CacheStrategy(RedisCacheStrategy(
        "reddit_default", True, True, 300, None, None), None)
    twitter_strategy = CacheStrategy(RedisCacheStrategy(
        "twitter_default", True, True, 300, None, None), None)
    reddit = ServiceTemplate("reddit", reddit_strategy, None, None, None, None)
    twitter = ServiceTemplate(
        "twitter", twitter_strategy, None, None, None, None)
    ServicesManager.initialize(twitter, reddit)
    pretty_log("Finished startup with services",
               str(ServicesManager.services.list_all()))


@app.get("/twitter")
async def get_twitter():
    return await Run.query(Query(service="twitter"))


@app.get("/reddit")
async def get_reddit():
    return await Run.query(Query(service="reddit"))


if __name__ == "__main__":
    main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
