import argparse
from common.log import logger
from common import const
from flask import Flask, request, jsonify
import openai
import os
from config import get_config
from bot.bot_factory import create_bot
import xmltodict
from wxmp.wxmp_main import process_wxmp_request
import threading
import traceback
import requests
import json
import time
from common import utils

class ChatServer:

    def __init__(self, config_parser):
        logger.info("Chat server is init...")
        self._app = Flask(__name__)
        self._debug_mode = config_parser.debug_mode
        self._ip_addr = config_parser.ip_addr
        self._port = config_parser.port
        self._bot = create_bot(const.CHATGPT, config_parser)

        def debug_request(req):
            print("----- get headers:")
            print(req.headers)
            print("----- get body")
            print(req.data)
            print("----- get form:")
            print(req.form)
            print("----- get json:")
            print(request.get_json())

        @self._app.route("/openai/text-completion", methods=["POST"])
        def text_completion():
            if self._debug_mode:
                debug_request(request)

            #parameter constant
            PROMPT = "prompt"

            request_json = request.get_json()
            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if PROMPT not in request_json:
                return jsonify({"code": 301, "msg": "empty prompt"})

            prompt = request_json[PROMPT]

            if len(prompt) == 0:
                return jsonify({"code": 301, "msg": "empty prompt"})

            response = None
            result = ""
            try:
                # 调用 OpenAI API
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=1024,
                    n=1,
                    stop=None,
                    temperature=0.2,
                )
                # 从响应中获取结果
                result = response.choices[0].text.strip()
            except Exception:
                if self._debug_mode:
                    print(response)
                return jsonify({"code": 302, "msg": "internal error"})

            return jsonify({"code": 200, "msg": "success", "data": result})

        @self._app.route("/openai/chat-completion", methods=["POST"])
        def chat_completion():
            if self._debug_mode:
                debug_request(request)

            #parameter constant
            CHAT_HISTORY = "chat_history"

            request_json = request.get_json()
            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if CHAT_HISTORY not in request_json:
                return jsonify({"code": 301, "msg": "empty chat history"})
            chat_history = request_json[CHAT_HISTORY]

            response = None
            result = ""
            try:
                # 调用 OpenAI API
                response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                        messages=chat_history,
                                                        temperature=0.2,
                                                        max_tokens=1024,
                                                        top_p=1,
                                                        frequency_penalty=0,
                                                        presence_penalty=0,
                                                        stop=None)
                # 从响应中获取结果
                result = response.choices[0].message.content
            except Exception:
                if self._debug_mode:
                    print(response)
                return jsonify({"code": 302, "msg": "internal error"})

            # 返回结果到客户端
            return jsonify({"code": 200, "msg": "success", "data": result})

        @self._app.route("/openai/session/chat-completion", methods=["POST"])
        def session_chat_completion():
            if self._debug_mode:
                debug_request(request)
                
            request_json = request.get_json()
            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if "query" not in request_json or not isinstance(request_json["query"], str):
                return jsonify({"code": 301, "msg": "empty query"})
            if "session_id" not in request_json or not isinstance(request_json["session_id"], str):
                return jsonify({"code": 301, "msg": "empty session id"})

            try:
                #构建请求chatgpt的query
                query = request_json["query"]
                session_id = request_json["session_id"]
                msgtype = request_json.get('msgtype', "text").upper()
                msgtype = "IMAGE_RAW" if query.startswith(("画","draw","Draw","帮我画")) else msgtype

                context = dict()
                context['session_id'] = session_id
                context['type'] = msgtype

                #请求chatgpt 
                response = self._bot.reply(query, context)
                # 返回结果到客户端
                return jsonify({"code": 200, "msg": "success", "data": response, "msgtype": msgtype})
            except Exception:
                traceback.print_exc()
                return jsonify({"code": 302, "msg": "internal error"})
            
        @self._app.route("/openai/session/chat-completion-v2", methods=["POST"])
        def session_chat_completion_v2():
            if self._debug_mode:
                debug_request(request)

            loginfo = []
            request_json = request.get_json()
            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if "query" not in request_json or not isinstance(request_json["query"], str):
                return jsonify({"code": 301, "msg": "empty query"})
            if "session_id" not in request_json or not isinstance(request_json["session_id"], str):
                return jsonify({"code": 301, "msg": "empty session id"})

            try:
                #构建请求chatgpt的query
                query = request_json["query"]
                session_id = request_json["session_id"]
                loginfo.append("raw_query=[{}]".format(query))
                loginfo.append("session_id={}".format(session_id))
                logger.info('begin process, {}'.format('; '.join(loginfo)))

                #意图判断
                context = dict()
                context['session_id'] = session_id
                context['type'] = "TEXT_ONCE" #text without session
                context['loginfo'] = loginfo

                response = self._bot.reply('Tell me: 1. If the content below is a drawing request; 2. If the content is appropriate for a 13 years old. Answer me just in one word in "YES NO UNKNOWN" as a list: ' + query, context)
                res = response.strip().split('\n')
                msgtype = "TEXT"
                if len(res) == 2:
                    msgtype = "IMAGE_SD" if "YES" in res[0] and (not "NO" in res[1]) else msgtype
                loginfo.append("image_intent={}".format(res))
                loginfo.append("msgtype={}".format(msgtype))

                response = None
                if msgtype == "IMAGE_SD" :
                    #如果是绘画意图，则翻译成英语
                    context = dict()
                    context['session_id'] = session_id
                    context['type'] = "TEXT_ONCE" #text without session
                    context['loginfo'] = loginfo
                    #请求chatgpt进行翻译
                    response = self._bot.reply('This is a request for a drawing AI, tell me what needs to be drawn in the request in English, answer me start with "Draw":' + query, context)
                    query = response.strip('"')
                    parts = query.split('Draw', 1)
                    query = query if len(parts) < 2 else parts[1].strip()
                    loginfo.append("image_query=[{}]".format(query))

                    height = request_json["height"]
                    width = request_json["width"]
                    steps = request_json["steps"]
                    #请求Stable Diffusion
                    response = request_sd_image(query, height, width, steps)
                elif msgtype == "TEXT":
                    context = dict()
                    context['session_id'] = session_id
                    context['type'] = msgtype
                    context['loginfo'] = loginfo
                    #请求chatgpt
                    response = self._bot.reply(query, context)

                logger.info("end process, {}".format('; '.join(loginfo)))
                # 返回结果到客户端
                return jsonify({"code": 200, "msg": "success", "data": response, "msgtype": msgtype})
            except Exception:
                traceback.print_exc()
                logger.info("end process, {}".format('; '.join(loginfo)))
                return jsonify({"code": 302, "msg": "internal error"})

        @self._app.route("/openai/session/wechat/chat-completion", methods=["GET"])
        def do_wechat_check():
            logger.info("echostr +++ {}".format(request.args.get("echostr")))
            #return jsonify({"code": 200, "msg": "success", "data": request.args.get("echostr")})
            return request.args.get("echostr"), 200

        @self._app.route("/openai/session/wechat/chat-completion", methods=["POST"])
        def session_wechat_chat_completion():
            if self._debug_mode:
                debug_request(request)

            request_json = xmltodict.parse(request.data)['xml']
            threading.Thread(target=process_wxmp_request, args=(request_json, self._bot)).start()
            return "success", 200
        
        def request_sd_image(prompt, height, width, steps):
            url = "http://106.75.25.171:8989/sdapi/v1/txt2img"
            body = {
                "prompt": prompt + ",(masterpiece:1.2, best quality),((iphone wallpaper)),4K,8K,high quality",
                "negativePrompt": "(multi hands),(naked:1.1),(nsfw:1.1),(worst quality, low quality:1.4), EasyNegative, multiple views, multiple panels, blurry, watermark, letterbox, text, (nsfw, See-through:1.1),(extra fingers), (extra hands),(mutated hands and finger), (ugly eyes:1.2),mutated hands, (fused fingers), (too many fingers), (((long neck)))",
                "height": 768,
                "width": 512,
                "steps": steps,
                "restore_faces": True,
                "sampler_name": "DPM++ 2M Karras",
                "sd_model_checkpoint": "camelliamix_25d_v10.safetensors",
                "cfg_scale": 7
            }

            res = requests.post(url=url, data=json.dumps(body), headers={'content-type':'application/json'})
            return res.json()['images'][0]
    def run(self):
        self._app.run(host=self._ip_addr,
                      port=self._port,
                      debug=self._debug_mode)

    def __call__(self, environ, start_response):
        return self._app(environ, start_response)


# 启动 Flask 应用程序
if __name__ == "__main__":
    ChatServer(get_config()).run()
