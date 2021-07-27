from typing import Optional
from aiohttp import ClientSession
import asyncio


class Req:

    session: Optional[ClientSession] = None

    @classmethod
    def get_session(cls):
        if not cls.session:
            cls.session = ClientSession()
        return cls.session

    def __init__(self, verb: str, url: str, closeOnResponse: bool = True):
        self.verb = verb
        self.url = url
        self.closeOnResponse = closeOnResponse
        self.session = self.get_session()

    async def __aenter__(self):
        if self.verb == "GET":
            return await self.session.get(self.url)

    async def __aexit__(self, *args, **kwargs):
        if self.closeOnResponse:
            await self.session.close()