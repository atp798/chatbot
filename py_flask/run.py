# encoding:utf-8

from common.log import logger
from app.chat_server import ChatServer
from config import get_config


class AppEntry:

    def __init__(self):
        logger.info("App is init...")
        self._server = ChatServer(get_config())

    def __call__(self, environ, start_response):
        # WSGI wrapper for gunicorn
        return self._server(environ, start_response)


app_entry = AppEntry()

if __name__ == '__main__':
    try:
        logger.info("App starting...")
        server = ChatServer(get_config())
        server.run()
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)