from typing import Any, List, Tuple

from pyrogram import Client, __version__
from pyrogram.types import Message


class Opengm(Client, Message):
    OWNER_ID: int = 0
    CHATS: List[int] = []

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

        self.admins = {chat: {Opengm.OWNER_ID} for chat in Opengm.CHATS}

    async def start(self) -> None:
        await super().start()

        me = await self.get_me()
        for chat, admins in self.admins.items():
            async for admin in self.iter_chat_members(chat, filter="administrators"):

                admins.add(admin.user.id)

    async def stop(self, *args: Tuple[Any]) -> None:
        await super().stop()

    def is_admin(self, message: Message) -> bool:
        user_id = message.from_user.id
        chat_id = message.chat.id
        return user_id in self.admins[chat_id]
