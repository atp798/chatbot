import threading, time, os, sys, json, requests
sys.path.append(os.getcwd())
from common.log import logger
import traceback
import base64
from wxmp.wxmp_access_token import get_wxmp_token
from enum import Enum
import threading
from common.singleton import SingletonC

class VIP_LEVEL(Enum):
   L0 = 105
   L1 = 106
   L2 = 107
   L3 = 108
   NOLIMIT = 109


class WxmpVipLimit:
    def __init__(self, text_limit=0, image_limit=0):
        self.limit_dict = {
            "TEXT": text_limit,
            "IMAGE": image_limit
            }
    def __str__(self):
        return json.dumps(self.limit_dict)

@SingletonC
class WxmpRequestLimiter:
    def __init__(self):
        self.openid_dict = {}
        #self.conf_dict = {}
        ##vip0: 普通vip, 每天10条, 默认等级
        ##vip1: 普通vip, 每天10条, 默认等级, 留一个做扩展
        ##vip2: 无限量访问
        ##vip3: 可以画图，1024*1024高清，以“画xx”开头提问即可
        ##vip_forevel: 内部测试用，无限制
        self.vip_limit_dict = {
            VIP_LEVEL.L0.value: WxmpVipLimit(100, 50),
            VIP_LEVEL.L1.value: WxmpVipLimit(100, 50),
            VIP_LEVEL.L2.value: WxmpVipLimit(1000, 50),
            VIP_LEVEL.L3.value: WxmpVipLimit(1000, 1000),
            VIP_LEVEL.NOLIMIT.value: WxmpVipLimit(1000, 1000),
        }

        threading.Thread(target=self.update_user_vip_level_asyn).start()
        return

    def get_vip_limit_by_level(self, vip_level):
        return self.vip_limit_dict.get(vip_level)
    
    # 获取用户信息
    def get_user_info(self, openid):
        try:
            access_token = get_wxmp_token()
            url = 'https://api.weixin.qq.com/cgi-bin/user/info'
            params = {
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN'
            }
            response = requests.get(url, params=params)
            user_info = json.loads(response.text)
            tags = user_info.get("tagid_list", [])
            tags = min([max(tags), VIP_LEVEL.NOLIMIT.value])
            return tags
        except Exception as e:
            #logger.info("get user tags info error, set to nolimit mode...")
            return None

    def update_user_vip_level_asyn(self):
        while True:
            openids = [key for key in self.openid_dict]
            for openid in openids:
                vip_level = self.get_user_info(openid)
                if vip_level:
                    self.openid_dict[openid] = vip_level
                time.sleep(1/100)
            time.sleep(10)
            
    
    def do_limit(self, openid, session, msgtype):
        #这个方法实现的比较挫，每次都遍历，但考虑到用户少，也没啥了
        # 设置时区
        tz_offset = 8  # 东八区
        tz_secs = tz_offset * 3600
        # 获取当前时间戳
        now = time.time()
        # 计算当天凌晨时间戳
        midnight = int((now + tz_secs) // 86400 * 86400 - tz_secs)

        access_timestamp = [s for s in session if s.get("type") == msgtype and s.get("timestamp", 0) > midnight]

        btime = time.time()
        user_tag = self.openid_dict.get(openid, None)
        if user_tag is None:
            logger.info("get no user tags info, set to nolimit mode...")
            user_tag = VIP_LEVEL.NOLIMIT.value
            self.openid_dict[openid] = None

        limit_conf = self.get_vip_limit_by_level(user_tag)
        logger.info("midnight={}, access={}, msgtype={}, usertag={} limitconf={}".format(midnight, session, msgtype, user_tag, limit_conf))
        return len(access_timestamp) > limit_conf.limit_dict[msgtype]

    #同步更新，粗暴实现，可以考虑异步
    def update_whitelist(self):
        if self.last_update_timestamp is None or time.time() - self.last_update_timestamp > 600000000000:
            self.conf_dict = self.get_whitelist_from_github()
            #把字典倒过来
            tmp_dict = {}
            for key, value in self.conf_dict.items():
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
        return self.openid_dict.get(openid, VIP_LEVEL.L0.value)
    
    def get_vip_limit(self, openid):
        return self.vip_limit_dict.get(self.get_vip_level(openid))

if __name__ == "__main__":
    #print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z0"))
    #print(wxmp_token.get_vip_limit("oiJo_5k_gmRDC6GFWTPsKGvCiVbg"))
    #print(wxmp_token.get_vip_limit("oiJo_5v6u7R4O2Y54UmexxVsz6Z01111"))
    #wxmp_token.do_limit("1111", {})
    limiter = WxmpRequestLimiter()
    limiter.get_user_info('oiJo_5lGFN1xwiQtvFxT2W_7N6v8')