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
import re


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

                #意图判断
                context = {}
                context['session_id'] = session_id
                context['type'] = "TEXT" #text without session
                context['loginfo'] = loginfo
                response = self._bot.reply(
                    'Given a sentence "' + query + '"，' + 
                    'answer two questions: 1. Is this sentence just a request for drawing? 2. Is this sentence suitable for 18 years old? Return two answers, each answer should not exceed one word, and the answer should be either YES, NO, or UNCERTAIN'
                    , context)
                res = re.findall(r'\b(YES|NO|UNCERTAIN)\b', response.upper())

                msgtype = "TEXT"
                if len(res) >= 2:
                    msgtype = "IMAGE_SD" if ("YES" in res[0]) and ("NO" not in res[1]) else msgtype
                    msgtype = "IMAGE_INAPPROPRIATE" if ("YES" in res[0]) and ("NO" in res[1]) else msgtype
                #loginfo.append("image_intent_res={}".format(response))
                loginfo.append("image_intent={}".format(res))
                loginfo.append("msgtype={}".format(msgtype))
                logger.info('begin process, {}'.format('; '.join(loginfo)))

                response = None
                if msgtype == "IMAGE_SD" :
                    #如果是绘画意图，则翻译成英语,再请求sd
                    context = {}
                    context['session_id'] = session_id
                    context['type'] = msgtype #text without session
                    context['loginfo'] = loginfo
                    context['height'] = request_json["height"]
                    context['width'] = request_json["width"]
                    context['steps'] = request_json["steps"]
                    #请求Stable Diffusion
                    response = self._bot.reply(query, context)
                elif msgtype == "IMAGE_INAPPROPRIATE":
                    msgtype = "TEXT"
                    response = "You requested inappropriate content to draw, please change a request."
                #默认文字请求
                else:
                    context = {}
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
        
    def run(self):
        self._app.run(host=self._ip_addr,
                      port=self._port,
                      debug=self._debug_mode)

    def __call__(self, environ, start_response):
        return self._app(environ, start_response)


# 启动 Flask 应用程序
if __name__ == "__main__":
    ChatServer(get_config()).run()
