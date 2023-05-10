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
        return True
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

    #一次发送512长度
    once_len = 680
    while len(res) > 0:
        body={
            "touser": touser, 
            "msgtype": "text", 
            "text": {
                "content": res[:once_len]
                }
        }
        ret = do_post_action(url=url, body=body, retry=5)
        if ret == False: #上一次发送失败了，直接退出
            return ret
        res = res[once_len:]

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

def post_img_respons2wxmp_SD(image_base64=None, touser=None, retry=0):
    if not(image_base64 and touser):
        return False
    access_token = get_wxmp_token()
    try:
        local_path = '/var/tmp/' + touser + '_' + str(int(time.time() * 1000)) + '.png'
        with open(local_path, "wb") as f:
            f.write(image_base64)
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

    ss='''清明节是中国传统的重要节日之一，也是中华民族的传统文化遗产之一。每年的清明节，人们都会祭拜祖先、扫墓祭奠，以表达对逝去亲人的思念之情。同时，清明节也是人们缅怀历史、追思先贤的时刻，是中华民族的文化传承和精神纽带。本文将从历史、文化和现代意义三个方面来探讨清明节的主题。

历史方面，清明节的起源可以追溯到古代的春秋时期。据史书记载，春秋时期的鲁国公族孔氏，以祭祀先祖为主要活动，每年清明时节都会进行祭祀活动。孔子也曾经在清明节时到墓地祭拜先人，并感叹：“知者不惑，仁者不忧，勇者不惧。”这句话意味深长，表达了对先贤的敬仰和缅怀之情。随着时间的推移，清明节逐渐成为了全国性的传统节日，成为了人们缅怀历史、追思先贤的重要时刻。

文化方面，清明节也是中国传统文化的重要组成部分之一。在中国传统文化中，祭祀祖先是一种重要的文化习俗。清明节期间，人们会扫墓祭奠，为先人烧纸钱、焚香祷告，以表达对先人的敬仰和怀念之情。此外，清明节还有一些与民间文化相关的活动，比如踏青、放风筝等，这些活动都是人们在缅怀先人的同时，也在感受生活的美好和自然的神秘。

现代意义方面，清明节也有着重要的现代意义。随着社会的发展，人们对清明节的认识和理解也在不断深化。在现代社会中，人们不仅仅是在缅怀先人，更是在弘扬中华民族的优秀传统文化。清明节不仅仅是一个传统节日，更是一个文化载体，是中华民族的文化遗产和精神纽带。在这个节日里，人们可以感受到中华民族的文化底蕴和精神力量，也可以通过祭祀先人，表达对传统文化的尊重和珍视。

总之，清明节作为中国传统的重要节日，不仅有着深厚的历史渊源和文化底蕴，更有着重要的现代意义。在这个节日里，人们可以缅怀历史、追思先贤，也可以感受生活的美好和自然的神秘。同时，清明节也是中华民族的文化传承和精神纽带，是我们珍视和发扬的重要文化遗产。希望在未来的日子里，人们能够更加重视传统文化，弘扬民族精神，让清明节这个传统节日在现代社会中焕发出新的光彩。
'''

    sss = '123456'
    print(sss[:2], '--------', sss[2:])
    post_respons2wxmp(ss, "oiJo_5lGFN1xwiQtvFxT2W_7N6v8")
