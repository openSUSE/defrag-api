from defrag.routes.obs_packages import api_search
import pytest

@pytest.mark.asyncio
async def test_simple():
    response = await api_search("chess", "tumbleweed")
    print(response)

@pytest.mark.asyncio
async def test_home_repos():
    response = await api_search("spotify-qt", "tumbleweed", home_repos=True)
    print(response)
