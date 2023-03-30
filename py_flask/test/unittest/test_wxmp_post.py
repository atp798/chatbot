import requests
from dicttoxml import dicttoxml
import json




def post2test_serv():
    url = "http://128.1.41.43:9081/openai/session/wechat/chat-completion?signature=e6259740679387f90d2df613e00fb071b38776d7&timestamp=1679918602&nonce=1288599824&openid=oiJo_5lGFN1xwiQtvFxT2W_7N6v8"
    body={
        'ToUserName': 'gh_d583bbc11b80', 
        'FromUserName': 'oiJo_5lGFN1xwiQtvFxT2W_7N6v8', 
        'CreateTime': '1679918602', 
        'MsgType': 'text', 
        'Content': '写一首诗',
        'MsgId': '24050651727617347'
    }

    xml = dicttoxml(body, custom_root='xml', attr_type=False)
    print("post xml= ", xml)
    text = requests.post(url=url, data=xml)

    #text = requests.post(url=url, data=bytes(json.dumps(body, ensure_ascii=False), encoding='utf-8'))
    print("post res= ", text)
    return


if __name__ == '__main__':
    post2test_serv()