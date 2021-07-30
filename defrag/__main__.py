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

from datetime import datetime
from defrag.modules.news_reddit_twitter import RedditStoring, TwitterStoring
from defrag.modules.helpers.services_manager import Service, ServicesManager
from defrag.modules.helpers import GetQuery
from defrag.modules.helpers.cache import CacheMiddleWare, CacheStrategy, QueryResponse, RedisCacheStrategy, ServiceCacheStrategy
from typing import Dict
import uvicorn
import importlib
from defrag.modules import ALL_MODULES
from defrag import app, LOGGER, pretty_log

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
    now = datetime.now()
    twitter_redis = RedisCacheStrategy(
        "twitter", TwitterStoring.refresh, True, True, 300, None, None)
    twitter_cache_strat = CacheStrategy(None, twitter_redis, None)
    twitter = Service("twitter", True, ServiceCacheStrategy(
        [], twitter_cache_strat), now, None, None, None, None, None, None, None)
    reddit_redis = RedisCacheStrategy(
        "reddit", RedditStoring.refresh, True, True, 300, None, None)
    reddit_cache_strat = CacheStrategy(None, reddit_redis, None)
    reddit = Service("reddit", True, ServiceCacheStrategy(
        [], reddit_cache_strat), now, None, None, None, None, None, None, None)
    ServicesManager.register(twitter, reddit)


@app.get("/twitter", response_model=QueryResponse)
async def get_twitter():
    query = GetQuery(verb="GET", service="twitter")
    try:
        if cache_strategy := ServicesManager.get("twitter").cache_strategies.current.redis:
            return await CacheMiddleWare.run_query(query, cache_strategy)
        return QueryResponse(query=query, error="Unable to find a suitable cache strategy for the twitter service")
    except Exception as err:
        return QueryResponse(query=query, error=f"Was trying to meet your query when this error occurred: {err}")


@app.get("/reddit", response_model=QueryResponse)
async def get_reddit():
    query = GetQuery(verb="GET", service="reddit")
    try:
        if cache_strategy := ServicesManager.get("reddit").cache_strategies.current.redis:
            res = await CacheMiddleWare.run_query(query, cache_strategy)
            pretty_log("Finally", str(res))
            return QueryResponse(query=query, error="", result="")
        return QueryResponse(query=query, error="Unable to find a suitable cache strategy for the reddit service!")
    except Exception as err:
        return QueryResponse(query=query, error=f"Was trying to meet your query when this error occurred: {err}")


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Hello World"}


if __name__ == "__main__":
    main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
