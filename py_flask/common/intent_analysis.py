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

    def do_chatgpt(self, query, loginfo):
        context = {}
        context['type'] = const.TEXT_ONCE #text without session
        context['loginfo'] = loginfo
        context['system_prompt'] = self.description
        response = self.chatgpt_bot.reply(self.query_format.format(query), context) 
        return response['content']

    def do_analyse(self, query, loginfo=[]):
        pass
        
class ImageIntentAnalyser(IntentAnalyser):
    def __init__(self, desc, query_format) -> None:
        super().__init__(desc, query_format)
                   
    def do_analyse(self, query, loginfo=[]):
        res = self.do_chatgpt(query, loginfo)
        res = re.findall(r'\b(YES|NO|UNCERTAIN)\b', res.upper())

        msgtype = None
        if len(res) >= 2:
            msgtype = const.IMAGE_SD if ("YES" in res[0]) and ("YES" in res[1]) else msgtype
            msgtype = const.IMAGE_INAPPROPRIATE if ("YES" in res[0]) and ("NO" in res[1]) else msgtype
        loginfo.append("image_itent_res={} image_intent={}".format(res, msgtype))
        return msgtype

class ContentExtractor(IntentAnalyser):
    def __init__(self, desc="", query_format="") -> None:
        super().__init__(desc, query_format)

    def do_analyse(self, query, loginfo=[]):
        res = self.do_chatgpt(query, loginfo)
        prompt = res.strip('"')
        parts = prompt.split('Draw', 1)
        prompt = prompt if len(parts) < 2 else parts[1].strip()
        loginfo.append('image_query={}'.format(prompt))
        return prompt
    
class TimelinessAnalayser(IntentAnalyser):
    def __init__(self, desc="", query_format="") -> None:
        super().__init__(desc, query_format)
    def do_analyse(self, query, loginfo=[]):
        res = self.do_chatgpt(query, loginfo)
        res = re.findall(r'\b(YES|NO|UNCERTAIN)\b', res.upper())

        msgtype = None
        if len(res) >= 2:
            msgtype = const.TIMELINESS if ("YES" in res[0]) and ("YES" in res[1]) else msgtype
            msgtype = const.TIMELINESS_INAPPROPRIATE if ("YES" in res[0]) and ("NO" in res[1]) else msgtype
        loginfo.append("timeliness_res={} timeliness_intent={}".format(res, msgtype))
        return msgtype
    
class GoogleQueryExtractor(IntentAnalyser):
    def __init__(self, desc="", query_format="") -> None:
        super().__init__(desc, query_format)

    def do_analyse(self, query, loginfo=[]):
        res = self.do_chatgpt(query, loginfo)
        prompt = res.strip('"')
        #parts = prompt.split(':', 1)
        #prompt = prompt if len(parts) < 2 else parts[1].strip()
        loginfo.append('google_search_query={}'.format(prompt))
        return prompt


image_intent_analyser_18 = ImageIntentAnalyser(
    desc='Now you are a text analyzer, you will analyze the text for intent and suitability for minors.',
    query_format=('Given a sentence "{}", answer two questions:'
        '1. Is this sentence has strong demand of drawing?'
        '2. Is this request suitable for 18 years old?'
        'Return two answers, each answer should not exceed one word, and the answer should be either YES or NO')
)

image_intent_analyser_15 = ImageIntentAnalyser(
    desc='Now you are a text analyzer, you will analyze the text for intent and suitability for minors.',
    query_format=('Given a sentence "{}", answer two questions:'
        '1. Is this sentence has strong demand of drawing?'
        '2. Is this request suitable for 15 years old?'
        'Return two answers, each answer should not exceed one word, and the answer should be either YES or NO')
)

content_extractor_english = ContentExtractor(
    desc='Now you are a content understanding machine, you will extract valid information in the text.',
    query_format=('The request is: "{}".'
        'Tell me what needs to be drawn in the request in English, answer me start with "Draw":')
)

timeliness_analayser = TimelinessAnalayser(
    desc='Now you are a text analyzer, you will analyze the text for intent and suitability for minors.',
    query_format=('Given a sentence "{}", answer two questions:'
        '1. Is this sentence has strong demand of timeliness?'
        '2. Is this request suitable for 18 years old?'
        'Return two answers, each answer should not exceed one word, and the answer should be either YES or NO')
)

google_query_extractor = GoogleQueryExtractor(
    desc='Now you are a content understanding machine, you will extract valid information in the text.',
    #query_format=('The request is: "{}".'
        #'Summarize the query used for google search from the request,'
         #'keep the language of query same with the request,'
         #'and answer me just 1 best query.')
    query_format=('给定一个句子"{}"'
        '从句子中提取出适合做搜索query的内容,'
        '把最好的一个query返回给我，不需要多余的语言.'
    )
)

