from pyrogram import Client
from pyrogram.types import Message
from opengm.opengm import Opengm, command
from opengm.utils.chat_status import user_admin
from opengm.utils.plugins import register_plugin
from opengm.utils.commands import get_args
from opengm.utils.extraction import extract_user_and_text
register_plugin("Admin management", "This is a help text.")
