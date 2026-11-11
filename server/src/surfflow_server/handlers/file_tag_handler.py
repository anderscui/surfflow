# coding=utf-8
from typing import Sequence

from archaeo.io.files import json_load
from archaeo.llm_providers import OllamaProvider

from surfflow_server.config import logger, SURFFLOW_DB, LOCAL_FILE_TAG_VERSION, LOCAL_FILE_TAG_FILE
from surfflow_server.data_access.database import connect_db
from surfflow_server.data_access.local_file_tag import get_file_tags, update_file_tags
from surfflow_server.schemas.file_tag import FileTagInput, FileTagRecord
from surfflow_server.taggers.llm_tagger import LlmFileTagger

llm = OllamaProvider('gemma4:26b')
# tags = ['语言学习', '艺术', '绘画', '中国绘画', '书法', '摄影', '建筑', '电影', '音乐']
TAGS = [item['tag'] for item in json_load(LOCAL_FILE_TAG_FILE)]
tagger = LlmFileTagger(provider=llm, tags=TAGS)


def get_local_file_tags(filenames: list[str]):
    with connect_db(SURFFLOW_DB) as db_conn:
        file_tags = get_file_tags(db_conn, filenames, tagger=tagger.name, tags_version=LOCAL_FILE_TAG_VERSION)
        logger.debug(file_tags)


def tag_files(files: Sequence[FileTagInput],
              force: bool = False) -> dict[str, list[str]]:
    by_path: dict[str, FileTagInput] = {}
    for file in files:
        if not file.raw_path.strip() or not file.filename.strip():
            raise ValueError(f'Invalid file input: {file!r}')
        if file.raw_path in by_path and by_path[file.raw_path].filename != file.filename:
            raise ValueError(f'Conflicting filenames for path {file.raw_path!r}')
        by_path[file.raw_path] = file

    unique_files = list(by_path.values())
    if not unique_files:
        return {}

    with connect_db(SURFFLOW_DB) as db_conn:
        cached = {} if force else get_file_tags(db_conn,
                                                list(by_path),
                                                tagger=tagger.name,
                                                tags_version=LOCAL_FILE_TAG_VERSION)
        results = {
            file.raw_path: cached[file.raw_path].tags
            for file in unique_files
            if file.raw_path in cached and cached[file.raw_path].filename == file.filename
        }

        pending = [file for file in unique_files if file.raw_path not in results]
        for file in pending:
            tags = tagger.tag(file.filename)
            record = FileTagRecord(
                raw_path=file.raw_path,
                tagger=tagger.name,
                tags_version=LOCAL_FILE_TAG_VERSION,
                filename=file.filename,
                tags=tags,
            )
            update_file_tags(db_conn, [record])
            results[file.raw_path] = tags

    return results


if __name__ == '__main__':
    filenames = ['/Users/andersc/Downloads/金瓶梅：崇祯本 (兰陵笑笑生, 1989).epub',
                 '/Users/andersc/Downloads/摄影构图学_重排版 (Ben Clements, David Rosenfeld, 2011).pdf']
    get_local_file_tags(filenames)

    to_tag = [
        FileTagInput(raw_path='/Users/andersc/Downloads/AI Engineering Guidebook (DailyDoseofDS.com, 2025).pdf',
                     filename='AI Engineering Guidebook (DailyDoseofDS.com, 2025).pdf'),
        FileTagInput(raw_path='/Users/andersc/Downloads/Geography of the World (DK, 2007).pdf',
                     filename='Geography of the World (DK, 2007).pdf'),
        FileTagInput(raw_path='/Users/andersc/Downloads/一次讀懂經濟學經典 50 Economics Classics.epub',
                     filename='一次讀懂經濟學經典 50 Economics Classics.epub'),
        FileTagInput(raw_path='/Users/andersc/Downloads/摄影构图学_重排版 (Ben Clements, David Rosenfeld, 2011).pdf',
                     filename='摄影构图学_重排版 (Ben Clements, David Rosenfeld, 2011).pdf'),
        FileTagInput(raw_path='/Users/andersc/Downloads/金瓶梅：崇祯本 (兰陵笑笑生, 1989).epub',
                     filename='金瓶梅：崇祯本 (兰陵笑笑生, 1989).epub')
    ]
    print(tag_files(to_tag, force=False))
