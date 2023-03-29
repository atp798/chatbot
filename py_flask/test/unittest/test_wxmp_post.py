import requests
from dicttoxml import dicttoxml
import json

def get_welcome_words():
    return '''
嗨，你好！我是全世界最聪明的聊天机器人“机器知心”，接下来我会一直陪着你解答你的任何问题，比如你可以问我：“外星人真实存在吗？”

问题1：外星人真实存在吗？
问题2：三星堆文化来自何方？
问题3：请帮我列出双色球的预测方法？
问题4：怎么做辣椒炒肉？
问题5：怎么吃减肥最快？

你也可以向我提出画图的问题，只要以画开头提问就好了，比如：
问题1：画一只正在玩球的金毛
问题2：画一个写作业的小学生
'''

url = "http://128.1.41.43:9081/openai/session/wechat/chat-completion?signature=e6259740679387f90d2df613e00fb071b38776d7&timestamp=1679918602&nonce=1288599824&openid=oiJo_5lGFN1xwiQtvFxT2W_7N6v8"
body={'ToUserName': 'gh_d583bbc11b80', 'FromUserName': 'oiJo_5lGFN1xwiQtvFxT2W_7N6v8', 'CreateTime': '1679918602', 
      'MsgType': 'text', 
      'Content': '4444',
      'MsgId': '24050651727617347'}

#xml = dicttoxml(body, custom_root='xml', attr_type=False)
#print("post xml= ", xml)
#text = requests.post(url=url, data=xml)

text = requests.post(url=url, data=bytes(json.dumps(body, ensure_ascii=False), encoding='utf-8'))
print("post res= ", text)

'''
print('-------------')
whitelist_url = 'https://github.com/atp798/chatbot/blob/main/py_flask/common/wxmp_whitelist.json'
username = 'your_username'
# 发送请求并获取响应
response = requests.get(whitelist_url)

# 解析响应并打印结果
if response.status_code == 200:
    print(response.json())
else:
    print('请求失败，状态码：', response.status_code)
'''



