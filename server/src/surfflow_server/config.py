# coding=utf-8
import os
from pathlib import Path

from loguru import logger

from archaeo.io.files import expand_user_path

ROOT_DIR = Path(__file__).parent
logger.debug(f'root dir: {ROOT_DIR}')

DATA_DIR = ROOT_DIR / 'data'
# STATIC_DIR = ROOT_DIR / 'static'
# TEMPLATES_DIR = ROOT_DIR / 'templates'
logger.debug(f'data dir: {DATA_DIR}')

WORKING_DIR = expand_user_path(os.getenv('WORKING_DIR', '~/Downloads'))
ARCHIVE_DIR = expand_user_path(os.getenv('ARCHIVE_DIR', '~/Downloads/doc_backup'))
logger.debug(f'working dir: {WORKING_DIR}')
logger.debug(f'archive dir: {ARCHIVE_DIR}')

SOURCE_DIRS = [
    '~/Downloads/to_read',
    '~/Downloads/books/',
    '~/Downloads/movie',
    '~/data/corpus',
    '/Volumes/T2/books',
    '/Volumes/T2/movie',
    '/Volumes/T2/media',
    '/Volumes/T2/corpus',
    # '~/Library/Mobile Documents/com~apple~Preview/Documents/soc',
    '~/Library/Mobile Documents/com~apple~Preview/Documents',
]
SOURCE_DIRS = [expand_user_path(d.rstrip('/')) for d in SOURCE_DIRS]
logger.debug(f'source dirs: {SOURCE_DIRS}, count: {len(SOURCE_DIRS)}')

ES_SERVER = os.getenv('ES_SERVER', 'http://localhost:9200')
ES_INDEX_LOCAL_FILE = 'local_files'
ES_VERSION = '20260715_1'
ES_MAPPINGS_FILE = os.path.join(DATA_DIR, f'mappings/local_files.json')

# REDIS_EMBEDDING_DB = os.getenv('REDIS_EMBEDDING_DB')
SURFFLOW_DB = os.getenv('SURFFLOW_DB', '~/works/dbs/surfflow/surfflow.db')
SURFFLOW_EMB_DB = os.getenv('SURFFLOW_EMB_DB', '~/works/dbs/surfflow/surfflow_emb.db')
