from typing import Optional
from aiohttp import ClientSession


class Session:

    client: Optional[ClientSession] = None
    
    @classmethod
    async def close(cls) -> None:
        if cls.client and not cls.client.closed:
            await cls.client.close()
            cls.client = None

    def __new__(self) -> ClientSession:
        if not self.client or self.client.closed:
            self.client = ClientSession(trust_env=True)
        return self.client
    