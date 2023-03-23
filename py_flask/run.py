# encoding:utf-8

from common.log import logger
from app.chat_server import ChatServer
from config import get_config

if __name__ == '__main__':
    try:
        logger.info("App starting...")
        server = ChatServer(get_config())
        server.run()
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)