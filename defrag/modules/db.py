import logging
from os import environ as env
from typing import Type
from redis import Redis

logging.basicConfig()

__MOD_NAME__ = "db"


def connect_auth() -> Redis:
    return Redis(host=env["REDIS_HOST"], port=env["REDIS_PORT"], password=env["REDIS_PWD"])


def redis_hello_world() -> None:
    r = connect_auth()
    r.set("Hello", "World")
    res = r.get("Hello").decode("utf-8")
    assert res == "World"

if __name__ == "__main__":
    redis_hello_world()