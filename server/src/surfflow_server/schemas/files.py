# coding=utf-8
from pathlib import Path

from pydantic import BaseModel, Field

from archaeo import logger
from archaeo.io.files import (get_file_size, get_file_hash, get_file_blocks,
                              get_file_created_time, get_file_modified_time,
                              get_file_accessed_time, get_absolute_path)
from archaeo.iterable import find_by


class FileTypes:
    book = 'book'
    image = 'image'
    audio = 'audio'
    video = 'video'
    office = 'office'
    text = 'text'
    code = 'code'
    data = 'data'
    zip = 'zip'
    link = 'link'
    # other = 'other'
    unknown = 'unknown'


class CollectionTypes:
    book = 'book'
    movie = 'movie'
    dataset = 'dataset'
    image = 'image'
    icloud = 'icloud'
    unknown = 'unknown'


class StorageTypes:
    local = 'local'
    portable = 'portable'
    icloud = 'icloud'
    unknown = 'unknown'


class SizeLabels:
    large = 'large'
    average = 'average'
    small = 'small'
    none = ''

    @classmethod
    def parse(cls, file_type: str, raw_size: int | None):
        if raw_size is None:
            return cls.none
        if file_type == FileTypes.book and raw_size >= 100 * 1000 * 1000:
            return cls.large
        if raw_size >= 1000 * 1000 * 1000:
            return cls.large
        elif raw_size >= 500 * 1000 * 1000:
            return cls.average
        return cls.none


def get_file_type_mappings():
    mapping = {
        FileTypes.book: ('pdf', 'epub', 'mobi', 'azw3', 'djvu', 'chm'),
        FileTypes.image: ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'),
        FileTypes.audio: ('mp3', 'wav', 'aiff'),
        FileTypes.video: ('mp4', 'mkv', 'avi', 'rm', 'rmvb', 'wmv', 'm4p', 'm4v', 'mpg', 'mpeg', 'flv'),
        FileTypes.office: ('doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'rtf'),
        FileTypes.text: ('txt', 'md', 'vtt'),
        FileTypes.code: ('py', 'java', 'cs', 'm', 'sql'),
        FileTypes.data: ('csv', 'json',),
        FileTypes.zip: ('zip', 'gz', 'bz2', '7z', 'rar', 'tar'),
        FileTypes.link: ('icloud', 'lnk'),
    }
    return {ft_ext: ft for ft, ft_exts in mapping.items() for ft_ext in ft_exts}


file_type_mappings = get_file_type_mappings()


def parse_file_type(ext: str) -> str:
    if not ext:
        return FileTypes.unknown
    raw_type = ext.lower().strip()
    raw_type = raw_type.lstrip('.')
    return file_type_mappings.get(raw_type, FileTypes.unknown)


def parse_collection(base_dir: str):
    mapping = {
        CollectionTypes.book: ('book', 'ebook'),
        CollectionTypes.movie: ('movie',),
        CollectionTypes.dataset: ('dataset', 'corpus'),
        CollectionTypes.image: ('image',),
        CollectionTypes.icloud: ('com~apple',),
    }
    col_type_mappings = {ct_kw: ct for ct, ct_kws in mapping.items() for ct_kw in ct_kws}
    col_type_keywords = list(col_type_mappings.keys())

    parts = list(reversed(Path(base_dir).parts))
    for part in parts:
        kw_i = find_by(col_type_keywords, lambda kw: part.startswith(kw))
        if kw_i >= 0:
            kw = col_type_keywords[kw_i]
            return col_type_mappings[kw]
    return CollectionTypes.unknown


def parse_storage_type(raw_path: str):
    file_path = raw_path.lower()
    if '/com~apple' in file_path:
        return StorageTypes.icloud
    elif file_path.startswith('/volumes/'):
        return StorageTypes.portable
    else:
        return StorageTypes.local


class FileInfo(BaseModel):
    base_dir: str
    raw_path: str
    relative_path: str
    # file name with ext
    name: str
    # file name without ext
    stem: str
    # file ext
    extension: str
    size: int
    path_parts: list[str] = Field(default_factory=list)

    creation_time: int | None = None
    modification_time: int | None = None
    last_access_time: int | None = None

    edition: int | None = None
    year: int | None = None

    hash: str | None = None
    hash_algorithm: str | None = None
    tags: list[str] = Field(default_factory=list)

    # collection of base dir, e.g. book, paper, movie, dataset, image
    collection: str = CollectionTypes.unknown
    # enum value based on `extension`
    file_type: str = FileTypes.unknown

    @classmethod
    def load_file(cls,
                  base_dir: str | Path,
                  raw_path: str | Path,
                  tags: list[str] | None = None,
                  max_size_for_hash=1000 * 1000 * 1000):

        def _need_to_calc_hash(file_path: str | Path, collection_type: str, file_size, block_size=512):
            if collection_type != CollectionTypes.icloud:
                return True
            file_store_blocks = get_file_blocks(file_path)
            # in iCloud, a placeholder file's blocks is usually 0, on macOS, the block_size is 512.
            # here adding these rules to avoid downloading too many files from the iCloud server.
            need_to_calc = file_store_blocks > 200 and (file_store_blocks * block_size > file_size * 0.6)
            if not need_to_calc:
                logger.debug(f'file blocks: {file_store_blocks}')
            return need_to_calc

        if not raw_path:
            raise ValueError(f'`raw_path` is required.')
        if not base_dir:
            raise ValueError(f'`base_dir` is required.')

        base_dir = get_absolute_path(base_dir)
        raw_path = get_absolute_path(raw_path)
        relative_path = str(raw_path.relative_to(base_dir))

        name = raw_path.name
        stem = raw_path.stem
        extension = raw_path.suffix.lower().lstrip(".")
        size = get_file_size(raw_path)
        path_parts = list(Path(relative_path).parts[:-1])

        edition = None
        year = None

        collection = parse_collection(base_dir)

        file_hash = None
        hash_algorithm = 'md5'
        if (size is not None and size < max_size_for_hash
                and _need_to_calc_hash(raw_path, collection, size)):
            try:
                file_hash = get_file_hash(raw_path, algorithm=hash_algorithm)
            except OSError as e:
                logger.error(f'get hash error: {e}, file: {raw_path}')
        if not file_hash:
            hash_algorithm = None

        if not tags:
            tags = []

        file_type = parse_file_type(extension)

        return cls(base_dir=str(base_dir),
                   raw_path=str(raw_path),
                   relative_path=relative_path,

                   name=name,
                   stem=stem,
                   extension=extension,
                   size=size,
                   path_parts=path_parts,

                   creation_time=get_file_created_time(raw_path),
                   modification_time=get_file_modified_time(raw_path),
                   last_access_time=get_file_accessed_time(raw_path),

                   edition=edition,
                   year=year,

                   hash=file_hash,
                   hash_algorithm=hash_algorithm,
                   tags=tags,

                   collection=collection,
                   file_type=file_type)


if __name__ == '__main__':
    # base_dir = '~/Library/Mobile Documents/com~apple~Preview/Documents'
    # file = '~/Library/Mobile Documents/com~apple~Preview/Documents/psy/.选择的悖论-用心理学解读人的经济行为.pdf.icloud'

    # print(parse_file_type('.pdf'))
    # print(parse_file_type('md'))
    # print(parse_file_type('data'))

    # base_dir = '~/Library/Mobile Documents/com~apple~Preview/Documents'
    # file = '~/Library/Mobile Documents/com~apple~Preview/Documents/phil/人文科学的逻辑.pdf'
    base_dir = '~/Downloads/books'
    file = '~/Downloads/books/艾丽丝•门罗/你以为你是谁 (艾丽丝•门罗, 2023).epub'

    fi = FileInfo.load_file(base_dir, file, tags=['psy'])
    print(fi)
