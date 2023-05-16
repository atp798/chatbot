"""
channel factory
"""
from common import const


def create_bot(bot_type, conf_json):
    """
    create a channel instance
    :param channel_type: channel type code
    :return: channel instance
    """
    if bot_type == const.BAIDU:
        # Baidu Unit对话接口
        from bot.baidu.baidu_unit_bot import BaiduUnitBot
        return BaiduUnitBot(conf_json)

    elif bot_type == const.CHATGPT:
        # ChatGPT 网页端web接口
        from bot.chatgpt.chat_gpt_bot import ChatGPTBot
        return ChatGPTBot(conf_json)

    elif bot_type == const.OPEN_AI:
        # OpenAI 官方对话模型API
        from bot.openai.open_ai_bot import OpenAIBot
        return OpenAIBot(conf_json)
    raise RuntimeError
