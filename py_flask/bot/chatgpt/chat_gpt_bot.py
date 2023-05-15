
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
import json


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
            return ""

        if not 'loginfo' in context:
            context['loginfo'] = []
        loginfo = context.get('loginfo')

        #问答类的，需要组织session，画图的暂时不需要
        session_id = context.get('session_id', None)
        if session_id is None:
            return "Invalid session id"
        if msgtype == "TEXT" or msgtype == "TEXT_ONCE":
            if query == self._clear_memory_commands:
                self._session.clear_session(session_id)
                return 'memory cleared'
            session = self._session.build_session_query(query, session_id, msgtype) 
            if session is None:
                return "Build session failed, query is tooooo long"

        btime = time.time()
        if msgtype == "TEXT_ONCE":
            #对于text once请求，要求他的结果尽量确定，并且不污染session
            reply_content = self.reply_text(session, session_id, retry_count=0, strict_completion=True)
            if reply_content["completion_tokens"] > 0:
                self._session.save_session_by_count(reply_content["content"], session_id, reply_content["total_tokens"], 8)
        elif msgtype == "TEXT":
            reply_content = self.reply_text(session, session_id, 0)
            if reply_content["completion_tokens"] > 0:
                self._session.save_session(reply_content["content"], session_id, reply_content["total_tokens"])
        elif msgtype == "IMAGE":
            reply_content = self.reply_image(query, 0)
        elif msgtype == "IMAGE_RAW":
            reply_content = self.reply_image_rawdata(query)
        elif msgtype == "IMAGE_SD":
            reply_content = {"content": self.request_sd_image(query, context)} 

        tdiff = time.time() - btime
        loginfo.append("openai_query=[{}], openai_msgtype={}, openai_time={}".format(query, msgtype, int(tdiff * 1000)))
        return reply_content["content"]

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
    
    def request_sd_image(self, prompt, context):
        loginfo = context.get('loginfo', [])

        #请求chatgpt进行翻译
        context_tmp = {}
        context_tmp['session_id'] = "GPT_PRO_TRANSLATE_BOT_001"
        context_tmp['type'] = "TEXT_ONCE" #text without session
        response = self.reply(
            'The request is: "' + prompt + '". ' +
            'Tell me what needs to be drawn in the request in English, answer me start with "Draw":'
            , context_tmp)
        prompt = response.strip('"')
        parts = prompt.split('Draw', 1)
        prompt = prompt if len(parts) < 2 else parts[1].strip()
        loginfo.append("image_query=[{}]".format(prompt))

        height = context.get("height")
        width = context.get("width")
        steps = context.get("steps")
        url = "http://106.75.25.171:8989/sdapi/v1/txt2img"
        body = {
            "prompt": prompt + ",(masterpiece:1.2, best quality),((iphone wallpaper)),4K,8K,high quality",
            "negativePrompt": "(multi hands),(no clothes,naked:1.4),(nsfw:1.4),(worst quality, low quality:1.4), EasyNegative, multiple views, multiple panels, blurry, watermark, letterbox, text, (nsfw, See-through:1.1),(extra fingers), (extra hands),(mutated hands and finger), (ugly eyes:1.2),mutated hands, (fused fingers), (too many fingers), (((long neck)))",
            "height": 768,
            "width": 512,
            "steps": 20,
            "restore_faces": True,
            "sampler_name": "DPM++ 2M Karras",
            "sd_model_checkpoint": "camelliamix_25d_v10.safetensors",
            "cfg_scale": 7
        }

        res = requests.post(url=url, data=json.dumps(body), headers={'content-type':'application/json'})
        res = res.json()['images'][0]
        #res = base64.b64encode(res).decode()
        return res

