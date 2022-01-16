from pyrogram.errors import BadRequest
from pyrogram.types import Message

from opengm.opengm import Opengm
from opengm.utils.commands import get_args
import opengm.plugins.sql.users as sql
import logging

LOGGER = logging.getLogger(__name__)


async def id_from_reply(message: Message):
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    return user_id, message.text


async def extract_user_and_text(msg: Message):
    print("Starting extract")
    prev_msg = msg.reply_to_message
    args = get_args(msg)
    split_text = msg.text.split(None, 1)
    print(split_text)
    if len(split_text) < 2:
        id, text = await id_from_reply(msg)
        return await id_from_reply(msg)

    text_to_parse = split_text[1]
    text = ""
    # parse message entities
    entities = list(msg.entities)
    # Sort out everything not a mention from list
    entity_list = []
    for entity in entities:
        if entity.type == "text_mention":
            entity_list.append(entity)
    if len(entity_list) > 0:
        ent = entity_list[0]
    else:
        ent = None
    if entities and ent and ent.offset == len(msg.text) - len(text_to_parse):
        ent = entity_list[0]
        user_id = ent.user.id
        text = msg.text[ent.offset + ent.length:]
    # Extract from written ID
    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = msg.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    # Extract from username
    elif len(args) >= 1 and args[0][0] == '@':
        username = args[0]
        users = await sql.get_user_id_by_name(username)
        # get text
        text = " ".join(args[1:])
        if not users:
            pass
        elif len(users) == 1:
            user_id = users[0].user_id
        else:
            for user_obj in users:
                try:
                    userdat = await (await (Opengm.get_chat_member(msg.chat.id, user_obj.user_id)).user)
                    if userdat.username == username:
                        user_id = userdat.userdat.id

                except BadRequest as excp:
                    LOGGER.error(excp.message)
    # Extract from reply
    elif prev_msg:
        user_id, text = await id_from_reply(msg)

    # Fallback
    else:
        return None, None
    return user_id, text
