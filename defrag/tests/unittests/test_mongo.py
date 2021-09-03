
from defrag import app
from defrag.modules.db.mongo import client, drop_every_collection, drop_this_collection, save_as_docs, get_docs
from fastapi.testclient import TestClient
import asyncio

test_client = TestClient(app)

async def run_all_tests():
    collName = "events"
    async with await client.start_session() as s:
        await drop_this_collection(collName)
        await save_as_docs([{"id": n} for n in range(0, 3)], collName)
        docs = await get_docs(collName)
        assert len(docs) == 3
        await drop_this_collection(collName)
        docs = await get_docs(collName)
        assert len(docs) == 0


def test():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_all_tests())
