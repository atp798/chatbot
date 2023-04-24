import json
import time
import threading
import os
import sys
sys.path.append(os.getcwd())
from common.log import logger
from common.singleton import SingletonC
from config import get_config
import requests
import traceback

@SingletonC
class WxmpToken(object):
    def __init__(self, expire_time=None):
        self.timestamp = None
        self.token = None
        self.timeout = 60 if expire_time is None else expire_time
        self.is_running = True
        if get_config().open_wxmp:
            threading.Thread(target=self._auto_get_token).start()

    def get_token(self):
        return self.token

    def _auto_get_token(self):
        logger.info("starting get wx token, appid={} secret={}".format(get_config().appid, get_config().secret))
        while self.is_running:
            #初始化
            if self.timestamp is None or self.token is None:
                oldtoken = self.token
                self.token = self._get_access_token()
                self.timestamp = time.time()
                logger.info("get newtoken={} oldtoken={} time={}".format(self.token, oldtoken, self.timestamp))
                time.sleep(1.0/100)
                continue
            else:
                nowtime = time.time()
                timediff = nowtime - self.timestamp
                #过期了
                if (timediff > self.timeout):
                    tmp_token = self._get_access_token() 
                    #拿到相同的token了
                    if tmp_token == self.token:
                        logger.info("get same token, do nothing")
                        pass
                    else:
                        logger.info("get newtoken={} oldtoken={} time={}".format(tmp_token, self.token, self.timestamp))
                        self.token = tmp_token
                        self.timestamp = nowtime
            #1s检查一次
            time.sleep(1)

    # 获取access_token
    def _get_access_token(self):
        try:
            appid = get_config().appid
            secret = get_config().secret
            url = 'https://api.weixin.qq.com/cgi-bin/token'
            params = {
                'grant_type': 'client_credential',
                'appid': appid,
                'secret': secret
            }
            response = requests.get(url, params=params)
            access_token = json.loads(response.text)['access_token']
            return access_token
        except Exception as e:
            logger.info("_get_access_token error={}".format(response.text))
            return None

    def close(self):
        self.is_running = False

wxToken = WxmpToken()
def get_wxmp_token():
    while True:
        token = wxToken.get_token()
        if token:
            return token
        time.sleep(1)
