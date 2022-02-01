from pyrogram import filters
from pyrogram.types import Message


def get_args(msg: Message):
    return msg.text.split()[1:]


def command(command: str):
    return filters.regex("^(!|/)help(@fancyhammerbot)?")
