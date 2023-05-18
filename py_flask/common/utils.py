import re
from common.log import logger
import requests

def is_chinese(string):
    """
    判断字符串是否为中文
    """
    pattern = re.compile(r'[\u4e00-\u9fa5]')
    match = pattern.search(string)
    return match is not None

def get_google_search_content(query):
    try:
        url = 'http://127.0.0.1:8084/openai/session/google_search'
        headers = {'Content-Type': 'application/json'}
        data = {'query': query}
        response = requests.post(url, headers=headers, json=data)
        logger.info("google search res json:{}".format(response.json()))
        return response.json
    except Exception as e:
        logger.exception(e)
        return None

if __name__ == '__main__':
    print(is_chinese("ssdfdf"))
    print(is_chinese("水电费"))