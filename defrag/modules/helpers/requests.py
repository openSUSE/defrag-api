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
        if not cls.session:
            cls.session = ClientSession()
        return cls.session

    def __init__(self, url: str, verb: str = "GET", json: Optional[Dict[AnyStr, AnyStr]] = None, closeOnResponse: bool = True) -> None:
        if json:
            self.json = json
        self.verb = verb
        self.url = url
        self.closeOnResponse = closeOnResponse
        self.session = self.get_session()

    async def __aenter__(self) -> Any:
        # Fix me: this is not an appropriate return type, but the library does not seem to expose the right type.
        try:
            if not self.verb in self.implemented_verbs:
                raise self.ReqException(
                    f"This verb is not implemented {self.verb}")
            if self.verb == "GET":
                return await self.session.get(self.url)
            if self.verb == "POST":
                if not self.json:
                    raise self.ReqException(
                        f"POST-ing requires passing a json argument, as in `Req(ulr, verb='GET', json=...)`.")
                return await self.session.post(self.url, json=self.json)
        except aiohttp.ClientResponseError as exp:
            raise NetworkException(f"{exp.status}: {exp.message}")
        except aiohttp.ServerTimeoutError as exp:
            raise NetworkException("Timeout.")

    async def __aexit__(self, *args, **kwargs) -> None:
        if self.closeOnResponse:
            await self.session.close()
