import time
from functools import partial
from pyrogram import Client, filters
from pyrogram.types import Message
from opengm.opengm import Opengm

command = partial(filters.command, prefixes="/")

@Opengm.on_message(command("ping"))
async def ping(cl: Client, message: Message) -> None:
    start = time.time()
    reply = await message.reply_text("...")
    delta_ping = time.time() - start
    await reply.edit_text(f"**OpenSUSE Bot Test!** `{delta_ping * 1000:.3f} ms`")
