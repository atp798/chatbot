import re
from common.log import logger
import requests
from thefuzz import fuzz
from thefuzz import process
import jieba
from rank_bm25 import BM25Okapi

def is_chinese(string):
    """
    判断字符串是否为中文
    """
    pattern = re.compile(r'[\u4e00-\u9fa5]')
    match = pattern.search(string)
    return match is not None


def relevance_by_bm25(query, docs):
    query_token = list(jieba.cut_for_search(query))
    doc_token = [list(jieba.cut_for_search(d)) for d in docs]
    bm25 = BM25Okapi(doc_token)
    return bm25.get_scores(query_token)

def get_google_search_content(query):
    try:
        url = 'http://127.0.0.1:8084/openai/session/google_search'
        headers = {'Content-Type': 'application/json'}
        data = {'query': query}
        response = requests.post(url, headers=headers, json=data)
        data = response.json()['data'][:3]
        titles_dict = {d['title']: d for d in data if len(d.get('content', "")) > 100}
        titles = list(titles_dict.keys())
        title_contents = [t + '\n\r' + titles_dict[t]['content'] for t in titles]

        #titles_scores_1 = [fuzz.partial_ratio(query, t) for t in titles]
        #titles_scores_2 = [fuzz.partial_ratio(query, t) for t in title_contents]
        #titles_scores = [titles_scores_1[i] + titles_scores_2[i] for i in range(0, len(titles_scores_1))]
        titles_scores = relevance_by_bm25(query, title_contents)

        logger.debug("google search titles={} scores={}".format(titles, titles_scores))
        max_score = max(titles_scores)
        best_title = titles[ [i for i in range(0, len(titles_scores)) if titles_scores[i] == max_score][0] ]
        logger.debug("google search best_title={} content={}".format(best_title, titles_dict[best_title]))
        #logger.info("google search res json:{}".format(response.json()))
        return titles_dict[best_title]
    except Exception as e:
        logger.exception(e)
        return None

if __name__ == '__main__':
    print(is_chinese("ssdfdf"))
    print(is_chinese("水电费"))