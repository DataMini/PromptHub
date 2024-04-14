import os

from dotenv import load_dotenv

from unittest import TestCase
from client.prompthub import PromptHub

load_dotenv()


class TestPromptHub(TestCase):
    def test_prompt_hub(self):
        hub = PromptHub(
            # url='https://prompthub.dminfra.cn',
            url='http://127.0.0.1:8000',
            token=os.environ.get('TOKEN', ''),
            category=os.environ.get('CATEGORY'),
        )
        prompt = hub.get('hello')
        print(prompt.url)

