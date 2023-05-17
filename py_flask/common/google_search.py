import requests
import json
import spacy
import openai
import threading
import time
from bs4 import BeautifulSoup
from common.log import logger
from typing import Dict, Generator, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from bot.chatgpt.chat_gpt_session import num_tokens_from_messages

class GoogleSearch:
    def __init__(self, api_key, cx, openai_api_key):
        #self._google_search_api_key = config_parser.google_search_api_key
        #self._google_search_cx = config_parser.google_search_cx
        self._google_search_api_key = api_key
        self._google_search_cx = cx


    def scroll_to_percentage(self, driver: WebDriver, ratio: float) -> None:
        """Scroll to a percentage of the page

        Args:
            driver (WebDriver): The webdriver to use
            ratio (float): The percentage to scroll to

        Raises:
            ValueError: If the ratio is not between 0 and 1
        """
        if ratio < 0 or ratio > 1:
            raise ValueError("Percentage should be between 0 and 1")
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {ratio});")


    def create_message(self, chunk: str, question: str) -> Dict[str, str]:
        """Create a message for the chat completion

        Args:
            chunk (str): The chunk of text to summarize
            question (str): The question to answer

        Returns:
            Dict[str, str]: The message to send to the chat completion
        """
        return {
            "role": "user",
            "content": f'"""{chunk}""" Using the above text, answer the following'
            f' question: "{question}" -- if the question cannot be answered using the text,'
            " summarize the text.",
        }

    def split_text(self,
        text: str,
        max_length: int = 4096,
        model: str = "gpt-3.5-turbo",
        question: str = "",
    ) -> Generator[str, None, None]:
        """Split text into chunks of a maximum length

        Args:
            text (str): The text to split
            max_length (int, optional): The maximum length of each chunk. Defaults to 8192.

        Yields:
            str: The next chunk of text

        Raises:
            ValueError: If the text is longer than the maximum length
        """
        flattened_paragraphs = " ".join(text.split("\n"))
        nlp = spacy.load("en_core_web_sm")
        nlp.add_pipe("sentencizer")
        doc = nlp(flattened_paragraphs)
        sentences = [sent.text.strip() for sent in doc.sents]

        current_chunk = []

        for sentence in sentences:
            message_with_additional_sentence = [
                self.create_message(" ".join(current_chunk) + " " + sentence, question)
            ]

            expected_token_usage = (
                num_tokens_from_messages(messages=message_with_additional_sentence, model=model)
                + 1
            )
            if expected_token_usage <= max_length:
                current_chunk.append(sentence)
            else:
                yield " ".join(current_chunk)
                current_chunk = [sentence]
                message_this_sentence_only = [
                    self.create_message(" ".join(current_chunk), question)
                ]
                expected_token_usage = (
                    num_tokens_from_messages(messages=message_this_sentence_only, model=model)
                    + 1
                )
                if expected_token_usage > max_length:
                    raise ValueError(
                        f"Sentence is too long in webpage: {expected_token_usage} tokens."
                    )

        if current_chunk:
            yield " ".join(current_chunk)


    def process_chunk(self, i, index, summaries, chunk, question):
        btime = time.time()
        model = "gpt-3.5-turbo"
        messages = [self.create_message(chunk, question)]
        #tokens_for_chunk = num_tokens_from_messages(messages, model)

        summary = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )

        summaries[index] = summary.choices[0].message["content"]
        tdiff = time.time() - btime
        logger.info("text {} chunk {} len={} summarize_chunk_time={}".format(i, index, len(chunk),int(tdiff * 1000)))    

    def summarize_text(self, j,
        url: str, text: str, question: str, driver: Optional[WebDriver] = None
    ) -> str:
        """Summarize text using the OpenAI API

    Args:
        url (str): The url of the text
        text (str): The text to summarize
        question (str): The question to ask the model
        driver (WebDriver): The webdriver to use to scroll the page

    Returns:
        str: The summary of the text
    """
        if not text:
            return "Error: No text to summarize"

        model = "gpt-3.5-turbo"

        summaries = []
        chunks = list(
            self.split_text(
                text, max_length=4096, model=model, question=question
            ),
        )
        scroll_ratio = 1 / len(chunks)
        workers = []
        if len(chunks) > 1:
            for i, chunk in enumerate(chunks):
                if driver:
                    self.scroll_to_percentage(driver, scroll_ratio * i)
                summaries.append(i)
                thread = threading.Thread(target=self.process_chunk, args=(j, i, summaries, chunk, question,))
                thread.start()
                workers.append(thread)
        
            for thread in workers:
                thread.join()

            combined_summary = "\n".join(summaries)
            messages = [self.create_message(combined_summary, question)]
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )
        else:
            messages = [self.create_message(chunks[0], question)]
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )
    
    def request_link(self, link):
        res = requests.get(link)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.body.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk) 
        return text
    
    def process_link(self, i, link, rtn, query):
        btime = time.time()
        text = self.request_link(link)
        #summary = self.summarize_text(i, link, text, query)
        #content = json.loads(json.dumps(summary))["choices"][0]["message"]["content"]
        rtn["content"] = text
        tdiff = time.time() - btime
        logger.info("text {} len={} summarize_link_time={} link={}".format(i, len(text), int(tdiff * 1000), link))    

    def search(self, query):
        btime = time.time()
        url = "https://www.googleapis.com/customsearch/v1?key="+self._google_search_api_key+"&cx="+self._google_search_cx+"&q=" + query
        logger.info(f"google search api: {url}")
        res = requests.get(url)
        res = json.loads(res.text)
        if 'spelling' in res:
            query = res['spelling']['correctedQuery']
            url ="https://www.googleapis.com/customsearch/v1?key="+self._google_search_api_key+"&cx="+self._google_search_cx+"&q=" + query
            logger.info(f"google search api: {url}")
            res = requests.get(url)
            res = json.loads(res.text)

        data = res.get('items')
        results = []
        workers = []
        for i in range(len(data)):
            rtn = dict()
            rtn["title"] = data[i]["title"]
            results.append(rtn)
            thread = threading.Thread(target=self.process_link, args=(i, data[i]["link"],rtn,query, ))
            thread.start()
            workers.append(thread)
        
        for thread in workers:
            thread.join()

        rtnlen = len(results[0]["content"])
        index = 0
        for i, result in enumerate(results):
            l = len(result["content"])
            if abs(l-3000) < abs(rtnlen-3000):
                index = i
                rtnlen = l
        if len(results[index]["content"]) > 3500:
            results[index]["content"] = results[index]["content"][0: 3500]

        tdiff = time.time() - btime
        logger.info("search_time={} index={}".format(int(tdiff * 1000), index)) 
        return results[index]

