# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import logging
from os import environ as env
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware

__MOD_NAME__ = "tgrambot"

logging.basicConfig(level=logging.INFO)


async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


async def echo(message: types.Message):
    await message.answer(message.text)

def start_bot():
    bot = Bot(token=env["TELEGRAM_BOT_TOKEN"])
    dp = Dispatcher(bot)
    dp.middleware.setup(LoggingMiddleware())
    dp.register_message_handler(send_welcome, commands=['start', 'welcome'])
    dp.register_message_handler(echo, content_types=types.Message)
    asyncio.create_task(dp.start_polling())