import asyncio
from typing import Any, Dict, List, Optional
from motor import motor_asyncio
from defrag import MONGO_PWD, MONGO_NAME

URI = f"mongodb+srv://defrag-api:{MONGO_PWD}@cluster0.fbqfu.mongodb.net/{MONGO_NAME}?retryWrites=true&w=majority"
client: motor_asyncio.AsyncIOMotorClient = motor_asyncio.AsyncIOMotorClient(
    URI)
db = client["defrag"]


async def save_as_docs(docs: List[Dict[str, Any]], collName: str) -> None:
    coll = db[collName]
    await coll.insert_many(docs)


async def get_docs(collName: str, query: Dict[str, Any] = {}, length: Optional[int] = None) -> List[Dict[str, Any]]:
    coll = db[collName]
    return await coll.find(query).to_list(length)


async def drop_this_collection(collName: str) -> None:
    coll = db[collName]
    await db.drop_collection(coll)


async def drop_every_collection() -> None:
    colls = await db.list_collection_names()
    await asyncio.gather(*[db.drop_collection(coll) for coll in colls])
    print("Dropped everything.")

    
    