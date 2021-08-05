from defrag.modules.helpers.exceptions import NetworkException
from typing import Any, AnyStr, Dict, Optional
from aiohttp import ClientSession
import aiohttp


class Req:

    class ReqException(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    session: Optional[ClientSession] = None
    implemented_verbs = ["GET", "POST"]

    @classmethod
    def get_session(cls) -> ClientSession:
        if not cls.session or cls.session.closed:
            cls.session = ClientSession()
        return cls.session

    def __init__(self, url: str, json: Optional[Dict[AnyStr, AnyStr]] = None, closeOnResponse: bool = True) -> None:
        if json:
            self.json = json
        self.url = url
        self.closeOnResponse = closeOnResponse

    async def __aenter__(self) -> Any:
        # Fix me: this is not an appropriate return type, but the library does not seem to expose the right type.
        try:
            if self.json:
                return await self.session.post(self.url, json=self.json)
            return await self.session.get(self.url)
        except Exception as error:
            print(f"This error occurred while Requesting: {error}")

    async def __aexit__(self, *args, **kwargs) -> None:
        if self.closeOnResponse:
            await self.close_session()
