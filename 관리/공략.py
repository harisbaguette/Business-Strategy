#!/usr/bin/env python3
"""공략 프로젝트 현황을 전략서 머리말에서 읽어 보여 준다. 읽기만 한다.

list: 전체 현황(상태·수정일·다음 할 일·연결 폴더)
find: 작업 폴더나 이름으로 해당 공략 프로젝트를 찾는다
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['작성일', '수정일', '상태', '다음 할 일', '연결 폴더']
ORDER = {'운영 중': 0, '실행 전 확인': 1, '중단·보류': 2}


def projects(root: Path = ROOT) -> list[dict]:
    rows = []
    for path in sorted((root / '전략서').glob('*/전략서.md')):
        head = path.read_text(encoding='utf-8-sig').split('\n## ', 1)[0]
        row = {'이름': path.parent.name, '폴더': str(path.parent)}
        for key in FIELDS:
            match = re.search(rf'^- {key}: (.+)$', head, re.M)
            row[key] = match[1].strip() if match else ''
        rows.append(row)
    rows.sort(key=lambda r: r['수정일'], reverse=True)
    return sorted(rows, key=lambda r: ORDER.get(r['상태'], 3))


def linked(row: dict) -> Path | None:
    value = row.get('연결 폴더', '')
    if not value or value == '없음':
        return None
    return Path(value).expanduser().resolve()


def find(rows: list[dict], folder: str | None, name: str | None) -> list[dict]:
    if folder:
        target = Path(folder).expanduser().resolve()
        hits = [(len(str(p)), r) for r in rows
                if (p := linked(r)) and (target == p or p in target.parents)]
        return [r for _, r in sorted(hits, key=lambda h: h[0], reverse=True)][:1]
    key = (name or '').replace(' ', '').lower()
    exact = [r for r in rows if r['이름'].replace(' ', '').lower() == key]
    return exact or [r for r in rows if key and key in r['이름'].replace(' ', '').lower()]


def show(rows: list[dict]) -> None:
    if not rows:
        print('공략 프로젝트 없음')
        return
    for r in rows:
        print(f"- {r['이름']} | {r['상태'] or '상태 없음'} | 수정 {r['수정일'] or '?'}")
        print(f"  다음 할 일: {r['다음 할 일'] or '(비어 있음)'}")
        if r['연결 폴더']:
            print(f"  연결 폴더: {r['연결 폴더']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true', help='JSON으로 출력')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='전체 현황')
    finder = sub.add_parser('find', help='작업 폴더나 이름으로 찾기')
    finder.add_argument('--folder', help='작업 중인 폴더(연결 폴더나 그 하위)')
    finder.add_argument('--name', help='공략 프로젝트 이름 일부')
    args = parser.parse_args()

    rows = projects()
    if args.command == 'find':
        if not (args.folder or args.name):
            parser.error('find에는 --folder나 --name이 필요함')
        rows = find(rows, args.folder, args.name)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        show(rows)
    return 0 if rows or args.command == 'list' else 1


if __name__ == '__main__':
    sys.exit(main())
