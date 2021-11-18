from pyrogram.types import Message
from pyrogram import Client
from opengm.utils.commands import get_args
import opengm.plugins.sql.users 
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
    print(len(split_text))
    if len(split_text) < 2:
        print("here")
        id, text = await id_from_reply(msg)
        print(id)
        print(text)
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

    # Extract from reply
    elif prev_msg:
        user_id, text = await id_from_reply(msg)
    
    # Fallback
    else:
        return None, None
    return user_id, text
