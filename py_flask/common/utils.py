import re

def is_chinese(string):
    """
    判断字符串是否为中文
    """
    pattern = re.compile(r'[\u4e00-\u9fa5]')
    match = pattern.search(string)
    return match is not None


if __name__ == '__main__':
    print(is_chinese("ssdfdf"))
    print(is_chinese("水电费"))