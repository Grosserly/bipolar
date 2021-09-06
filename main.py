import config
import logging
import aioredis
from bot import Parrot

logging.info("Initializing bot...")

redis_url = f"{config.REDIS_HOST}"

bot = Parrot(
    prefix=config.COMMAND_PREFIX,
    admin_user_ids=config.ADMIN_USER_IDS,
    redis=aioredis.Redis(
        username=config.REDIS_USERNAME,
        password=config.REDIS_PASSWORD,
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_INDEX,
        decode_responses=True,
    ),
)

bot.run(config.DISCORD_BOT_TOKEN)
