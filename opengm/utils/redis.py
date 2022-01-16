from redis import Redis, BlockingConnectionPool
from opengm import REDIS_PWD, REDIS_HOST, REDIS_PORT
import logging

LOGGER = logging.getLogger(__name__)
pool = None
REDIS = None

def init_redis():
    LOGGER.debug("Initializing Redis..")
    pool = BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD,)
    REDIS = Redis(connection_pool=pool)
    LOGGER.debug("Redis init complete!")

