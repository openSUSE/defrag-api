from functools import partial
from typing import Any, List, Tuple

from pyrogram import Client, __version__, filters
from pyrogram.types import Message
from functools import partial
from opengm.plugins.sql import get_objects, create

command = partial(filters.command, prefixes="/")


class Opengm(Client, Message):
    OWNER_ID: int = 0
    CHATS: List[int] = []
    BASE = None
    SESSION = None
    engine = None
    def __init__(self) -> None:
        name = self.__class__.__name__.lower()
        print(name)
        super().__init__(
            session_name=name,
            config_file=f"{name}.ini",
            workers=4,
            plugins=dict(root=f"{name}/plugins"),
            workdir=".",
        )

    async def start(self) -> None:
        await super().start()
        BASE, SESSION, engine = get_objects()
        await create(engine)
        from opengm.plugins.sql.users import ensure_bot_in_db
        me = await self.get_me()
        await ensure_bot_in_db(me.id, me.username)

    async def stop(self, *args: Tuple[Any]) -> None:
        await super().stop()
