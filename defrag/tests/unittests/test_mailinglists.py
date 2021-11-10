from defrag.modules.mailinglists import MailingLists
from defrag.routes import app

from fastapi.testclient import TestClient
import pytest
import asyncio

client = TestClient(app)

@pytest.mark.asyncio
async def test_worker():
    MailingLists.run_worker()
    await asyncio.sleep(10)
    assert any(len(list(v)) > 0 for v in MailingLists.feeds.values())
    MailingLists.feeds = {}
    MailingLists.bm_tokenized = None
    MailingLists.corpus = []


@pytest.mark.asyncio
async def test_feeds_index():
    await MailingLists.save_all_feeds()
    MailingLists.init_tokenize_corpus()
    assert any(len(list(v)) > 0 for v in MailingLists.feeds.values())


def test_get_feeds():
    response = client.get("/mailinglists?list_names=support,factory")
    assert response.status_code == 200
    print(response.text)


def test_search():
    response = client.get("/mailinglists/search?keywords=tickets")
    assert response.status_code == 200
    print(response.text)