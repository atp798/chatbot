import logging
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

import os


def init_logger(log_level=logging.INFO):
    REAL_PATH = os.path.dirname(os.path.realpath(__file__))
    print("log path: ", REAL_PATH)

    #rHandler = RotatingFileHandler(os.path.join(REAL_PATH, 'log.info.'))

    # 创建TimedRotatingFileHandler对象，按天级轮换日志
    rHandler = TimedRotatingFileHandler('./log/log.info', when='midnight', interval=1, backupCount=30)

    rHandler.setLevel(log_level)
    # 设置日志文件名格式
    rHandler.suffix = '%Y%m%d'

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
    #logger.addHandler(console)
    return logger


# 日志句柄
logger = init_logger()
