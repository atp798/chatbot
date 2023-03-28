import threading
import time,datetime
import sys
from common.log import logger
import json


class WxmpVipLimit:
    def __init__(self, text_limit=0, image_limit=0):
        self.text_limit = text_limit
        self.image_limit = image_limit
    def __str__(self):
        return json.dumps({"text_limit": self.text_limit, "image_limit": self.image_limit})

class WxmpRequestLimiter:
    def __init__(self, path="./common/wxmp_whitelist.json"):
        confdict = None
        with open(path, mode='r', encoding='utf-8') as f:
             confdict = json.loads(f.read())
        if (confdict is None):
            logger.error("cannot open vip list, exit")
            sys.exit(-1)

        #把字典倒过来
        tmp_dict = {}
        for key, value in confdict.items():
            for v in value:
                tmp_dict[v] = key
        self.openid_dict = tmp_dict 
        
        ##vip0: 普通vip, 每天10条, 默认等级
        ##vip1: 普通vip, 每天10条, 默认等级, 留一个做扩展
        ##vip2: 无限量访问
        ##vip3: 可以画图，1024*1024高清，以“画xx”开头提问即可
        ##vip_forevel: 内部测试用，无限制
        self.vip_limit_dict = {
            "vip_level_0": WxmpVipLimit(10, 0),
            "vip_level_1": WxmpVipLimit(10, 0),
            "vip_level_2": WxmpVipLimit(1000, 0),
            "vip_level_3": WxmpVipLimit(1000, 1000),
            "vip_level_forever": WxmpVipLimit(1000, 1000),
        }

    def get_vip_level(self, openid):
        return self.openid_dict.get(openid, "vip_level_0")
    
    def get_vip_limit(self, openid):
        return self.vip_limit_dict.get(self.get_vip_level(openid))
    
    def do_limit(self, openid, session):
        #这个方法实现的比较挫，每次都遍历，但考虑到用户少，也没啥了
        # 设置时区
        tz_offset = 8  # 东八区
        tz_secs = tz_offset * 3600
        # 获取当前时间戳
        now = time.time()
        # 计算当天凌晨时间戳
        midnight = int((now + tz_secs) // 86400 * 86400 - tz_secs)

        text_access_timestamp = [s for s in session if s.get("role", "") == "user" and s.get("type") == "text" and s.get("timestamp", 0) > midnight]
        image_access_timestamp = [s for s in session if s.get("role", "") == "user" and s.get("type") == "image" and s.get("timestamp", 0) > midnight]

        limit_conf = self.get_vip_limit(openid)
        return len(text_access_timestamp) < limit_conf.text_limit and len(image_access_timestamp) < limit_conf.image_limit

if __name__ == "__main__":
    wxmp_token = WxmpVipTokenBucket()
    print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z0"))
    print(wxmp_token.get_vip_limit("oiJo_5k_gmRDC6GFWTPsKGvCiVbg"))
    print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z01111"))
    wxmp_token.do_limit("1111", {})

