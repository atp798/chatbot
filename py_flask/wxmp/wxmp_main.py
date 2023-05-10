import json
import time
import threading
import os
import sys
sys.path.append(os.getcwd())
from common.log import logger
from common.singleton import SingletonC
from config import get_config
import traceback
import re
from wxmp.wxmp_post2user import post_img_respons2wxmp, post_respons2wxmp, post_img_respons2wxmp_SD

def process_wxmp_request(request_json, bot):
    #parameter constant
    loginfo = []
    loginfo.append("request_json={}".format(request_json))
    can_process_type = ['text', 'event']
    if not request_json.get('MsgType', None) in can_process_type:
        logger.info("cannot process this msgtype")
        return

    #对关注请求特殊处理
    try:
        #关注
        if request_json["MsgType"] == "event" and request_json["Event"] == "subscribe":
            post_respons2wxmp(get_welcome_words(), request_json["FromUserName"])
            logger.info("handle subscribe event, return welcome words")
            return

        #取关
        if request_json["MsgType"] == "event" and request_json["Event"] == "unsubscribe":
            return
    except Exception as error:
        logger.info("handler subscribe/unsubscribe reqeust error")
        return

    session_id = request_json["FromUserName"]
    query = request_json["Content"]
    loginfo.append("raw_query=[{}], session_id={}".format(query, session_id))
    logger.info('begin process, {}'.format('; '.join(loginfo)))

    #标注请求类型，文字还是画图，有可能有更复杂的
    msg_type = request_json.get("MsgType", "TEXT").upper()
    msg_type = "IMAGE_SD" if any(item in {'画'} for item in query[:4]) else msg_type #对中文，前4个字包含画
    msg_type = "IMAGE_SD" if any(item.lower() in {'draw'} for item in query.split(' ')[:4]) else msg_type #对英文，前4个词包含画
    if msg_type == "IMAGE_SD":
        #意图判断
        context_tmp = {}
        context_tmp['session_id'] = session_id
        context_tmp['type'] = "TEXT_ONCE" #text without session
        response = bot.reply(
            'Given a sentence "' + query + '"，' + 
            'answer two questions: 1. Is this sentence just a request for drawing? 2. Is this sentence suitable for 12 years old? Return two answers, each answer should not exceed one word, and the answer should be either YES, NO, or UNCERTAIN'
            , context_tmp)
        res = re.findall(r'\b(YES|NO|UNCERTAIN)\b', response.upper())
        if len(res) >= 2:
            msg_type = "IMAGE_SD" if ("YES" in res[0]) and ("YES" in res[1]) else "TEXT"
        loginfo.append("res={}, msgtype={}".format(res, msg_type))

    context = {}
    context['session_id'] = session_id
    context['type'] = msg_type
    response = None
    retry = 3
    while retry > 0:
        retry -= 1
        try:
            response = bot.reply(query, context)
            # 从响应中获取结果
        except Exception as error:
            logger.info("get openai err=".format(error))
            traceback.print_exc()
            continue
        if response:
            break
    toUserName = request_json["FromUserName"]
    #fromUserName = request_json["ToUserName"] 
    if not response:
        response = "发生未知错误，系统正在修复中，请稍后重试..."

    if context['type'] == "TEXT":
        post_respons2wxmp(response, toUserName)
    elif context['type'] == "IMAGE":
        post_img_respons2wxmp(response, toUserName)
    elif context['type'] == "IMAGE_SD":
        post_img_respons2wxmp_SD(response, toUserName)
    logger.info("end process, {}".format('; '.join(loginfo)))
    return
    

def get_welcome_words():
    return '''
嗨，你好！我是全世界最聪明的聊天机器人“机器知心”，接下来我会一直陪着你解答你的任何问题。
你可以问我一些简单的问题，比如：外星人真实存在吗？
或者，你可以跟我玩一些文字游戏，比如：“我希望你表现得像西游记中的唐三藏。我希望你像唐三藏一样回应和回答。不要写任何解释。必须以唐三藏的语气和知识范围为基础。我的第一句话是'你好'。”
你也可以向我提出画图的问题，只要以“画”开头提问就好了，比如：“画一只正在玩球的金毛”、“画一个写作业的小学生”。

我可以担任数学老师、小说家、编剧、说唱歌手、诗人、哲学家、画家、程序员、医生等多达5000个角色，只需要你能为我定制好角色的原型！
现在开始来愉快地玩耍吧~~
'''