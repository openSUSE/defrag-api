from typing import Optional
from functools import wraps
from pyrogram import Client
from pyrogram.types import Message, Chat
from opengm import redis
from pottery import RedisDict
#from opengm.plugins.base import reload_admins
admins = RedisDict({}, redis=redis, key="chat_admins")
# {chat_id: [user_id, user_id]}

async def can_delete(chat: Chat, bot: Client) -> bool:
    return (await bot.get_chat_member(chat.id, (await bot.get_me()).id)).can_delete_messages

def user_admin(func):
    @wraps(func)
    async def is_admin(cl: Client, message: Message, *args, **kwargs):
        if message.chat.type in ('channel', 'private'):
            return await func(cl, message, *args, **kwargs)
        user = message.from_user
        if not user:
            pass
        #if not message.chat.id in admins:
        #    await reload_admins(message.chat.id, cl) 
        if user.id in admins[message.chat.id]:
            return await func(cl, message, *args, **kwargs)
        else:
            await message.reply("Who dis non-admin telling me what to do?")
    return is_admin
