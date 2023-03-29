import requests
import json
import base64


def get_whitelist_from_github(url="https://api.github.com/repos/atp798/chatbot/contents/py_flask/common/wxmp_whitelist.json"):
    try:
        response = requests.get(url)
        json_data = json.loads(response.content)
        content = json_data['content']
        decoded_content = base64.b64decode(content).decode('utf-8')
        json_obj = json.loads(decoded_content)
        return json_obj
    except Exception as e:
        return None

print(get_whitelist_from_github())