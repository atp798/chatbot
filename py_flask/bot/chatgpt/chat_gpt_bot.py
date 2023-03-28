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
        '''
        msgtype = context.get('type')
        msgtype = "IMAGE" if query.startswith("画") else msgtype
        if msgtype is None:
            return ""

        logger.info("[OPEN_AI] begin process query={}".format(query))
        session_id = context.get('session_id')

        if query == self._clear_memory_commands:
            self._session.clear_session(session_id)
            return '会话已清除'
        if query == self._clear_all_memory_commands:
            self._session.clear_all_session()
            return '所有人会话历史已清除'

        session = self._session.build_session_query(query, session_id, msgtype)
        if session is None:
            prefix = "文字对话" if msgtype == "TEXT" else ""
            prefix = "画图对话" if msgtype == "IMAGE" else ""
            return prefix+"请求已经达到最大次数，请明天再来..."

        logger.debug("[OPEN_AI] session query={}".format(session))

        btime = time.time()
        if msgtype == "TEXT":
            reply_content = self.reply_text(session, session_id, 0)
            if reply_content["completion_tokens"] > 0:
                self._session.save_session(reply_content["content"], session_id, reply_content["total_tokens"])

        if msgtype == "IMAGE":
            reply_content = self.reply_image(query, 0)

        tdiff = time.time() - btime
        logger.info("[OPEN_AI] end process query={}, time={}".format(query, int(tdiff * 1000)))
        return reply_content["content"]

    def reply_text(self, session, session_id, retry_count=0) -> dict:
        '''
        call openai's ChatCompletion to get the answer
        :param session: a conversation session
        :param session_id: session id
        :param retry_count: retry count
        :return: {}
        '''
        try:
            btime = time.time()
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # 对话模型的名称
                messages=session,
                temperature=0.6,  # 值在[0,1]之间，越大表示回复越具有不确定性
                #max_tokens=4096,  # 回复最大的字符数
                top_p=1,
                frequency_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                presence_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            )
            tdiff = time.time() - btime
            logger.info("[openai] openai.ChatCompletion.create time={}".format(int(tdiff * 1000)))
            # logger.info("[ChatGPT] reply={}, total_tokens={}".format(response.choices[0]['message']['content'], response["usage"]["total_tokens"]))
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
                logger.warn("[OPEN_AI] RateLimit exceed, 第{}次重试".format(retry_count + 1))
                return self.reply_text(session, session_id, retry_count + 1)
            else:
                return {"completion_tokens": 0, "content": "提问太快啦，请休息一下再问我吧"}
        except openai.error.APIConnectionError as e:
            # api connection exception
            logger.warn(e)
            logger.warn("[OPEN_AI] APIConnection failed")
            return {"completion_tokens": 0, "content": "我连接不到你的网络"}
        except openai.error.Timeout as e:
            logger.warn(e)
            logger.warn("[OPEN_AI] Timeout")
            return {"completion_tokens": 0, "content": "我没有收到你的消息"}
        except Exception as e:
            # unknown exception
            logger.exception(e)
            Session.clear_session(session_id)
            return {"completion_tokens": 0, "content": "请再问我一次吧"}

    def reply_image(self, query, retry_count=0):
        try:
            logger.info("[OPEN_AI] image_query={}".format(query))
            response = openai.Image.create(
                prompt=query,    #图片描述
                n=1,             #每次生成图片的数量
                size="1024x1024"   #图片大小,可选有 256x256, 512x512, 1024x1024
            )
            image_url = response['data'][0]['url']
            logger.info("[OPEN_AI] image_url={}".format(image_url))
            return {"completion_images": 1, "content": image_url}

        except openai.error.RateLimitError as e:
            logger.warn(e)
            if retry_count < 1:
                time.sleep(5)
                logger.warn("[OPEN_AI] ImgCreate RateLimit exceed, 第{}次重试".format(retry_count+1))
                return self.create_img(query, retry_count+1)
            else:
                return "请求太快啦，请休息一下再问我吧"