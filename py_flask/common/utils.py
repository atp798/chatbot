import re
from common.log import logger
import requests
from thefuzz import fuzz
from thefuzz import process

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
        data = response.json()['data']
        titles_dict = {d['title']: d for d in data}
        titles = titles_dict.keys()
        titles_scores = [fuzz.partial_token_set_ratio(t) for t in titles]
        logger.info("google search titles={} scores={}".format(titles, titles_scores))
        max_score = max(titles_scores)
        best_title = titles[ [i for i in range(0, len(titles_scores)) if titles_scores[i] == max_score][0] ]
        logger.info("google search best_title={} content={}".format(best_title, titles_dict[best_title]))
        #logger.info("google search res json:{}".format(response.json()))
        return titles_dict[best_title]
    except Exception as e:
        logger.exception(e)
        return None

if __name__ == '__main__':
    print(is_chinese("ssdfdf"))
    print(is_chinese("水电费"))