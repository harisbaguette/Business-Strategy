#!/usr/bin/env python3
"""로컬 문서·자료 구조를 읽기 전용으로 확인한다. 사실성·수익성 판정은 하지 않는다."""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {'.git', 'graft', '__pycache__', 'node_modules', '.venv'}
STATUSES = {'실행 전 확인', '운영 중', '중단·보류'}
LINK = re.compile(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\s)]+))\)')
PRIVATE_COLUMN = re.compile(r'작가|작성자|판매자(?:명|이름)?|채널|연락처|이메일|전화|실명|author|email|phone|seller_name|channel_name', re.I)


def documents(root: Path):
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(folder) / name
            if not path.is_symlink():
                yield path


def without_code(text: str) -> str:
    return re.sub(r'(?ms)^```.*?^```[^\n]*', '', text)


def local_links(path: Path, text: str):
    for match in LINK.finditer(without_code(text)):
        target = match.group(1) or match.group(2)
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        yield (path.parent / unquote(parsed.path)).resolve()


def check(root: Path) -> tuple[list[str], list[str], int]:
    errors, notices = [], []
    required = ['README.md', 'AGENTS.md', 'CLAUDE.md', '1-프로젝트지침.txt',
                '2-공략규약.md', '전략서/README.md', '관리/파일관리.md', '관리/점검기록.md']
    for name in required:
        if not (root / name).is_file():
            errors.append(f'필수 파일 없음: {name}')
    rule = root / '2-공략규약.md'
    expected = []
    if rule.is_file():
        section = rule.read_text(encoding='utf-8').split('## 공략 전략서 양식', 1)
        if len(section) == 2:
            template = section[1].split('\n---', 1)[0]
            expected = [(int(n), title) for n, title in re.findall(r'^(\d+)\. \*\*(.*?)\.\*\*', template, re.M)]
        if not expected or [n for n, _ in expected] != list(range(len(expected))):
            errors.append('공략 규약에서 연속된 전략서 양식을 읽을 수 없음')

    paths = list(documents(root))
    texts = {}
    hashes = {}
    for path in paths:
        if path.suffix not in {'.md', '.txt', '.csv', '.py'}:
            continue
        data = path.read_bytes()
        if data:
            hashes.setdefault(hashlib.sha256(data).hexdigest(), []).append(path.relative_to(root).as_posix())
        if path.suffix in {'.md', '.txt'}:
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError:
                errors.append(f'UTF-8 아님: {path.relative_to(root)}')
                continue
            texts[path] = text
            if path.suffix == '.md':
                for target in local_links(path, text):
                    if not target.exists():
                        errors.append(f'끊긴 로컬 링크: {path.relative_to(root)} → {target.name}')
                    elif not target.is_relative_to(root):
                        errors.append(f'저장소 밖 로컬 링크: {path.relative_to(root)}')
    for same in hashes.values():
        if len(same) > 1:
            notices.append('내용이 같은 파일: ' + ', '.join(same))

    index_path = root / '전략서/README.md'
    index = texts.get(index_path, '')
    indexed = set(local_links(index_path, index))
    strategies = sorted((root / '전략서').glob('*/전략서.md'))
    if not strategies:
        notices.append('아직 작성된 시장 전략서가 없음')
    for path in strategies:
        label = path.relative_to(root).as_posix()
        text = texts.get(path, '')
        if path.resolve() not in indexed:
            errors.append(f'시장 목록 누락: {label}')
        actual = [(int(n), title) for n, title in re.findall(r'^## (\d+)\. (.+)$', text, re.M)]
        if expected and actual != expected:
            errors.append(f'전략서 칸·순서 불일치: {label}')
        parts = re.split(r'^## \d+\. .+$', text, flags=re.M)
        for i, body in enumerate(parts[1:]):
            if not body.strip():
                errors.append(f'빈 전략서 칸 {i}: {label}')
        card = re.search(r'(?ms)^## 0\. .+?\n(.*?)^## 1\.', text)
        if not card or not 1 <= len([line for line in card[1].splitlines() if line.strip()]) <= 15:
            errors.append(f'공략 카드 없음 또는 15줄 초과: {label}')
        values = {}
        for key in ['작성일', '수정일', '상태']:
            match = re.search(rf'^- {key}: (.+)$', text, re.M)
            if not match:
                errors.append(f'{key} 누락: {label}')
            else:
                values[key] = match[1].strip()
        if values.get('상태') not in STATUSES:
            errors.append(f'상태 값 확인 필요: {label}')
        try:
            created = date.fromisoformat(values['작성일'])
            modified = date.fromisoformat(values['수정일'])
            if created > modified:
                errors.append(f'작성일이 수정일보다 뒤임: {label}')
        except (KeyError, ValueError):
            errors.append(f'날짜 형식 확인 필요: {label}')
        matching_rows = [line for line in index.splitlines()
                         if path.resolve() in set(local_links(index_path, line))]
        if matching_rows and (values.get('수정일', '') not in matching_rows[0]
                              or values.get('상태', '') not in matching_rows[0]):
            errors.append(f'시장 목록의 날짜·상태 불일치: {label}')
        evidence = path.parent / '근거.md'
        if not evidence.is_file() or evidence.resolve() not in set(local_links(path, text)):
            errors.append(f'근거 파일 또는 연결 누락: {label}')
        if values.get('상태') == '실행 전 확인':
            notices.append(f'{path.parent.name}: 실행·수익 검증 전 (문서 상태 표시)')

    for child in (root / '전략서').iterdir() if (root / '전략서').is_dir() else []:
        if child.is_dir() and not (child / '전략서.md').is_file():
            errors.append(f'전략서 없는 시장 폴더: {child.name}')
        if child.is_file() and child.name != 'README.md':
            errors.append(f'시장 폴더 밖 결과·자료: {child.name}')
    for path in paths:
        if path.suffix != '.csv':
            continue
        label = path.relative_to(root).as_posix()
        if not re.fullmatch(r'(원자료|실적)-\d{4}-\d{2}-\d{2}(?:-.+)?\.csv', path.name):
            errors.append(f'CSV 이름에 종류·수집일 필요: {label}')
        evidence = path.parent / '근거.md'
        if path.resolve() not in set(local_links(evidence, texts.get(evidence, ''))):
            errors.append(f'CSV의 근거 설명·링크 누락: {label}')
        try:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.reader(stream))
            if len(rows) < 2 or not rows[0] or len(set(rows[0])) != len(rows[0]):
                errors.append(f'CSV 헤더·자료 확인 필요: {label}')
                continue
            if any(PRIVATE_COLUMN.search(name) for name in rows[0]):
                errors.append(f'개인 식별 정보 열 발견: {label}')
            if any(len(row) != len(rows[0]) for row in rows[1:]):
                errors.append(f'CSV 열 수 불일치: {label}')
        except (UnicodeDecodeError, csv.Error) as exc:
            errors.append(f'CSV 읽기 실패: {label} ({type(exc).__name__})')
    return errors, notices, len(strategies)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1],
                        help='점검할 저장소 (격리된 사본 확인에 사용)')
    args = parser.parse_args()
    errors, notices, count = check(args.root.resolve())
    for message in errors:
        print('오류:', message)
    for message in notices:
        print('참고:', message)
    print(f'구조 점검: 시장 {count}개, 오류 {len(errors)}개, 참고 {len(notices)}개')
    print('이 결과는 파일 구조 검사이며 시장 사실·수익성 검증이 아닙니다.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
