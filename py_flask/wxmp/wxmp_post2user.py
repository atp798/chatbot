import json
import time
import threading
import os
import sys
sys.path.append(os.getcwd())
from common.log import logger
import requests
from flask import jsonify
import traceback
from wxmp.wxmp_access_token import get_wxmp_token

def do_post_action(url="", body={}, retry=0):
    try:
        res = requests.post(url=url, data=bytes(json.dumps(body, ensure_ascii=False), encoding='utf-8'))
        logger.info("post msg to wxmp, status={}, could retry {} times".format(res.text, retry)) 
        if json.loads(res.text).get('errcode') != 0 and retry > 0:
            return do_post_action(url, body, retry - 1)
    except Exception as e:
        traceback.print_exc()
        if retry > 0:
            return do_post_action(url, body, retry - 1)
        return False

def post_respons2wxmp(res=None, touser=None, retry=0):
    if not(res and touser):
        return False
    access_token = get_wxmp_token()
    url='https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=' + access_token + "&charset=utf-8";
    body={
        "touser": touser, 
        "msgtype": "text", 
        "text": {
            "content": res
            }
    }
    return do_post_action(url=url, body=body, retry=5)

def post_img_respons2wxmp(image_url=None, touser=None, retry=0):
    if not(image_url and touser):
        return False
    access_token = get_wxmp_token()
    try:
        local_path = '/var/tmp/' + touser + '_' + str(int(time.time() * 1000)) + '.png'
        download_image(image_url, local_path)
        media_id = img_upload(local_path)
        delete_image(local_path)
    except Exception as e:
        logger.info('error update image to wx:'.format(e))
        return False

    url='https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=' + access_token
    body = {
        "touser": touser,
        "msgtype": "image",
        "image": {
            "media_id": media_id
        }
    }
    return do_post_action(url=url, body=body, retry=5)

def img_upload(local_path):
    access_token = get_wxmp_token()
    url = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token=%s&type=%s" % (access_token, "image")
    files = {'media': open('{}'.format(local_path), 'rb')}
    res = requests.post(url, files=files)
    content = json.loads(res.content.decode())
    logger.info("upload image, res={}content={}".format(res, content))
    return content['media_id']

def download_image(img_url, local_path):
    with open(local_path, "wb") as f:
        f.write(requests.get(img_url).content)

def delete_image(local_path):
    if not local_path:
        return
    os.remove(local_path)

if __name__ == '__main__':
    post_respons2wxmp("test中文", "oiJo_5lGFN1xwiQtvFxT2W_7N6v8")
