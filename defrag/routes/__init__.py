from defrag import app
from defrag.routes import bugs, dispatcher, docs, organizer, docs, reddit, search, suggestions, twitter, wiki

app.include_router(bugs.router)
app.include_router(dispatcher.router)
app.include_router(docs.router)
app.include_router(organizer.router)
app.include_router(reddit.router)
app.include_router(search.router)
app.include_router(suggestions.router)
app.include_router(twitter.router)
app.include_router(wiki.router)


