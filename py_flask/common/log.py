import logging
from logging.handlers import RotatingFileHandler
import os


def init_logger(log_level=logging.INFO):
    REAL_PATH = os.path.dirname(os.path.realpath(__file__))
    print("log path: ", REAL_PATH)

    rHandler = RotatingFileHandler(os.path.join(REAL_PATH, 'log.txt'))
    rHandler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s %(pathname)s func: %(funcName)s \
        line: %(lineno)s %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    rHandler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(level=log_level)
    logger.addHandler(rHandler)
    logger.addHandler(console)
    return logger


# 日志句柄
logger = init_logger()
