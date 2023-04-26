# encoding:utf-8

from bot.bot import Bot
from common.log import logger
from common.token_bucket import TokenBucket
from common.expired_dict import ExpiredDict
from common.session import Session
import openai
import time
import requests
import io
from config import get_config
import base64


# OpenAI对话模型API (可用)
class ChatGPTBot(Bot):

    def __init__(self, config_parser):
        logger.info("bot is starting...")
        openai.api_key = config_parser.api_key
        self._session = Session(config_parser)

        self._enable_rate_limit = False
        if config_parser.rate_limit_chatgpt > 0:
            self._enable_rate_limit = True
            self._tb4chatgpt = TokenBucket(config_parser.rate_limit_chatgpt)
        if len(config_parser.clear_memory_commands) > 0:
            self._clear_memory_commands = config_parser.clear_memory_commands
        if len(config_parser.clear_all_memory_commands) > 0:
            self._clear_all_memory_commands = config_parser.clear_all_memory_commands

    def reply(self, query, context=None):
        # acquire reply content
        '''
            type and session_id is important in context!!!
            type is TEXT by default
        '''
        msgtype = context.get('type', None)
        if msgtype is None:
            logger.warn("[OPEN_AI] error request, no msgtype!")
            return ""

        if not 'loginfo' in context:
            context['loginfo'] = []
        loginfo = context.get('loginfo')

        session_id = context.get('session_id', None)
        if session_id is None:
            return "Invalid session id"
        if query == self._clear_memory_commands:
            self._session.clear_session(session_id)
            return 'memory cleared'

        session = self._session.build_session_query(query, session_id, msgtype) 
        if session is None:
            return "Build session failed"

        btime = time.time()
        #对于text once请求，要求他的结果尽量确定
        if msgtype == "TEXT" or msgtype == "TEXT_ONCE":
            reply_content = self.reply_text(session, session_id, 0, 0) if msgtype == "TEXT_ONCE" \
                else self.reply_text(session, session_id, 0, 0.6)
            if reply_content["completion_tokens"] > 0:
                self._session.save_session(reply_content["content"], session_id, reply_content["total_tokens"])

        elif msgtype == "IMAGE":
            reply_content = self.reply_image(query, 0)

        elif msgtype == "IMAGE_RAW":
            reply_content = self.reply_image_rawdata(query)

        tdiff = time.time() - btime
        loginfo.append("openai_query=[{}], msgtype={}, time={}".format(query, msgtype, int(tdiff * 1000)))
        return reply_content["content"]

    def reply_text(self, session, session_id, retry_count=0, temperature=0.6) -> dict:
        '''
        call openai's ChatCompletion to get the answer
        :param session: a conversation session
        :param session_id: session id
        :param retry_count: retry count
        :return: {}
        '''
        try:
            response = openai.ChatCompletion.create(
                model= get_config().gpt_model,  # 对话模型的名称
                messages=session,
                temperature=temperature,  # 值在[0,1]之间，越大表示回复越具有不确定性
                #max_tokens=4096,  # 回复最大的字符数
                top_p=1,
                frequency_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                presence_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            )
            return {
                "total_tokens": response["usage"]["total_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
                "content": response.choices[0]['message']['content']
            }
        except openai.error.RateLimitError as e:
            # rate limit exception
            logger.warn(e)
            if retry_count < 1:
                time.sleep(5)
                logger.warn("[OPEN_AI] RateLimit exceed, {} times retry".format(retry_count + 1))
                return self.reply_text(session, session_id, retry_count + 1)
            else:
                return {"completion_tokens": 0, "content": "you ask too fast, please wait a moment"}
        except openai.error.APIConnectionError as e:
            # api connection exception
            logger.warn(e)
            logger.warn("[OPEN_AI] APIConnection failed")
            return {"completion_tokens": 0, "content": "cannot connect to openai"}
        except openai.error.Timeout as e:
            logger.warn(e)
            logger.warn("[OPEN_AI] Timeout")
            return {"completion_tokens": 0, "content": "cannot receive openai response"}
        except Exception as e:
            # unknown exception
            logger.exception(e)
            Session.clear_session(session_id)
            return {"completion_tokens": 0, "content": "unknown error, please ask again"}

    def reply_image(self, query, retry_count=0):
        try:
            logger.info("[OPEN_AI] image_query={}".format(query))
            response = openai.Image.create(
                prompt=query,    #图片描述
                n=1,             #每次生成图片的数量
                size="256x256"   #图片大小,可选有 256x256, 512x512, 1024x1024
            )
            image_url = response['data'][0]['url']
            return {"completion_images": 1, "content": image_url}

        except openai.error.RateLimitError as e:
            logger.warn(e)
            if retry_count < 1:
                time.sleep(5)
                logger.warn("[OPEN_AI] ImgCreate RateLimit exceed, 第{}次重试".format(retry_count+1))
                return self.create_img(query, retry_count+1)
            else:
                return "请求太快啦，请休息一下再问我吧"
            
    def reply_image_rawdata(self, query):
        logger.info("[OPEN_AI] image_raw_query={}".format(query))
        imgurl = self.reply_image(query=query, retry_count=3).get("content", None)
        if imgurl is None:
            return ""
        
        retry_count = 3
        imgcontent = ""
        while retry_count > 0:
            retry_count -= 1
            try:
                imgcontent = requests.get(imgurl).content
                if imgcontent:
                    break
            except Exception as e:
                logger.warn("reply_image_rawdata download img error, retry count={}".format(retry_count))

        imgcontent = base64.b64encode(imgcontent).decode()
        return {"completion_images": 1, "content": imgcontent}

