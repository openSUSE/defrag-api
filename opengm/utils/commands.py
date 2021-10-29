from pyrogram.types import Message
from pyrogram import filters

def get_args(msg: Message):
    return msg.text.split()[1:]


def command(command: str):
    return filters.regex("^(!|/)help(@fancyhammerbot)?")
