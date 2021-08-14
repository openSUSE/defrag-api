import asyncio
from defrag.modules.helpers.services_manager import ServiceTemplate, ServicesManager
import logging
from os import environ as env
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware

__MOD_NAME__ = "tgrambot"

logging.basicConfig(level=logging.INFO)


async def master_handler(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


async def echo(message: types.Message):
    await message.answer(message.text)


async def sendToChannel(bot: Bot):
    await bot.send_message("@pubchess", "Test")


def start_bot():
    bot = Bot(token=env["TELEGRAM_BOT_TOKEN"])
    dp = Dispatcher(bot)
    dp.middleware.setup(LoggingMiddleware())
    dp.register_message_handler(master_handler, commands=['start', 'welcome'])
    dp.register_message_handler(echo, content_types=types.Message)
    asyncio.create_task(dp.start_polling())


def register():
    template = ServiceTemplate(__MOD_NAME__, None, None, None, None, None)
    service = ServicesManager.realize_service_template(template, None)
    ServicesManager.register_service(__MOD_NAME__, service)
    start_bot()
