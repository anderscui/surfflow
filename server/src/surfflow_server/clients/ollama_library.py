# coding=utf-8

import json
import logging
from datetime import timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LIBRARY_URL = 'https://ollama.com/library?sort=newest'
OUTPUT_FILE = Path('ollama_models.json')

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html',
    })

    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount('https://', HTTPAdapter(max_retries=retry))

    return session


def _parse_download(downloads: str) -> int:
    downloads = downloads.replace(',', '')
    downloads = downloads.lower()
    if downloads.endswith('k'):
        return int(float(downloads[:-1]) * 10 ** 3)
    elif downloads.endswith('m'):
        return int(float(downloads[:-1]) * 10 ** 6)
    else:
        return int(float(downloads))


def _parse_date(date: str) -> str:
    # UTC ISO 8601 format
    return parse(date).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_model(card) -> dict | None:
    link = card.select_one('a[href^="/library/"]')
    if not link:
        return None

    name_element = link.select_one('h2 span')
    if not name_element:
        return None

    name = name_element.get_text(strip=True)

    description_element = link.select_one('div[title] > p')
    description = (
        description_element.get_text(' ', strip=True)
        if description_element else ''
    )

    capabilities = [
        span.get_text(strip=True)
        for span in link.select('span.bg-indigo-50')
    ]

    sizes = [
        span.get_text(strip=True)
        for span in link.select('span.text-blue-600')
    ]

    metadata = link.select(
        'p.text-neutral-500 > span.flex.items-center'
    )

    downloads_text = None
    downloads = None
    tag_count = None
    # update_date_text = None
    update_date_raw = None
    update_date = None

    if len(metadata) >= 3:
        downloads_element = metadata[0].select_one('span')
        tags_element = metadata[1].select_one('span')
        updated_element = metadata[2]

        if downloads_element:
            downloads_text = downloads_element.get_text(strip=True)
            downloads = _parse_download(downloads_text)

        if tags_element:
            tag_count = int(
                tags_element.get_text(strip=True).replace(',', '')
            )

        updated_spans = updated_element.select('span')
        # if updated_spans:
        #     update_date_text = updated_spans[-1].get_text(strip=True)

        update_date_raw = updated_element.get('title')
        update_date = _parse_date(update_date_raw)

    return {
        'name': name,
        'description': description,
        'capabilities': capabilities,
        'sizes': sizes,
        'downloads_text': downloads_text,
        'downloads': downloads,
        'tag_count': tag_count,
        # 'update_date_text': update_date_text,
        'update_date_raw': update_date_raw,
        'update_date': update_date,
    }


def fetch_models(session: requests.Session) -> list[dict]:
    response = session.get(LIBRARY_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    main = soup.select_one('main') or soup

    cards = main.select('li:has(> a[href^="/library/"])')

    models = []

    for card in cards:
        model = parse_model(card)
        if model:
            models.append(model)

    return models


def main():
    session = create_session()
    models = fetch_models(session)

    OUTPUT_FILE.write_text(
        json.dumps(models, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    logger.info(
        'Saved %d models to %s',
        len(models),
        OUTPUT_FILE.resolve(),
    )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
    )
    main()
