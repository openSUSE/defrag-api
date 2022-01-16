from pyrogram import Client, filters
from pyrogram.types import Message

from opengm.opengm import Opengm
from opengm.utils.chat_status import user_admin, admins
from opengm.utils.commands import get_args
from opengm.utils.extraction import extract_user
from opengm.utils.plugins import register_plugin

HELPTEXT = """
**Admin only commands:**
- /promote: Promote a user to admin (by reply or userhandle)
- /demote: Demote an admin to user (by reply or userhandle)
- /pin: Pin a message (by reply)
- /unpin: Unpin a message (by reply)
- /unpinall: Unpin all messages

**User commands:**
- /admins or /adminlist: List all admins
"""
register_plugin("Admin management", HELPTEXT)


@Opengm.on_message(filters.command("promote"))
@user_admin
async def promote_user(bot: Client, msg: Message):
    args = get_args(msg)
    me = (await bot.get_me()).id
    bot_member = await msg.chat.get_member(me)
    target = await extract_user(msg)
    if target is None:
        await msg.reply_text("Please specify a user.")
        return
    user_member = await msg.chat.get_member(target)
    if user_member.status in ["creator", "administrator"]:
        await msg.reply_text("User is already an admin.")
        return
    if target == me:
        await msg.reply_text("I cannot promote myself.")
        return
    # check if bot has permissions to promote
    if not bot_member.can_promote_members:
        await msg.reply_text("I do not have permissions to promote users.")
        return
    # set the same permissions as the bot

    await bot.promote_chat_member(msg.chat.id, target, can_change_info=bot_member.can_change_info,
                                  can_post_messages=bot_member.can_post_messages,
                                  can_delete_messages=bot_member.can_delete_messages,
                                  can_invite_users=bot_member.can_invite_users,
                                  can_restrict_members=bot_member.can_restrict_members,
                                  can_pin_messages=bot_member.can_pin_messages,
                                  can_manage_voice_chats=bot_member.can_manage_voice_chats,
                                  can_manage_chat=bot_member.can_manage_chat,
                                  can_edit_messages=bot_member.can_edit_messages,
                                  can_promote_members=bot_member.can_promote_members)
    await msg.reply_text(f"User {user_member.user.mention} has been promoted.", parse_mode="html")


@Opengm.on_message(filters.command("demote"))
@user_admin
async def demote_user(bot: Client, msg: Message):
    args = get_args(msg)
    me = (await bot.get_me()).id
    bot_member = await msg.chat.get_member(me)
    target = await extract_user(msg)
    if target is None:
        await msg.reply_text("Please specify a user.")
        return
    user_member = await msg.chat.get_member(target)
    if user_member.status is "creator":
        await msg.reply_text("I cannot demote the creator of this group.")
        return
    if target == me:
        await msg.reply_text("Why would I demote myself, are you insane?")
        return
    # check if bot has permissions to demote
    if not bot_member.can_promote_members:
        await msg.reply_text("I do not have permissions to demote users.")
        return
    # demote the user
    await bot.promote_chat_member(msg.chat.id, target, can_change_info=False,
                                  can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                                  can_pin_messages=False, can_manage_voice_chats=False, can_manage_chat=False,
                                  can_edit_messages=False, can_promote_members=False)
    await msg.reply_text(f"User {user_member.user.mention} has been demoted.", parse_mode="html")


@Opengm.on_message(filters.command("pin"))
@user_admin
async def pin_message(bot: Client, msg: Message):
    args = get_args(msg)
    target_msg = msg.reply_to_message
    if target_msg is None:
        await msg.reply_text("Please reply to a message to pin it.")
        return
    # check if bot has permissions to pin
    if not msg.chat.permissions.can_pin_messages:
        await msg.reply_text("I do not have permissions to pin messages.")
        return
    # pin the message
    await bot.pin_chat_message(msg.chat.id, target_msg.message_id)
    await msg.reply_text("Message pinned.")


@Opengm.on_message(filters.command("unpin"))
@user_admin
async def unpin_message(bot: Client, msg: Message):
    args = get_args(msg)
    # check if bot has permissions to pin
    if not msg.chat.permissions.can_pin_messages:
        await msg.reply_text("I do not have permissions to unpin messages.")
        return
    target_msg = msg.reply_to_message
    if target_msg is None:
        await msg.reply_text("Please reply to a message to unpin it or use /unpinall.")
        return
    # unpin the message
    await bot.unpin_chat_message(msg.chat.id, target_msg.message_id)
    await msg.reply_text("Message unpinned.")


@Opengm.on_message(filters.command("unpinall"))
@user_admin
async def unpinall(bot: Client, msg: Message):
    # check if bot has permissions to pin
    if not msg.chat.permissions.can_pin_messages:
        await msg.reply_text("I do not have permissions to unpin messages.")
        return
    # unpin the message
    await bot.unpin_all_chat_messages(msg.chat.id)
    await msg.reply_text("All pinned messages unpinned.")


@Opengm.on_message(filters.command(["invitelink", "invite"]))
@user_admin
async def get_invite_link(bot: Client, msg: Message):
    if msg.chat.type == "private":
        await msg.reply_text("This command is meant to be used in a group chat.")
        return
    chat_id = msg.chat.id
    # check if group has username
    if msg.chat.username:
        await msg.reply_text(f"Group link: {msg.chat.username}")
        return
    # check if bot has permissions to generate invite link
    if not msg.chat.permissions.can_invite_users:
        await msg.reply_text("I do not have permissions to generate invite links.")
        return
    await msg.reply_text(f"Group link: {await bot.export_chat_invite_link(chat_id)}")

# Helps debugging
@Opengm.on_message(filters.group & filters.command(["admins", "adminlist"]))
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
