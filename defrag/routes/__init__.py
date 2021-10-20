from defrag import app, routes
from defrag.modules import discover_modules
# from defrag.routes import bugs, dispatcher, docs, organizer, reddit, search, suggestions, twitter, wiki
import importlib

ALL_ROUTES = discover_modules(routes.__file__)

for module_name in ALL_ROUTES:
    imported_module = importlib.import_module("defrag.routes." + module_name)
    if hasattr(imported_module, "router"):
        app.include_router(imported_module.router)

"""
app.include_router(bugs.router)
app.include_router(dispatcher.router)
app.include_router(docs.router)
app.include_router(organizer.router)
app.include_router(reddit.router)
app.include_router(search.router)
app.include_router(suggestions.router)
app.include_router(twitter.router)
app.include_router(wiki.router)


"""