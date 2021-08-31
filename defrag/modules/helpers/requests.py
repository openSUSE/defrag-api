from typing import Any, AnyStr, Dict, Optional
from aiohttp import ClientSession


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

    @classmethod
    async def close_session(cls) -> None:
        if cls.session and not cls.session.closed:
            await cls.session.close()
            cls.session = None

    def __init__(self, url: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[AnyStr, AnyStr]] = None) -> None:
        self.json = json
        self.params = params
        self.url = url

    async def __aenter__(self) -> Any:
        if not self.json:
            return await self.get_session().get(self.url, params=self.params)
        else:
            return await self.get_session().post(self.url, json=self.json)

    async def __aexit__(self, *args, **kwargs) -> None:
        """ Closing session handler offloaded to __main__. """
        pass
