import logging
from sys import exit
from decouple import config
from .opengm import Opengm

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.getLevelName(config("LOG_LEVEL", default="INFO")),
)

try:
    if __name__ == "__main__":
        Opengm().run()

except KeyboardInterrupt:
    exit()
