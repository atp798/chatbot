from bot.chatgpt import chat_gpt_bot
from config import conf
from bot import bot_factory
from common import const
import re
from common.log import logger
from bot.chatgpt import chat_gpt_bot

class IntentAnalyser(object):
    def __init__(self, desc="", query_format="") -> None:
        self.chatgpt_bot = chat_gpt_bot.ChatGPTBot(conf_json=conf())
        self.description = desc
        self.query_format = query_format

    def do_chatgpt(self, loginfo, query):
        context = {}
        context['type'] = const.TEXT_ONCE #text without session
        context['loginfo'] = loginfo
        context['system_prompt'] = self.description
        response = self.chatgpt_bot.reply(self.query_format.format(query), context) 
        return response
        
class ImageIntentAnalyser(IntentAnalyser):
    def __init__(self, desc, query_format) -> None:
        super().__init__(desc, query_format)
                   

    def do_analyse(self, query, loginfo=[]):
        res = self.do_chatgpt(loginfo, query)
        res = re.findall(r'\b(YES|NO|UNCERTAIN)\b', res.upper())

        msgtype = const.TEXT
        if len(res) >= 2:
            msgtype = const.IMAGE_SD if ("YES" in res[0]) and ("YES" in res[1]) else msgtype
            msgtype = const.IMAGE_INAPPROPRIATE if ("YES" in res[0]) and ("NO" in res[1]) else msgtype
        loginfo.append("image_intent={}".format(res))
        return msgtype
        

image_intent_analyser_18 = ImageIntentAnalyser(
    desc='Now you are a text analyzer, you will analyze the text for intent and suitability for minors.',
    query_format=('Given a sentence "{}", answer two questions: '
        '1. Is this sentence just a request for drawing? '
        '2. Is this sentence suitable for 18 years old? '
        'Return two answers, each answer should not exceed one word, and the answer should be either YES or NO')
)

image_intent_analyser_15 = ImageIntentAnalyser(
    desc='Now you are a text analyzer, you will analyze the text for intent and suitability for minors.',
    query_format=('Given a sentence "{}", answer two questions: '
        '1. Is this sentence just a request for drawing? '
        '2. Is this sentence suitable for 15 years old? '
        'Return two answers, each answer should not exceed one word, and the answer should be either YES or NO')
)



