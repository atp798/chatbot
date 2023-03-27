import json
import time
import threading
import sys
sys.path.append("./")
from urllib import parse, request
from config import get_config
from common.log import logger
from singleton import SingletonC

@SingletonC
class WxmpToken(object):
    def __init__(self, expire_time=None):
        self.timestamp = None
        self.token = None
        self.timeout = 600 if expire_time is None else expire_time
        self.is_running = True
        threading.Thread(target=self._auto_get_token).start()

    def get_token(self):
        return self.token

    def _auto_get_token(self):
        logger.info("starting get wx token, appid={} secret={}".format(get_config().appid, get_config().secret))
        while self.is_running:
            #初始化
            if self.timestamp is None or self.token is None:
                oldtoken = self.token
                self.token = self._get_wxCode_token()
                self.timestamp = time.time()
                logger.info("get newtoken={} oldtoken={} time={}".format(self.token, oldtoken, self.timestamp))
            else:
                nowtime = time.time()
                timediff = nowtime - self.timestamp
                #过期了
                if (timediff > self.timeout):
                    tmp_token = self._get_wxCode_token() 
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

    def _get_wxCode_token(self):
        try:
            appid = get_config().appid
            secret = get_config().secret
            textmod = {"grant_type": "client_credential",
                "appid": appid,
                "secret": secret
            }
            textmod = parse.urlencode(textmod)
            header_dict = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko'}
            url = 'https://api.weixin.qq.com/cgi-bin/token'
            req = request.Request(url='%s%s%s' % (url, '?', textmod), headers=header_dict)
            res = request.urlopen(req)
            res = res.read().decode(encoding='utf-8')
            res = json.loads(res)
            access_token = res["access_token"]
            print('res:', res)
            print('access_token:', access_token)
            return access_token
        except Exception as e:
            print('error:', e)
            return None
        
    def close(self):
        self.is_running = False

wxToken = WxmpToken()
def get_wxmp_token():
    return wxToken.get_token()


def post_respons2wxmp(res=None):
    pass


if __name__ == '__main__':

    res = \
    """<xml>
  <ToUserName><![CDATA[{toUser}]]></ToUserName>
  <FromUserName><![CDATA[{fromUser}]]></FromUserName>
  <CreateTime>{ctime}</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[{content}]]></Content>
</xml>""".format(toUser="11", fromUser="22", ctime=time.time(), content="33")
    print("tttttttt=", res)
    for i in range(1, 3):
        #logger.info("get_token={}".format(get_wxmp_token()))
        #time.sleep(1)
        pass
    wxToken.close()