from aiogram.dispatcher.webhook import BaseResponse
from defrag import app
from defrag.modules.helpers.services_manager import ServiceTemplate, ServicesManager
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import asyncio
import logging
from os import environ as env

__MOD_NAME__ = "tgrambot"

logging.basicConfig(level=logging.INFO)

TOKEN = env["TELEGRAM_BOT_TOKEN"]
# about HOST: use ngrok.io to get an https endpoint to expose and forward from
# in prodution we will need to pass our own TLS certificate to `set_webhook` below
WEBHOOK_HOST = env["TELEGRAM_HOST"]
WEBHOOK_PATH = env["TELEGRAM_PATH"]
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}{TOKEN}"
APP_PORT = env["APP_PORT"]
APP_HOST = env["APP_HOST"]


bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


@dp.message_handler()
async def echo(message: types.Message) -> None:
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await bot.send_message(chat_id=message.chat.id, text="Hi!\nI'm EchoBot!\nPowered by aiogram.")


@app.post(WEBHOOK_PATH + TOKEN)
async def bot_endpoint(data: dict):
    res = await dp.process_update(types.Update(**data))
    if isinstance(res, BaseResponse):
        return res.get_response()
    print("Not an instance of BaseResponse.")


def start_bot(webhook: bool) -> None:
    dp.middleware.setup(LoggingMiddleware())
    if webhook:
        asyncio.create_task(bot.set_webhook(url=WEBHOOK_URL))
    else:
        asyncio.create_task(dp.start_polling())


def register() -> None:
    template = ServiceTemplate(__MOD_NAME__, None, None, None, None, None)
    service = ServicesManager.realize_service_template(template, None)
    ServicesManager.register_service(__MOD_NAME__, service)
    start_bot(webhook=True)
