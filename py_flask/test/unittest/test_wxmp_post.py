import requests
from dicttoxml import dicttoxml
import json

import os
import sys
sys.path.append(os.getcwd())

#from wxmp.wxmp_post2user import do_post_action


def post2test_serv():
    url = "http://128.1.41.43:9081/openai/session/wechat/chat-completion?signature=e6259740679387f90d2df613e00fb071b38776d7&timestamp=1679918602&nonce=1288599824&openid=oiJo_5lGFN1xwiQtvFxT2W_7N6v8"
    body={
        'ToUserName': 'gh_d583bbc11b80', 
        'FromUserName': 'oiJo_5lGFN1xwiQtvFxT2W_7N6v8', 
        'CreateTime': '1679918602', 
        'MsgType': 'text', 
        'Content': '你是gpt几？',
        'MsgId': '24050651727617347'
    }

    xml = dicttoxml(body, custom_root='xml', attr_type=False)
    print("post xml= ", xml)
    text = requests.post(url=url, data=xml)

    #text = requests.post(url=url, data=bytes(json.dumps(body, ensure_ascii=False), encoding='utf-8'))
    print("post res= ", text)
    return

def test_android_app_post():
    url = "http://chatbot.huago.app/openai/session/chat-completion"
    body = {
        "query": "help me to write a flask demo program",
        "session_id": "test_did",
        "msgtype" : "text"
    }

    res = requests.post(url=url, data=json.dumps(body), headers={'content-type':'application/json'})
    return res
    #do_post_action(url=url, body=body, retry=0)


if __name__ == '__main__':
    #post2test_serv()
    #test = test_android_app_post()
    #print(test.text)
    query="帮我我我画画衣服"
    #query="draw"
    msg = "IMAGE" if any(item in {'画'} for item in query[:4]) else 'text'
    msg = "IMAGE" if any(item.lower() in {'draw'} for item in query.split(' ')[:4]) else msg
    print('-----------------')
    print(query[:5])
    print(msg)
