from typing import Optional
from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from opengm import redis
from pottery import RedisDict

admins = RedisDict({}, redis=redis, key="chat_admins")
# {chat_id: [user_id, user_id]}


def user_admin(func):
    @wraps(func)
    async def is_admin(cl: Client, message: Message, *args, **kwargs):
        if message.chat.type in ('channel', 'private'):
            return await func(cl, message, *args, **kwargs)
        user = message.from_user
        if not user:
            pass
        if user.id in admins[message.chat.id]:
            return await func(cl, message, *args, **kwargs)
        else:
            await message.reply("Who dis non-admin telling me what to do?")
    return is_admin
