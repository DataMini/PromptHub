import os

from dotenv import load_dotenv

from unittest import TestCase
from client.prompthub import PromptHub

load_dotenv()


class TestPromptHub(TestCase):
    hub = PromptHub(
        # url='https://prompthub.dminfra.cn',
        url='http://127.0.0.1:8000',
        token=os.environ.get('TOKEN', ''),
        category=os.environ.get('CATEGORY'),
    )

    prompt_name = 'ut_test_prompt'

    def tearDown(self):
        self.hub.delete_template(self.prompt_name)

    def test_prompt(self):
        self.hub.create_template(self.prompt_name, 'hello world')
        prompt = self.hub.get(self.prompt_name)
        template = self.hub.get_template(self.prompt_name)
        print(template.text)
        print(prompt.url)
