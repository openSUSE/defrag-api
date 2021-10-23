from defrag import app, routes
from defrag.modules import discover_modules
import importlib

ALL_ROUTES = discover_modules(routes.__file__)

for module_name in ALL_ROUTES:
    imported_module = importlib.import_module("defrag.routes." + module_name)
    if hasattr(imported_module, "router"):
        app.include_router(imported_module.router)