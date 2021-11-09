from asyncio import sleep

from pyrogram import Client, filters
from pyrogram.errors.exceptions.forbidden_403 import MessageDeleteForbidden
from pyrogram.types import Message

from opengm.opengm import Opengm
from opengm.utils.chat_status import can_delete, user_admin
from opengm.utils.commands import get_args
from opengm.utils.plugins import register_plugin

HELP = """
- /purge [x]: Reply to a message to delete all messages sent after it. Takes an optional argument x to specify the number of messages to delete.
- /p [x]: Same as /purge
- /del: Similar to /purge but only deletes one message.
"""
register_plugin("Message deletion", HELP)


@Opengm.on_message(filters.command("del"))
@user_admin
async def delete_message(bot: Client, msg: Message):
    if msg.reply_to_message:
        if await can_delete(msg.chat, bot):
            await msg.delete()
            await msg.reply_to_message.delete()
        else:
            await msg.reply_text("I don't have delete rights!")
    else:
        await msg.reply_text("Whadya want to delete?")


@Opengm.on_message(filters.command(["purge", "p"]))
@user_admin
async def purge(bot: Client, msg: Message):
    args = get_args(msg)
    msg_src = msg.reply_to_message
    if not msg_src:
        await msg.reply_text("Reply to a message to select where to start purging from.")
        return
    if await can_delete(msg.chat, bot):
        message_id = msg.reply_to_message.message_id
        if args:
            try:
                # For some reason I need to substract 1
                number = int(args[0]) - 1
            except ValueError:
                msg.reply_text("You need to provide a valid number!")
                return
            delete_to = msg_src.message_id + number
        else:
            delete_to = msg.message_id - 1
        # Number thing
        msgs = []
        count = 0
        error = False
        for m_id in range(
                delete_to, message_id - 1, -1):  # Reverse iteration over message ids
            msgs.append(m_id)
            count = count + 1
            if len(msgs) == 100:
                try:
                    await bot.delete_messages(msg.chat.id, msgs)
                    msgs = []
                except MessageDeleteForbidden:
                    error = True
                    await bot.send_message(msg.chat.id, "Cannot delete all messages. The messages may be too old, I might not have delete rights, or this might not be a supergroup.")

        if msgs:
            try:
                await bot.delete_messages(msg.chat.id, msgs)
                await bot.delete_messages(msg.chat.id, msg.message_id)
            except MessageDeleteForbidden:
                error = True
                await bot.send_message(msg.chat.id, "Cannot delete all messages. The messages may be too old, I might not have delete rights, or this might not be a supergroup.")
            if not error:
                done = await bot.send_message(msg.chat.id, "Purge complete!\n\nPurged {} messages. **This auto-generated message shall be self destructed in 2 seconds.**".format(count))
                await sleep(2)
                await done.delete()
    else:
        await msg.reply_text("I don't have delete rights!")
