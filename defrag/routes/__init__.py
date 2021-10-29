from defrag import app, routes
from defrag.modules import LOADED, discover_modules
import importlib

ALL_ROUTES = discover_modules(routes.__file__)

for module_name in (m for m in ALL_ROUTES if m in LOADED):
    imported_module = importlib.import_module("defrag.routes." + module_name)
    if hasattr(imported_module, "router"):
        app.include_router(imported_module.router)