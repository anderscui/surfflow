# coding=utf-8
from pathlib import Path

import requests


def download_file(session, url, dest):
    dest = Path(dest)
    temp = dest.with_name(dest.name + '.part')

    try:
        with session.get(url, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()

            with temp.open('wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        temp.replace(dest)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def download_github_releases(
    repo: str,
    output_dir: str | Path,
    release_contains: str = '',
    asset_contains: str = '',
    asset_suffix: str = '.epub',
    start_page: int = 1,
    per_page: int = 30,
    max_pages: int | None = None,
    max_releases: int | None = None,
    stop_tag: str | None = None,
    dry_run: bool = True,
):
    """
    按页获取 GitHub Releases，并筛选、下载附件。

    max_releases: 最多扫描多少条 Release（包括不匹配的）
    stop_tag: 遇到指定 tag_name 时停止，不处理该 Release
    dry_run: True 时只显示匹配结果，不下载
    """
    if not 1 <= per_page <= 100:
        raise ValueError('per_page must be between 1 and 100')

    output_dir = Path(output_dir)
    api_url = f'https://api.github.com/repos/{repo}/releases'

    session = requests.Session()
    session.headers.update({
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'surfflow-release-downloader',
    })

    scanned = 0
    matched = 0
    downloaded = 0
    page = start_page

    while True:
        if max_pages is not None and page >= start_page + max_pages:
            break

        response = session.get(
            api_url,
            params={'page': page, 'per_page': per_page},
            timeout=30,
        )
        response.raise_for_status()
        releases = response.json()

        if not releases:
            break

        print(f'\nPage {page}: {len(releases)} releases')

        for release in releases:
            if max_releases is not None and scanned >= max_releases:
                break

            scanned += 1

            name = release.get('name') or ''
            tag = release['tag_name']

            # 终止条件：不处理边界 Release
            if stop_tag is not None and tag == stop_tag:
                print(f'Stop at: {tag}')
                return {
                    'scanned': scanned,
                    'matched': matched,
                    'downloaded': downloaded,
                }

            if release_contains not in name:
                continue

            matched += 1
            print(f'\nRelease: {name} ({tag})')

            for asset in release.get('assets', []):
                filename = asset['name']

                if asset_contains not in filename:
                    continue

                if asset_suffix and not filename.lower().endswith(
                    asset_suffix.lower()
                ):
                    continue

                dest = output_dir / filename

                if dest.exists():
                    print(f'  Skip: {filename}')
                    continue

                print(f'  {"Match" if dry_run else "Download"}: {filename}')

                if not dry_run:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    download_file(
                        session,
                        asset['browser_download_url'],
                        dest,
                    )
                    downloaded += 1

        if max_releases is not None and scanned >= max_releases:
            break

        if len(releases) < per_page:
            break

        page += 1

    return {
        'scanned': scanned,
        'matched': matched,
        'downloaded': downloaded,
    }
