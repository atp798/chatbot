import threading
import time,datetime
import sys
from common.log import logger
import json
import requests
import traceback
import base64


class WxmpVipLimit:
    def __init__(self, text_limit=0, image_limit=0):
        self.limit_dict = {
            "TEXT": text_limit,
            "IMAGE": image_limit
            }
    def __str__(self):
        return json.dumps(self.limit_dict)

class WxmpRequestLimiter:
    def __init__(self, path="./common/wxmp_whitelist.json"):
        self.last_update_timestamp = None
        self.confdict = {}
        self.openid_dict = {}
        ##vip0: 普通vip, 每天10条, 默认等级
        ##vip1: 普通vip, 每天10条, 默认等级, 留一个做扩展
        ##vip2: 无限量访问
        ##vip3: 可以画图，1024*1024高清，以“画xx”开头提问即可
        ##vip_forevel: 内部测试用，无限制
        self.vip_limit_dict = {
            "vip_level_0": WxmpVipLimit(100, 50),
            "vip_level_1": WxmpVipLimit(100, 50),
            "vip_level_2": WxmpVipLimit(1000, 50),
            "vip_level_3": WxmpVipLimit(1000, 1000),
            "vip_level_forever": WxmpVipLimit(1000, 1000),
        }

        self.update_whitelist()
        return

    #同步更新，粗暴实现，可以考虑异步
    def update_whitelist(self):
        if self.last_update_timestamp is None or time.time() - self.last_update_timestamp > 60:
            self.confdict = self.get_whitelist_from_github()
            #把字典倒过来
            tmp_dict = {}
            for key, value in self.confdict.items():
                for v in value:
                    tmp_dict[v] = key
            self.openid_dict = tmp_dict
            self.last_update_timestamp = time.time()

    def get_whitelist_from_github(self, url="https://api.github.com/repos/atp798/chatbot/contents/py_flask/common/wxmp_whitelist.json"):
        try:
            response = requests.get(url)
            json_data = json.loads(response.content)
            content = json_data['content']
            decoded_content = base64.b64decode(content).decode('utf-8')
            json_obj = json.loads(decoded_content)
            logger.info("update remote whitelist succ!!")
            logger.info("{}".format(json_obj))
            return json_obj
        except Exception as e:
            logger.info("update remote whitelist error!!")
            traceback.print_exc()
            return None 

    def get_vip_level(self, openid):
        return self.openid_dict.get(openid, "vip_level_0")
    
    def get_vip_limit(self, openid):
        return self.vip_limit_dict.get(self.get_vip_level(openid))
    
    def do_limit(self, openid, session, msgtype):
        #每60s更新一下数据表
        self.update_whitelist()

        #这个方法实现的比较挫，每次都遍历，但考虑到用户少，也没啥了
        # 设置时区
        tz_offset = 8  # 东八区
        tz_secs = tz_offset * 3600
        # 获取当前时间戳
        now = time.time()
        # 计算当天凌晨时间戳
        midnight = int((now + tz_secs) // 86400 * 86400 - tz_secs)

        logger.info("midnight={}, access={}, msgtype={}".format(midnight, session, msgtype))
        access_timestamp = [s for s in session if s.get("type") == msgtype and s.get("timestamp", 0) > midnight]

        limit_conf = self.get_vip_limit(openid)
        return len(access_timestamp) > limit_conf.limit_dict[msgtype]

if __name__ == "__main__":
    wxmp_token = WxmpVipTokenBucket()
    print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z0"))
    print(wxmp_token.get_vip_limit("oiJo_5k_gmRDC6GFWTPsKGvCiVbg"))
    print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z01111"))
    wxmp_token.do_limit("1111", {})

