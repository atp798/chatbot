import argparse
from common.log import logger
from common import const
from flask import Flask, request, jsonify
import openai
import os
from config import get_config
from bot.bot_factory import create_bot
import xmltodict
from dict2xml import dict2xml
import time
import requests
import traceback


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

        @self._app.route("/openai/session/wechat/chat-completion",
                         methods=["GET"])
        def do_wechat_check():
            logger.info("echostr +++ {}".format(request.args.get("echostr")))
            #return jsonify({"code": 200, "msg": "success", "data": request.args.get("echostr")})
            return request.args.get("echostr"), 200

        @self._app.route("/openai/session/wechat/chat-completion",
                         methods=["POST"])
        def session_wechat_chat_completion():
            if self._debug_mode:
                debug_request(request)

            #parameter constant
            QUERY = "Content"
            SESSION_ID = "FromUserName"

            logger.info(
                "request={} headers={} reqpath={} args={} data={} form={}".
                format(request, request.headers, request.path, request.args,
                       request.data, request.form))
            request_json = xmltodict.parse(request.data)['xml']
            logger.info("request_json={}".format(request_json))

            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if QUERY not in request_json or not isinstance(
                    request_json[QUERY], str):
                return jsonify({"code": 301, "msg": "empty query"})
            if SESSION_ID not in request_json or not isinstance(
                    request_json[SESSION_ID], str):
                return jsonify({"code": 301, "msg": "empty session id"})

            session_id = request_json["FromUserName"]
            query = request_json["Content"]

            context = dict()
            context['session_id'] = session_id

            response = None
            result = ""
            try:
                response = self._bot.reply(query, context)
                # 从响应中获取结果
                result = response
            except Exception:
                if self._debug_mode:
                    print(response)
                return jsonify({"code": 302, "msg": "internal error"})

            res = {}
            res["ToUserName"] = request_json["FromUserName"]
            res["FromUserName"] = request_json["ToUserName"]
            res["CreateTime"] = int(time.time())
            res["MsgType"] = "transfer_customer_service"
            res["Content"] = result
            xml_res = {}
            xml_res["xml"] = res
            logger.info("response={} xml={}".format(result, dict2xml(xml_res)))

            # 返回结果到客户端
            return jsonify({"code": 200, "msg": "success", "data": result})

        @self._app.route("/openai/session/chat-completion", methods=["POST"])
        def session_chat_completion():
            if self._debug_mode:
                debug_request(request)
                
            #parameter constant
            QUERY = "query"
            SESSION_ID = "session_id"

            request_json = request.get_json()
            if len(request_json) == 0:
                return jsonify({"code": 301, "msg": "empty request"})
            if QUERY not in request_json or not isinstance(
                    request_json[QUERY], str):
                return jsonify({"code": 301, "msg": "empty query"})
            if SESSION_ID not in request_json or not isinstance(
                    request_json[SESSION_ID], str):
                return jsonify({"code": 301, "msg": "empty session id"})

            query = request_json[QUERY]
            session_id = request_json[SESSION_ID]

            context = dict()
            context['session_id'] = session_id

            response = None
            result = ""
            try:
                response = self._bot.reply(query, context)
                # 从响应中获取结果
                result = response
            except Exception:
                if self._debug_mode:
                    print(response)
                return jsonify({"code": 302, "msg": "internal error"})

            # 返回结果到客户端
            return jsonify({"code": 200, "msg": "success", "data": result})

    def run(self):
        self._app.run(host=self._ip_addr,
                      port=self._port,
                      debug=self._debug_mode)

    def __call__(self, environ, start_response):
        return self._app(environ, start_response)


# 启动 Flask 应用程序
if __name__ == "__main__":
    ChatServer(get_config()).run()
