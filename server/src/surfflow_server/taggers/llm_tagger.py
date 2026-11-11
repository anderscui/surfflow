# coding=utf-8
from archaeo.llm_providers import BaseLlmProvider

from surfflow_server.taggers.base import BaseFileTagger


import json
import re
from typing import Any

# from .base import BaseFileTagger


# Original single-file prompt, unchanged.
SYSTEM_PROMPT = '''你是一个个人知识库的文件主题分类器。

根据文件名，从预定义标签中选择 0～5 个最合适的主题标签。

规则：
1. 只能选择预定义标签，标签名称必须完全一致。
2. 标签应反映文件的主要领域或主题。
3. 可以选择多个标签，但不要添加只有间接关联的标签。
4. 优先选择最有辨识度的标签，避免不必要的宽泛标签。
5. 如果文件名无法提供足够信息，返回空列表。
6. 不要创建新标签，不要猜测无法从文件名判断的内容。
7. 只返回 JSON，格式为 {"tags": [...]}。
'''


def _response_content(response: Any) -> Any:
    """Accept plain text, dict, Ollama response, or OpenAI ChatCompletion."""
    if isinstance(response, (str, bytes)):
        return response
    if isinstance(response, dict):
        if 'tags' in response:
            return response
        if 'message' in response:
            return _response_content(response['message'])
        if 'choices' in response:
            return _response_content(response['choices'][0]['message'])
        if 'content' in response:
            return response['content']
    if hasattr(response, 'message'):
        return _response_content(response.message)
    if hasattr(response, 'choices'):
        return _response_content(response.choices[0].message)
    if hasattr(response, 'content'):
        return response.content
    raise TypeError(f'Unsupported LLM response type: {type(response)!r}')


def _parse_tags(response: Any, allowed_tags: set[str]) -> list[str]:
    content = _response_content(response)
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    if isinstance(content, str):
        content = content.strip()
        match = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
        data = json.loads(content)
    else:
        data = content

    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object')
    tags = data.get('tags')
    if not isinstance(tags, list) or len(tags) > 5:
        raise ValueError(f'Expected tags list of length 0–5, got: {tags!r}')
    if any(not isinstance(tag, str) for tag in tags):
        raise ValueError('Every tag must be a string')
    unknown = set(tags) - allowed_tags
    if unknown:
        raise ValueError(f'LLM returned unknown tags: {sorted(unknown)!r}')
    return list(dict.fromkeys(tags))


class LlmFileTagger(BaseFileTagger):

    def __init__(
        self,
        provider: BaseLlmProvider,
        tags: list[str],
        *,
        think: bool = False,
        prompt_version: str='v1',
        chat_kwargs: dict[str, Any] | None = None,
    ):
        if not tags or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise ValueError('tags must be non-empty strings')
        if len(tags) != len(set(tags)):
            raise ValueError('tags must be unique')

        self.provider = provider
        self.tags = tags.copy()
        self.allowed_tags = set(tags)
        self.think = think
        self.prompt_version = prompt_version
        self.chat_kwargs = dict(chat_kwargs or {})
        if 'stream' in self.chat_kwargs or 'think' in self.chat_kwargs:
            raise ValueError('Set stream and think via LlmFileTagger arguments')

    @property
    def name(self) -> str:
        return (
            f'llm_file_tagger/{self.provider.model}'
            f'/think={str(self.think).lower()}/prompt={self.prompt_version}'
        )

    def tag(self, filename: str) -> list[str]:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError('filename must be a non-empty string')

        user_prompt = (
            f'预定义标签：\n{json.dumps(self.tags, ensure_ascii=False)}\n\n'
            f'文件名：{json.dumps(filename, ensure_ascii=False)}'
        )
        response = self.provider.chat(
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_prompt},
            ],
            stream=False,
            think=self.think,
            **self.chat_kwargs,
        )

        return _parse_tags(response, self.allowed_tags)


if __name__ == '__main__':
    from archaeo.llm_providers import OllamaProvider

    llm = OllamaProvider('gemma4:26b')
    tags = ['语言学习', '艺术', '绘画', '中国绘画', '书法', '摄影', '建筑', '电影', '音乐']
    tagger = LlmFileTagger(provider=llm, tags=tags)
    print(tagger.tag('摄影构图学_重排版 (Ben Clements, David Rosenfeld, 2011).pdf'))
