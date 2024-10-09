import uvicorn

from api.config.settings import env, logger

if __name__ == "__main__":
    logger.info("starting uvicorn server")
    uvicorn.run(
        access_log=False,
        app="app:app",
        date_header=False,
        host=env.HOST,
        log_config=None,
        log_level=env.LOG_LEVEL.lower(),
        loop="uvloop",
        port=env.PORT,
        reload=env.is_development,
        server_header=False,
    )
