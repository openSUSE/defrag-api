import time
from pyrogram import Client
from pyrogram.types import Message
from opengm.opengm import Opengm, command
from opengm.utils.chat_status import user_admin
from opengm.utils.plugins import register_plugin
from opengm.utils.commands import get_args
from opengm.utils.extraction import extract_user_and_text 
register_plugin("Admin management", "This is a help text.")


@Opengm.on_message(command("extract"))
@user_admin
async def promote(bot: Client, msg: Message) -> None:
    args = get_args(msg)
    chat_id = msg.chat.id
    chat = msg.chat
    await msg.reply_text(await extract_user_and_text(msg))
