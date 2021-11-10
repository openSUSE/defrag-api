import configparser
from redis import Redis, BlockingConnectionPool


config = configparser.ConfigParser()
config.read(["config.ini", "opengm.ini", "opensuse.ini"])
REDIS_HOST = config["REDIS"]["REDIS_HOST"]
REDIS_PORT = int(config["REDIS"]["REDIS_PORT"])
REDIS_PWD = config["REDIS"]["REDIS_PWD"]

pool = BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD)
redis = Redis(connection_pool=pool)
