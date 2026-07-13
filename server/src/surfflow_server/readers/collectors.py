# coding=utf-8
from pathlib import Path

import time
from collections import Counter

from archaeo.io.docs import LocalFileMetadata
from archaeo.io.file_metadata import get_local_file_metadata
from archaeo.io.files import json_dump, list_files, file_exists, get_file_size, get_file_modified_time, json_load, \
    get_absolute_path
from archaeo.llm_providers import OllamaProvider
from surfflow_server.config import SOURCE_DIRS
from surfflow_server.embedders.text_embedders import LlmEmbedder
from surfflow_server.schemas.files import FileInfo, CollectionTypes
from surfflow_server.config import logger


def get_valid_prev_files(prev_file):
    prev_files = json_load(prev_file)
    logger.debug(f'prev files: {len(prev_files)}')

    valid_files = {}
    for item in prev_files:
        raw_path = item['raw_path']
        if (not file_exists(raw_path)
                or get_file_size(raw_path) != item['size']
                or get_file_modified_time(raw_path) != item['modification_time']
                or not item['hash']):
            logger.debug(f'invalid prev file: {raw_path}')
            continue
        valid_files[raw_path] = item
    logger.debug(f'valid prev files: {len(valid_files)}')
    return valid_files


def get_prev_metadata(prev_file):
    prev_metadata = json_load(prev_file)
    logger.debug(f'prev metadata: {len(prev_metadata)}')

    return prev_metadata


# def determine_dup_files(hash_files: defaultdict[list]):
#     def by_parts(file_items):
#         items = sorted(file_items, key=lambda f: len(PurePath(f['relative_path']).parts), reverse=True)
#         if len(PurePath(items[0]['relative_path']).parts) > len(PurePath(items[1]['relative_path']).parts):
#             return items[0], items[1:]
#         return None, []
#
#     def by_length(file_items):
#         items = sorted(file_items, key=lambda f: len(f['relative_path']), reverse=True)
#         if len(items[0]['relative_path']) > len(items[1]['relative_path']):
#             return items[0], items[1:]
#         return None, []
#
#     possible_dups = {}
#     for fh, files in hash_files.items():
#         if 1 < len(files) <= 100:
#             main_file, dups = by_parts(files)
#             if not dups:
#                 main_file, dups = by_length(files)
#             if main_file is not None and dups:
#                 dup_raw_paths = [f['raw_path'] for f in dups]
#                 print(dup_raw_paths)
#                 print()
#                 possible_dups[main_file['raw_path']] = dup_raw_paths
#     return possible_dups


def embed_files(local_file,
                metadata_file,
                embedding_file,
                embedder: LlmEmbedder):
    def build_embedding_text(file_info: FileInfo, metadata: LocalFileMetadata | None) -> str:
        return file_info.stem

    files = json_load(local_file)[:10]
    file_metadata = json_load(metadata_file)
    file_embeddings = {}
    start = time.time()
    for file in files:
        fi = FileInfo.model_validate(file)
        meta = file_metadata.get(fi.raw_path)
        embedding_text = build_embedding_text(fi, meta)
        embedding = embedder.embed_text(embedding_text)
        file_embeddings[fi.raw_path] = embedding

        if len(file_embeddings) % 5 == 0:
            logger.debug(f'embedded {len(file_embeddings)}, time: {time.time() - start}')

    logger.debug(f'embedded {len(file_embeddings)}, time: {time.time() - start}')
    json_dump(file_embeddings, embedding_file)


def get_metadata(local_file: str | Path, metadata_file: str | Path, prev_metadata=None):
    if prev_metadata is None:
        prev_metadata = {}

    local_file = get_absolute_path(local_file)
    local_files = json_load(local_file)
    logger.debug(f'total files: {len(local_files)}')

    all_metadata = {}
    start = time.time()
    for file in local_files:
        raw_path = file['raw_path']

        if file['collection'] == CollectionTypes.icloud and not file['hash']:
            logger.debug(f'skip metadata: {raw_path}')
            continue

        prev = prev_metadata.get(raw_path)
        if prev:
            all_metadata[raw_path] = prev
        else:
            try:
                metadata = get_local_file_metadata(raw_path)
            except Exception as e:
                logger.error(f'get metadata error: {e}')
                metadata = LocalFileMetadata()

            try:
                metadata_dump = metadata.model_dump(mode='json')
            except Exception as e:
                logger.error(f'dump metadata error: {raw_path}')
                metadata_dump = {}
            all_metadata[raw_path] = metadata_dump

        if len(all_metadata) % 1000 == 0:
            logger.debug(f'collected metadata: {len(all_metadata)}, time: {time.time() - start}')
            json_dump(all_metadata, metadata_file)

    logger.debug(f'collected metadata: {len(all_metadata)}, time: {time.time() - start}')
    json_dump(all_metadata, metadata_file)


def can_reuse_file_info(file: str | Path, prev: dict) -> bool:
    size = get_file_size(file)
    mod_time = get_file_modified_time(file)

    return (
            prev.get('size') == size
            and prev.get('modification_time') == mod_time
    )


def collect_files(output_file, prev_files=None):
    if prev_files is None:
        prev_files = {}

    c_exts = Counter()
    c_cols = Counter()
    c_fts = Counter()
    c_hashes = Counter()

    collected = []
    start = time.time()
    for base_dir in SOURCE_DIRS[:100]:
        for file in list_files(base_dir,
                               pattern='*.*',
                               excludes=lambda f: '.DS_Store' in str(f)):

            file_path_str = str(file)
            if any(kw in file_path_str for kw in ('.epub/', '.git/')):
                continue

            # if 'com~apple~Preview/' in file_path_str:
            #     continue
            if 'com~apple~Preview/Documents/mine/' in file_path_str:
                continue

            prev = prev_files.get(file_path_str)
            if prev:
                file_info = FileInfo.model_validate(prev)
            else:
                file_info = FileInfo.load_file(base_dir, file)

            c_exts[file_info.extension] += 1
            c_cols[file_info.collection] += 1
            c_fts[file_info.file_type] += 1
            c_hashes[file_info.hash] += 1
            # print('new file:', file_info)
            collected.append(file_info.model_dump())
            if len(collected) % 1000 == 0:
                logger.debug(f'collected {len(collected)} files, time: {time.time() - start}')

        json_dump(collected, output_file)
        print(f'finish {base_dir}, file count: {len(collected)}')

    print('extensions:', c_exts.total(), c_exts.most_common())
    print('collection:', c_cols.total(), c_cols.most_common())
    print('file type:', c_fts.total(), c_fts.most_common())
    print('file hash:', c_hashes.total(), c_hashes.most_common(100))

    json_dump(collected, output_file)
    logger.debug(f'finish all dirs, file count: {len(collected)}, time: {time.time() - start}')


if __name__ == '__main__':
    # prev_files = get_valid_prev_files('~/Downloads/local_files_260712_1.json')
    # collect_files('~/Downloads/local_files_260713_1.json', prev_files=prev_files)

    local_file = '~/Downloads/local_files_260713_1.json'
    metadata_file = '~/Downloads/local_metadata_260713_3.json'
    # prev_meta = get_prev_metadata(metadata_file)
    # get_metadata(local_file, '~/Downloads/local_metadata_260713_5.json', prev_metadata=prev_meta)

    output_embed_file = '~/Downloads/local_embeddings_260714_1.json'
    embedder = LlmEmbedder(OllamaProvider('qwen3-embedding:8b'))
    embed_files(local_file, metadata_file, output_embed_file, embedder=embedder)

