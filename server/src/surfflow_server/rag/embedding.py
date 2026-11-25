# coding=utf-8
from archaeo.llm_providers import OllamaProvider

from surfflow_server.embedders.text_embedders import LlmEmbedder

# _embedding_model = 'qwen3-embedding:8b'
# _embedding_model = 'qwen3-embedding:4b'
_embedding_model = 'qwen3-embedding:0.6b'
# _embedding_model = 'embeddinggemma-2:740m'
# _embedding_model = 'embeddinggemma-2:270m'


def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = LlmEmbedder(OllamaProvider(_embedding_model), cache=None)
    return embedder.embed_texts(texts, truncate=False, test111=1)


if __name__ == '__main__':
    import time

    # 8b: 15.679
    # 4b: 8.677
    # 0.6b: 1.485
    # 740m: 0.840

    texts = ['The fanfare is for good reason: Houdini is probably the most celebrated illusionist of all time. His name haunts dictionaries (the noun “houdini” is “a person or animal that is very good at escaping”) and pop songs (“catch me or I go Houdini,” trills Dua Lipa in one song). Houdini is famous in part because he was the “master of mystery”. But also because he was, as John Cox, a Houdini expert, puts it, “a master at understanding how to promote himself”. Just as you can study Houdini’s performances to understand magic, you can study his career to understand fame.',
 'Houdini offers three lessons for anyone looking to sell something. First, work hard to polish your product. The magician trained like an athlete to ensure he could get out of tight spaces and straitjackets and learned how to hold his breath for minutes on end for underwater escapes. Houdini was also one of the first people “to take the scholarship of magic seriously”, notes Eric Colleary, curator of “Houdini’s Library”. He collected biographies of magicians and histories of sorcery; his research helped him refine his craft and invent new tricks, such as being buried alive or making an elephant disappear.',
 'Second, learn the art of self-promotion. The “golden age” of magic in the 19th century was bolstered by mass media. Rather than buying an advert near the back of a newspaper, Houdini would pull off a stunt to get on the front page. “I’m not an advertiser, I’m news,” he once quipped. In every city he visited he dared police to lock him up so he could escape, and freed himself from straitjackets while hanging upside down from cranes. He was among the first magicians to use radio and movies to help promote his shows.',
 'Houdini also understood corporate partnerships. “How Houdini Made Magic”, a new podcast, looks at his “brand deal” with Joshua Tetley & Son, a brewer, in 1911. Rather than escaping from a sealed milk can full of water, he was challenged to get out of one filled with beer. But the stunt went awry: Houdini, who didn’t drink beer, apparently passed out from the stench in the container and had to be rescued. But that made the episode only more headline-worthy.',
 'Lastly, Houdini understood the importance of protecting his brand. Like the organisers of his centennial celebration in Budapest, Houdini tried to ™ lots of his tricks. It did not always work, in part because a patent spells out the secrets. So instead he launched attacks on his imitators, who called themselves things like Boudini, Hardini, Houdeen and Oudini. He challenged copycats to beat him on stage and threatened to expose the secrets of their tricks to the public. He also copyrighted illusions as “playlets”, that he'] * 10
    start = time.time()
    embeddings = embed_texts(texts)
    for emb in embeddings:
        print(len(emb))
    print(f'time elapsed: {time.time() - start:.3f}')
