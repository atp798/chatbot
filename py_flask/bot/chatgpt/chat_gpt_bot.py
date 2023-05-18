from common import const
from bot.bot import Bot
from common.log import logger
from common.token_bucket import TokenBucket
from common.expired_dict import ExpiredDict
import openai
import time
import requests
import io
from config import get_config
import base64
import json
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from common.session_manager import SessionManager
from config import conf
from common import intent_analysis


# OpenAI对话模型API (可用)
class ChatGPTBot(Bot):

    def __init__(self, conf_json):
        logger.info("bot is starting...")
        openai.api_key = conf_json.get('open_ai_api_key')
        self._session = SessionManager(ChatGPTSession, model="gpt-3.5-turbo")

        self._enable_rate_limit = False
        if conf_json.get('rate_limit_chatgpt', 0) > 0:
            self._enable_rate_limit = True
            self._tb4chatgpt = TokenBucket(conf_json.get('rate_limit_chatgpt'))
        if len(conf_json.get('clear_memory_commands')) > 0:
            self._clear_memory_commands = conf_json.get('clear_memory_commands', 'clear memory')

    def save_session(self, session_id, reply_text, count):
        self._session.session_reply(reply_text, session_id, count)

    def clear_session(self, session_id):
        self._session.clear_session(session_id)

    def reply(self, query, context=None):
        # acquire reply content
        '''
            type and session_id is important in context!!!
            type is TEXT by default
        '''
        msgtype = context.get('type', None)
        if msgtype is None:
            logger.warn("[OPEN_AI] error request, no msgtype!")
            return {"content":""}

        if not 'loginfo' in context:
            context['loginfo'] = []
        loginfo = context.get('loginfo')

        #问答类的，需要组织session，画图的暂时不需要
        session_id = context.get('session_id', None)  #可能为空
        if msgtype == const.TEXT or msgtype == const.TEXT_ONCE:
            if query == self._clear_memory_commands:
                self._session.clear_session(session_id)
                return {'content':'memory cleared'}
            session = self._session.session_query(query, session_id, context.get('system_prompt', None))
            if session is None:
                return {'content':"Build session failed, query is tooooo long"}

        btime = time.time()

        reply_content = {}
        if msgtype == const.IMAGE:
            reply_content = self.reply_image(query, 0)
        elif msgtype == const.IMAGE_RAW:
            reply_content = self.reply_image_rawdata(query)
        elif msgtype == const.IMAGE_SD:
            reply_content = {"content": self.request_sd_image(query, context)}
        elif msgtype == const.TEXT_ONCE:
            #对于text once请求，要求他的结果尽量确定，并且不污染session
            reply_content = self.reply_text(session.messages, session_id, retry_count=0, strict_completion=True)
            logger.debug("openai replay_text, content=[{}]".format(reply_content["content"].replace('\n', ' ').replace('\r', ' ')))
            #if reply_content["completion_tokens"] > 0:
                #self._session.session_reply(reply_content["content"], session_id, reply_content["total_tokens"], 1024)
        else: #msgtype == const.TEXT:
            reply_content = self.reply_text(session.messages, session_id, 0)
            if reply_content["completion_tokens"] > 0:
                self._session.session_reply(reply_content["content"], session_id, reply_content["total_tokens"])
            logger.debug("openai replay_text, content=[{}]".format(reply_content["content"].replace('\n', ' ').replace('\r', ' ')))

        tdiff = time.time() - btime
        loginfo.append("openai_query=[{}], openai_msgtype={}, openai_time={}".format(query[:5], msgtype, int(tdiff * 1000)))
        return reply_content

    def reply_text(self, session, session_id, retry_count=0, strict_completion=False) -> dict:
        '''
        call openai's ChatCompletion to get the answer
        :param session: a conversation session
        :param session_id: session id
        :param retry_count: retry count
        :return: {}
        '''
        try:
            if strict_completion:
                #logger.info("tandebug strict_completion, session={}".format(session))
                response = openai.ChatCompletion.create(
                model= get_config().gpt_model,  # 对话模型的名称
                messages=session,
                temperature=0.2,  # 值在[0,1]之间，越大表示回复越具有不确定性
                top_p=1,
                frequency_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                presence_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                )
            else:
                #logger.info("tandebug , session={}".format(session))
                response = openai.ChatCompletion.create(
                model= get_config().gpt_model,  # 对话模型的名称
                messages=session,
                temperature=0.6,  # 值在[0,1]之间，越大表示回复越具有不确定性
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
            self.clear_session(session_id)
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
    
    def request_sd_image(self, prompt, context):
        loginfo = context.get('loginfo', [])
        prompt = intent_analysis.content_extractor_english.do_analyse(prompt, loginfo)
        loginfo.append("image_query=[{}]".format(prompt))

        height = context.get("height")
        width = context.get("width")
        steps = context.get("steps")
        url = "http://106.75.25.171:8989/sdapi/v1/txt2img"
        body = {
            "prompt": prompt + ",(masterpiece:1.2, best quality),((iphone wallpaper)),4K,8K,high quality",
            "negative_prompt": ('(no clothes:1.1),(naked:1.2),(nsfw:1.2),(multi hands),(worst quality, low quality:1.4),'
                                '(extra fingers),(extra hands),(mutated hands and finger),(ugly eyes:1.2),(fused fingers),(long neck:1.2)",'
                                '(texts words watermarks:1.1)'
                                ),
            "height": 768,
            "width": 512,
            "steps": 20,
            "restore_faces": True,
            "sampler_name": "DPM++ 2M Karras",
            "cfg_scale": 7
        }

        res = requests.post(url=url, data=json.dumps(body), headers={'content-type':'application/json'})
        res = res.json()['images'][0]
        #res = base64.b64encode(res).decode()
        return res

