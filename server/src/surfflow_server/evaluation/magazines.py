# coding=utf-8
from collections import defaultdict
from pathlib import Path

from archaeo.io.epub import get_epub_metadata
from archaeo.io.files import list_files, get_file_size, json_dump
from archaeo.iterable import seq_similarity


def compare_epub_file(path1: Path, path2: Path, max_outline_level=3):
    metadata1 = get_epub_metadata(path1, max_outline_level=max_outline_level)
    metadata2 = get_epub_metadata(path2, max_outline_level=max_outline_level)

    # 可能会有文章顺序的不同
    outline1 = sorted([item.title for item in metadata1.outline.items])
    outline2 = sorted([item.title for item in metadata2.outline.items])
    outline1 = '\n'.join(outline1)
    outline2 = '\n'.join(outline2)
    print('outline len:', len(outline1), len(outline2))
    sim = seq_similarity(outline1, outline2)

    return sim, outline1, outline2


if __name__ == '__main__':
    source_dir = '/Users/andersc/data/dev/surfflow/magazines/epub'
    files = list(list_files(source_dir, excludes=lambda p: '.DS_Store' in str(p)))
    by_sub_dirs = defaultdict(list)
    for p in files:
        by_sub_dirs[p.parent.parent].append(p.parent.name + '/' + p.name)
    assert len(by_sub_dirs) == 100

    file_sims = []
    sub_dirs = sorted(by_sub_dirs)
    for sd in sub_dirs:
        # print(sd)
        file1, file2 = sorted(by_sub_dirs[sd])
        print(sd, file1, file2)
        file_sim = compare_epub_file(sd / file1, sd / file2, max_outline_level=3)
        file_sims.append([(str(sd), file1, file2), file_sim])
    json_dump(file_sims, '~/data/dev/surfflow/magazines/compare_results.json')



    # sd = sub_dirs[-100]
    # file1, file2 = sorted(by_sub_dirs[sd])
    # print(sd, file1, file2)
    # file_sim = compare_epub_file(sd / file1, sd / file2, max_outline_level=3)
    # print(file_sim[0])
