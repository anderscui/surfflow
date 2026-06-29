# coding=utf-8
import re


BOOK_TITLE_PATTERN = re.compile(r"《([^《》]{1,80})》")


def extract_book_titles(text: str) -> list[str]:
    titles = BOOK_TITLE_PATTERN.findall(text)
    return list(dict.fromkeys(title.strip() for title in titles if title.strip()))


if __name__ == '__main__':
    s = """《天真的人类学家》
这本书可总结命硬的人类学家在非洲上演我命由我不由天的励志故事（内含人类学学术版）

在这本书里你可以看到什么叫一个人偶尔大霉的同时还能小霉不断。非常欢乐，但建立在作者的敬业精神和吃不完的苦之上。

《美德的动摇》
感人呀，每本书都要研究美学的三岛在这本简单的娱乐小说里克制了自己！

仅仅是简单的女性出轨故事，却能体味到作者独特的妩媚又有一点冷酷的文笔，适合对三岛有兴趣却畏惧他时不时大发的佛学美学议论欲的读者。（说的就是你《晓寺》）"""

    books = extract_book_titles(s)
    print(books)
