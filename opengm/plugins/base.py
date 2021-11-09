import logging
import re

from pyrogram import Client, filters
from pyrogram.types import (CallbackQuery, ChatMemberUpdated,
                            InlineKeyboardButton, InlineKeyboardMarkup,
                            Message)

from opengm.opengm import Opengm, command
from opengm.utils.chat_status import admins, user_admin
from opengm.utils.commands import get_args
from opengm.utils.plugins import HELPABLE, HELPABLE_LOWER, paginate_plugins

# Do not register this plugin!

LOGGER = logging.getLogger(__name__)
HELPTEXT = """
Hey there! My name is {}.
I'm a modular group management bot with a few fun extras! Have a look at the following for an idea of some of the things I can help you with.

**Main** commands avaliable:
- /start: start the bot
- /help: PM's this message.
- /help <module name>: PM's you help for that module.
"""


def filter_admin_change_event(self, client, update):
    # If both of these atributes exist, a user's permission changed
    return update.old_chat_member and update.new_chat_member


admin_change_filter = filters.create(filter_admin_change_event)


# Help command. Links to PM when run in group and gives help when in PM
@Opengm.on_message(filters.command("help"))
async def help(cl: Client, message: Message) -> None:
    args = get_args(message)
    chat = message.chat
    if chat.type != "private":
        await message.reply("Contact me in PM to get the list of possible commands.",
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [InlineKeyboardButton(text="Help", url="t.me/{}?start=help".format((await cl.get_me()).username))]
                                ])
                            )
    else:
        if len(args) == 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=await paginate_plugins(0, HELPABLE, "help"))
            await message.reply(HELPTEXT.format("Test"), reply_markup=keyboard)
        elif args[0] in HELPABLE_LOWER:
            text = HELPTEXT + "\n\nAnd the following:\n" + \
                HELPABLE[HELPABLE_LOWER[args[0]]]
            await message.reply(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="All modules", callback_data="help_back")]]))
        else:
            await message.reply("There is no plugin with that name.")


# Handle button press in help view
@Opengm.on_callback_query(filters.regex(r"help_*"))
async def help_button_callback(cl: Client, query: CallbackQuery) -> None:
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    if mod_match:
        module = mod_match.group(1)
        text = HELPTEXT + "\n\nAnd the following:\n" + HELPABLE[module]
        await query.message.reply(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]))
    elif back_match:
        await query.message.reply(HELPTEXT.format("Test"), reply_markup=InlineKeyboardMarkup(inline_keyboard=await paginate_plugins(0, HELPABLE, "help")))
    elif prev_match:
        curr_page = int(prev_match.group(1))
        await query.message.reply(HELPTEXT, reply_markup=InlineKeyboardMarkup(paginate_modules(curr_page - 1, HELPABLE, "help")))
    elif next_match:
        next_page = int(next_match.group(1))
        await query.message.reply(HELPTEXT, reply_markup=InlineKeyboardMarkup(paginate_modules(next_page + 1, HELPABLE, "help")))
    await query.answer()

# Put a list of all admins in a chat to Redis


async def reload_admins(chat_id: int, bot: Client):
    list = []
    async for i in bot.iter_chat_members(chat_id, filter="administrators"):
        list.append(i.user.id)
    admins[chat_id] = list
    LOGGER.debug(f"Reloaded admin list for {chat_id}")

# Command to run reload_admins from a chat


@Opengm.on_message(filters.command("reload") & filters.group)
async def manually_reload_admins(bot: Client, message: Message):
    chat = message.chat
    member = await bot.get_chat_member(chat.id, message.from_user.id)
    if member.status not in ('administrator', 'creator'):
        await message.reply_text("You need to be an admin to do this!")
        return
    await reload_admins(chat.id, bot)
    await message.reply_text("Admins have been updated.")


# Automatically reload admins when a user's permission changed
@Opengm.on_chat_member_updated(filters.group & admin_change_filter)
async def auto_reload_admins(bot: Client, update: ChatMemberUpdated):
    if not hasattr(update, "old_chat_member"):
        return
    chat = update.chat
    if chat.id in admins:
        alist = admins[update.chat.id]
    else:
        alist = []
    if update.new_chat_member.status in (
        'administrator',
        'creator') and update.old_chat_member.status not in (
        'administrator',
            'creator'):
        if update.new_chat_member.user.id not in alist:
            alist.append(update.new_chat_member.user.id)
        LOGGER.info(
            f"Added {update.new_chat_member.user.id} to the admin store in {chat.id}")
    elif update.new_chat_member.status not in ('administrator', 'creator') and update.old_chat_member.status in ('administrator', 'creator'):
        alist.remove(update.new_chat_member.user.id)
        LOGGER.debug(
            f"Removed {update.new_chat_member.user.id} from the admin store in {chat.id}")
    admins[chat.id] = alist
    pass


@Opengm.on_message(filters.group & filters.new_chat_members)
async def bot_added_to_group(bot: Client, update: ChatMemberUpdated):
    LOGGER.info(f"Bot got added to {update.chat.id}")
    await reload_admins(update.chat.id, bot)


# Helps debugging
@Opengm.on_message(filters.group & filters.command("admins"))
async def list_admins(bot: Client, msg: Message):
    chat = msg.chat
    if chat.id in admins:
        alist = admins[chat.id]
        reply = f"List of Admins in {chat.title}:\n"
        for admin in alist:
            reply = reply + f" - {(await bot.get_chat_member(chat.id, admin)).user.mention}\n"
        await msg.reply_text(reply)
    else:
        await msg.reply_text("There are no admins in this chat, this can't be right... Please do /reload!")
