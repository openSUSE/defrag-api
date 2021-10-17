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

from defrag.modules.helpers.requests import Req
from defrag.modules.db.redis import RedisPool
from defrag import app, LOGGER
from defrag.modules import ALL_MODULES

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import uvicorn
import importlib


to_register = {}

def main() -> None:
    for module_name in ALL_MODULES:
        imported_module = importlib.import_module(
            "defrag.modules." + module_name)
        if not hasattr(imported_module, "__MOD_NAME__"):
            imported_module.__MOD_NAME__ = imported_module.__name__
        LOGGER.debug("Loaded Module {}".format(imported_module.__MOD_NAME__))
        if not imported_module.__MOD_NAME__.lower() in to_register:
            to_register[imported_module.__MOD_NAME__.lower()] = imported_module
        else:
            # NO_TWO_MODULES
            raise Exception(
                "Can't have two modules with the same name! Please change one")


@app.on_event("startup")
async def register_modules_as_services() -> None:
    """
    Registers all modules implementing 'register_service()
    """
    with RedisPool() as conn:
        conn.flushall()
    for service in to_register.values():
        if hasattr(service, "register_service"):
            service.register_service()


@app.on_event("shutdown")
async def close_session() -> None:
    await Req.close_session()


@app.get("/docs", include_in_schema=False)
def overridden_swagger():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="FastAPI", swagger_favicon_url="https://static.opensuse.org/favicon.svg")


@app.get("/redoc", include_in_schema=False)
def overridden_redoc():
    return get_redoc_html(openapi_url="/openapi.json", title="FastAPI", redoc_favicon_url="https://static.opensuse.org/favicon.svg")


if __name__ == "__main__":
    main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
