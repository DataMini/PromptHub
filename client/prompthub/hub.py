import requests
from jinja2 import Template, Environment, meta
from typing import List, Dict, Any, Optional
from . import errors


def find_jinja2_variables(template_str):
    """
    分析Jinja2模板字符串，返回模板中使用的所有变量。

    :param template_str: Jinja2模板字符串
    :return: 模板中使用的变量集合
    """
    env = Environment()
    # 将模板字符串解析为AST
    parsed_content = env.parse(template_str)
    # 使用meta模块找到所有未声明的变量
    undeclared_variables = meta.find_undeclared_variables(parsed_content)
    return undeclared_variables


class HTTPClient:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None

    def request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None,
                params: Optional[Dict[str, str]] = None, data=None) -> Any:
        try:
            response = self.session.request(method, url, headers=headers, params=params, data=data)
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.exceptions.ConnectionError:
            raise errors.ConnectionError
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise errors.NotFoundError
            elif e.response.status_code == 401:
                raise errors.UnauthorizedError
            else:
                raise errors.PromptsHubError(e)


class PromptTemplate:
    def __init__(self, id: int, name: str, text: str, output_format: str,
                 models: List[Dict[str, Any]], labels: List[Dict[str, Any]], url: str, api_url: str):
        self.id = id
        self.name = name
        self.text = text
        self.output_format = output_format
        self.models = models
        self.labels = labels
        self.url = url
        self.api_url = api_url


class Prompt:
    def __init__(self, name: str, text: str, output_format: str,
                 model: Optional[str] = None, template: PromptTemplate = None):
        self.name = name
        self.text = text
        self.content = text
        self.output_format = output_format
        self.model = model
        self.template = template


class PromptHub:

    def __init__(self, url: str, token: str, category: str):
        self.base_url = url
        self.headers = {'Authorization': f'Token {token}'}
        self.http_client = HTTPClient()

        self.category_name = None
        self.category_id = None
        self.set_category(category)

        # 最好是 3.5，其次是 4，如果这两个都没有，则使用任意一个 Prompt 所适用的 Model
        self.preferred_models = ['gpt-3.5', 'gpt-4', 'any']

    def set_category(self, category: str) -> None:
        resp = self.get_request(f"{self.base_url}/api/categories/", {'name': category})
        if not resp:
            raise errors.CategoryNotFoundError
        self.category_name = category
        self.category_id = resp[0]['id']

    def make_prompt_url(self, prompt_id: int) -> str:
        return f"{self.base_url}/categories/{self.category_id}/prompts/{prompt_id}/"

    def make_prompt_api_url(self, prompt_id: int = None) -> str:
        if prompt_id is None:
            return f"{self.base_url}/api/categories/{self.category_id}/prompts/"
        else:
            return f"{self.base_url}/api/categories/{self.category_id}/prompts/{prompt_id}/"

    def set_preferred_models(self, preferred_models: List[str]) -> None:
        self.preferred_models = [model.lower() for model in preferred_models]

    def get_request(self, url: str, params=None) -> Any:
        response = self.http_client.request('GET', url, headers=self.headers, params=params)
        return response

    def post_request(self, url: str, data=None) -> Any:
        response = self.http_client.request('POST', url, headers=self.headers, data=data)
        return response

    def delete_request(self, url: str) -> Any:
        response = self.http_client.request('DELETE', url, headers=self.headers)
        return response

    def get(self, prompt_name: str, raise_if_missing_variables: bool = True, **variables) -> Prompt:

        prompt_template = self.get_template(prompt_name)

        template = Template(prompt_template.text)
        missing_variables = [var for var in find_jinja2_variables(prompt_template.text) if var not in variables]
        if missing_variables and raise_if_missing_variables:
            raise errors.PromptMissingVariablesError(missing_variables)

        content = template.render(**variables)
        model_names = [model['name'] for model in prompt_template.models]
        model = self._get_valid_model(model_names)
        return Prompt(prompt_name, content, prompt_template.output_format, model,
                      template=prompt_template)

    def _get_valid_model(self, valid_model_names: List[str]) -> Optional[str]:
        # 从 Prompt 所适用的 Model 列表中获取一个自己最想要的 Model
        # Prompt's available models: all, gpt-4 （如果有all，则说明任何一个都可以）
        # Preferred models: gpt-3.5, gpt-4, any（优先级从高到低，如果有any，则说明可以使用任意一个）
        if 'all' in valid_model_names:
            return self.preferred_models[0]
        for preferred_model in self.preferred_models:
            if preferred_model == 'any':
                return valid_model_names[0] if valid_model_names else None
            if preferred_model in valid_model_names:
                return preferred_model
        if 'any' not in self.preferred_models:
            raise errors.NoValidModelError(f"Preferred models {self.preferred_models} "
                                           f"not found in Prompt's available models {valid_model_names}")
        return None

    def get_template(self, prompt_name: str) -> PromptTemplate:
        # uri = f"/api/categories/{self.category_name}/prompts/"
        prompts = self.get_request(self.make_prompt_api_url(), {'name': prompt_name})
        if not prompts:
            raise errors.PromptNotFoundError(f"Prompt '{prompt_name}' not found in category '{self.category_name}'")
        prompt_data = prompts[0]
        prompt_data['url'] = self.make_prompt_url(prompt_data['id'])
        prompt_data['api_url'] = self.make_prompt_api_url(prompt_data['id'])
        return PromptTemplate(**prompt_data)

    def create_template(self, name: str, text: str, output_format: str = "str",
                        model_names: List[str] = None, label_names: List[str] = None) -> PromptTemplate:
        resp = self.post_request(
            self.make_prompt_api_url(),
            data={'name': name,
                  'text': text,
                  'output_format': output_format,
                  'model_names': model_names,
                  'label_names': label_names,
                  }
        )
        resp['url'] = self.make_prompt_url(resp['id'])
        resp['api_url'] = self.make_prompt_api_url(resp['id'])
        return PromptTemplate(**resp)

    def delete_template(self, prompt_name: str) -> None:
        template = self.get_template(prompt_name)
        self.delete_request(template.api_url)
