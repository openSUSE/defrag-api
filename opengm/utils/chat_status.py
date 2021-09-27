from typing import Optional
from functools import wraps
from pyrogram import Client
from pyrogram.types import Chat, ChatMember, Message


async def is_user_admin(cl: Client, chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == 'private':
        return True

    if not member:
        member = await cl.get_chat_member(chat.id, user_id)
    return member.status in ('administrator', 'creator')


def user_admin(func):
    @wraps(func)
    async def is_admin(cl: Client, message: Message, *args, **kwargs):
        if message.chat.type == 'channel':
            return await func(cl, message, *args, **kwargs)
        user = message.from_user
        if not user:
            pass
        if await is_user_admin(cl, message.chat, user.id):
            return await func(cl, message, *args, **kwargs)
        else:
            await message.reply("Who dis non-admin telling me what to do?")

    return is_admin
