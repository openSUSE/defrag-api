from typing import Any, Awaitable, Coroutine, Optional
from aiohttp import ClientSession
import asyncio

from aiohttp.client_reqrep import ClientResponse


class Req:

    session: Optional[ClientSession] = None

    @classmethod
    def get_session(cls) -> ClientSession:
        if not cls.session:
            cls.session = ClientSession()
        return cls.session

    def __init__(self, verb: str, url: str, closeOnResponse: bool = True) -> None:
        self.verb = verb
        self.url = url
        self.closeOnResponse = closeOnResponse
        self.session = self.get_session()

    async def __aenter__(self) -> Any:
        # Fix me: this is not an appropriate return type, but the library does not seem to expose the right type.
        if self.verb == "GET":
            return await self.session.get(self.url)

    async def __aexit__(self, *args, **kwargs) -> None:
        if self.closeOnResponse:
            await self.session.close()
