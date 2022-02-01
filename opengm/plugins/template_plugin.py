import time

from pyrogram import Client
from pyrogram.types import Message

from opengm.opengm import Opengm, command
from opengm.utils.chat_status import user_admin
from opengm.utils.plugins import register_plugin

register_plugin("Template", "This is a help text.")


@Opengm.on_message(command("ping"))
@user_admin
async def ping(cl: Client, message: Message) -> None:
    start = time.time()
    reply = await message.reply_text("...")
    delta_ping = time.time() - start
    await reply.edit_text(f"**openSUSE Bot Test!** `{delta_ping * 1000:.3f} ms`")
