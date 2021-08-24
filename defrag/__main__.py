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
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from defrag import app, LOGGER
from defrag.modules import ALL_MODULES

IMPORTED = {}

<<<<<<< HEAD
=======

def main():
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


@app.get("/")
async def root():
    return {"message": "Hello World"}
>>>>>>> ec2bf616fed091c17a6e8b1c3c91b089e038ffe2

def main() -> None:
    for module_name in ALL_MODULES:
        imported_module = importlib.import_module(
            "defrag.modules." + module_name)
        if not hasattr(imported_module, "__MOD_NAME__"):
            imported_module.__MOD_NAME__ = imported_module.__name__
        LOGGER.debug("Loaded Module {}".format(imported_module.__MOD_NAME__))
        if not imported_module.__MOD_NAME__.lower() in IMPORTED:
            IMPORTED[imported_module.__MOD_NAME__.lower()] = imported_module
        else:
            # NO_TWO_MODULES
            raise Exception(
                "Can't have two modules with the same name! Please change one")


@app.on_event("startup")
async def register_modules_as_services() -> None:
    """ Registers all modules implementing 'register_service()'. """
    with RedisPool() as conn:
        conn.flushall()
    for service in IMPORTED.values():
        if hasattr(service, "register_service"):
            service.register_service()

<<<<<<< HEAD

@app.get("/docs", include_in_schema=False)
def overridden_swagger():
	return get_swagger_ui_html(openapi_url="/openapi.json", title="FastAPI", swagger_favicon_url="https://static.opensuse.org/favicon.svg")

@app.get("/redoc", include_in_schema=False)
def overridden_redoc():
	return get_redoc_html(openapi_url="/openapi.json", title="FastAPI", redoc_favicon_url="https://static.opensuse.org/favicon.svg")


=======
>>>>>>> ec2bf616fed091c17a6e8b1c3c91b089e038ffe2
if __name__ == "__main__":
    main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
