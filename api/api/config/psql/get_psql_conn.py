import asyncpg

from api.config.settings import env, logger


async def get_psql_conn():
    logger.info("connecting to psql")
    conn = await asyncpg.connect(
        database=env.PSQL_DATABASE,
        host=env.PSQL_HOST,
        password=env.PSQL_PASSWORD,
        user=env.PSQL_USER,
    )
    try:
        logger.info("connected to psql")
        yield conn
    finally:
        logger.info("closing psql connection")
        await conn.close()
