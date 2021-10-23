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

from typing import List
from defrag.modules.helpers.requests import Session
from defrag.modules.db.redis import RedisPool
from defrag import app, LOGGER
from defrag.modules import ALL_MODULES
from defrag.routes import *

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import uvicorn
import importlib


@app.on_event("startup")
async def register_modules_as_services(included: List[str] = ["search"]) -> None:
    """ Registers all modules implementing 'register_service() """
    
    # flushing cache
    with RedisPool() as conn:
        conn.flushall()
    
    # registering
    for module_name in (m for m in ALL_MODULES if m in included):
        imported_module = importlib.import_module("defrag.modules." + module_name)
        if hasattr(imported_module, "register_service"):
            imported_module.register_service()
            LOGGER.debug(f"Registered {module_name} as service.")
        

@app.on_event("shutdown")
async def close_session() -> None:
    await Session.close()


@app.get("/docs", include_in_schema=False)
def overridden_swagger():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="FastAPI", swagger_favicon_url="https://static.opensuse.org/favicon.svg")


@app.get("/redoc", include_in_schema=False)
def overridden_redoc():
    return get_redoc_html(openapi_url="/openapi.json", title="FastAPI", redoc_favicon_url="https://static.opensuse.org/favicon.svg")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
