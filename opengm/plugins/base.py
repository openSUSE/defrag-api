import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, InlineKeyboardButton
from opengm.opengm import Opengm, command
from opengm.utils.chat_status import user_admin, admins
from opengm.utils.plugins import HELPABLE, HELPABLE_LOWER, paginate_plugins
from opengm.utils.commands import get_args

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


@Opengm.on_message(filters.command("help"))
async def help(cl: Client, message: Message) -> None:
    args = get_args(message)
    chat = message.chat
    if chat.type != "private":
        await message.reply("Contact me in PM to get the list of possible commands.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Help", url="t.me/{}?start=help".format((await cl.get_me()).username))]]))
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


@Opengm.on_message(filters.command("reload") & filters.group)
async def reload_admins(bot: Client, message: Message):
    # if not message.chat.id in admins:
    #    admins[message.chat.id] = []
    chat = message.chat
    member = await bot.get_chat_member(chat.id, message.from_user.id)
    if member.status not in ('administrator', 'creator'):
        await message.reply_text("You need to be an admin to do this!")
        return
    list = []
    async for i in bot.iter_chat_members(message.chat.id, filter="administrators"):
        list.append(i.user.id)
    admins[message.chat.id] = list
    print(admins[message.chat.id])
