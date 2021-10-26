import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery, InlineKeyboardButton, ChatMemberUpdated
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

def filter_admin_change_event(self, client, update):
    print(hasattr(update, "old_chat_member"))
    print(hasattr(update, "new_chat_member"))
    return bool(update.old_chat_member) & bool(update.new_chat_member)

admin_change_filter = filters.create(filter_admin_change_event)
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
async def manually_reload_admins(bot: Client, message: Message):
    chat = message.chat
    member = await bot.get_chat_member(chat.id, message.from_user.id)
    if member.status not in ('administrator', 'creator'):
        await message.reply_text("You need to be an admin to do this!")
        return
    list = []
    async for i in bot.iter_chat_members(message.chat.id, filter="administrators"):
        list.append(i.user.id)
    admins[message.chat.id] = list
    await message.reply_text("Admins have been updated.")

@Opengm.on_chat_member_updated(filters.group & admin_change_filter)
async def reload_admins(bot: Client, update: ChatMemberUpdated):
    print(update)
    if not hasattr(update, "old_chat_member"):
        print("No!")
        return
    chat = update.chat
    alist = admins[update.chat.id]
    if update.new_chat_member.status in ('administrator', 'creator') and update.old_chat_member.status not in ('administrator', 'creator'):
        if update.new_chat_member.user.id not in alist:
            alist.append(update.new_chat_member.user.id)
        LOGGER.info(f"Added {update.new_chat_member.user.id} to the admin store in {chat.id}")
    elif update.new_chat_member.status not in ('administrator', 'creator') and update.old_chat_member.status in ('administrator', 'creator'):
        alist.remove(update.new_chat_member.user.id)
        LOGGER.info(f"Removed {update.new_chat_member.user.id} from the admin store in {chat.id}")
    admins[chat.id] = alist
    pass

@Opengm.on_chat_member_updated(filters.group & filters.new_chat_members)
async def bot_added_to_group(bot: Client, update: ChatMemberUpdated):
    print("Yo!")
