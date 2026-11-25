# SurfFlow

Stream web data seamlessly into your local knowledge base.


```python
CHUNKING_CONFIG = {
    'strategy': 'paragraph',
    'max_chars': 3000,
    'overlap': 0,
    'version': 'v1',
}

EMBEDDING_CONFIG = {
    'provider': 'ollama',
    'model': 'qwen3-embedding:0.6b',
    'dimension': 1024,
}
```
