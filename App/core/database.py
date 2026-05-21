from tortoise import Tortoise
from functools import lru_cache

# configuration
import App.core.settings as settings

@lru_cache
def get_settings():
    return settings.Settings()


tortoise_conn_string = "postgres://" + \
                       settings.settings.db_user + \
                       ":" + \
                       settings.settings.db_password + \
                       "@" + \
                       settings.settings.db_server + \
                       ":" + \
                       settings.settings.db_server_port + \
                       "/" + settings.settings.db_database

async def init():
    await Tortoise.init(
        db_url=tortoise_conn_string,
        modules={
            'models':
                [
                     "App.models.usuario",
                     "App.models.rol",
                     "App.models.endpoint",
                ]
        }
    )
    await Tortoise.generate_schemas()


async def close():
    await Tortoise.close_connections()

