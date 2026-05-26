from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

TARGET_DIRS = {
    'smart_chef': 'he_thong',
    'apps': 'nghiep_vu',
    'app': 'nghiep_vu',
    'services': 'dich_vu_ngoai',
    'app_services': 'dich_vu_ngoai',
    'database': 'du_lieu',
    'markdowns': 'tai_lieu',
    'tests': 'kiem_thu',
    'scripts': 'cong_cu_ho_tro',
}

SCRIPT_PATTERNS = ('check_', 'seed_', 'fix_', 'verify_', 'cleanup_')

IMPORT_REWRITES = [
    (re.compile(r'(?<![\w.])from\s+app\.services(?=[\s.])'), 'from dich_vu_ngoai'),
    (re.compile(r'(?<![\w.])import\s+app\.services(?=[\s.])'), 'import dich_vu_ngoai'),
    (re.compile(r'(?<![\w.])from\s+services(?=[\s.])'), 'from dich_vu_ngoai'),
    (re.compile(r'(?<![\w.])import\s+services(?=[\s.])'), 'import dich_vu_ngoai'),
    (re.compile(r'(?<![\w.])from\s+apps(?=[\s.])'), 'from nghiep_vu'),
    (re.compile(r'(?<![\w.])import\s+apps(?=[\s.])'), 'import nghiep_vu'),
    (re.compile(r'(?<![\w.])from\s+app(?=[\s.])'), 'from nghiep_vu'),
    (re.compile(r'(?<![\w.])import\s+app(?=[\s.])'), 'import nghiep_vu'),
    (re.compile(r'(?<![\w.])from\s+smart_chef(?=[\s.])'), 'from he_thong'),
    (re.compile(r'(?<![\w.])import\s+smart_chef(?=[\s.])'), 'import he_thong'),
    (re.compile(r"(?<![\w.])smart_chef(?=[\.\'\"/])"), 'he_thong'),
    (re.compile(r'(?<![\w.])apps(?=\.)'), 'nghiep_vu'),
    (re.compile(r'(?<![\w.])app(?=\.)'), 'nghiep_vu'),
    (re.compile(r'(?<![\w.])services(?=\.)'), 'dich_vu_ngoai'),
]


def log(actions: list[str], message: str) -> None:
    actions.append(message)
    print(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def file_hash(path: Path) -> bytes:
    return path.read_bytes()


def move_file(source: Path, destination: Path, actions: list[str]) -> None:
    if not source.exists():
        return
    if source.name.endswith('_patch.py'):
        source.unlink()
        log(actions, f'DELETE patch file: {source.relative_to(PROJECT_ROOT)}')
        return
    ensure_parent(destination)
    if destination.exists():
        if destination.is_file() and source.is_file() and file_hash(destination) == file_hash(source):
            log(actions, f'SKIP duplicate: {source.relative_to(PROJECT_ROOT)} -> {destination.relative_to(PROJECT_ROOT)}')
            source.unlink()
            return
        source.unlink()
        log(actions, f'SKIP existing and drop source: {source.relative_to(PROJECT_ROOT)} -> {destination.relative_to(PROJECT_ROOT)}')
        return
    shutil.move(str(source), str(destination))
    log(actions, f'MOVE file: {source.relative_to(PROJECT_ROOT)} -> {destination.relative_to(PROJECT_ROOT)}')


def move_tree(
    source: Path,
    destination: Path,
    actions: list[str],
    *,
    drop_root_init: bool = False,
) -> None:
    if not source.exists():
        return

    destination.mkdir(parents=True, exist_ok=True)

    for entry in sorted(source.iterdir(), key=lambda item: item.name.lower()):
        if drop_root_init and entry.name == '__init__.py' and source == PROJECT_ROOT / 'app':
            entry.unlink()
            log(actions, f'DELETE legacy init: {entry.relative_to(PROJECT_ROOT)}')
            continue

        target = destination / entry.name
        if entry.is_dir():
            move_tree(entry, target, actions)
            if entry.exists() and not any(entry.iterdir()):
                entry.rmdir()
                log(actions, f'REMOVE empty dir: {entry.relative_to(PROJECT_ROOT)}')
            continue

        move_file(entry, target, actions)

    if source.exists() and not any(source.iterdir()):
        source.rmdir()
        log(actions, f'REMOVE empty dir: {source.relative_to(PROJECT_ROOT)}')


def move_services_tree(source: Path, destination: Path, actions: list[str]) -> None:
    if not source.exists():
        return
    move_tree(source, destination, actions)


def move_app_tree(source: Path, destination: Path, services_destination: Path, actions: list[str]) -> None:
    if not source.exists():
        return

    destination.mkdir(parents=True, exist_ok=True)
    services_destination.mkdir(parents=True, exist_ok=True)

    for entry in sorted(source.iterdir(), key=lambda item: item.name.lower()):
        if entry.name == '__init__.py':
            entry.unlink()
            log(actions, f'DELETE legacy init: {entry.relative_to(PROJECT_ROOT)}')
            continue

        if entry.name == 'services' and entry.is_dir():
            move_tree(entry, services_destination, actions)
            if entry.exists() and not any(entry.iterdir()):
                entry.rmdir()
                log(actions, f'REMOVE empty dir: {entry.relative_to(PROJECT_ROOT)}')
            continue

        target = destination / entry.name
        if entry.is_dir():
            move_tree(entry, target, actions)
            if entry.exists() and not any(entry.iterdir()):
                entry.rmdir()
                log(actions, f'REMOVE empty dir: {entry.relative_to(PROJECT_ROOT)}')
            continue

        move_file(entry, target, actions)

    if source.exists() and not any(source.iterdir()):
        source.rmdir()
        log(actions, f'REMOVE empty dir: {source.relative_to(PROJECT_ROOT)}')


def move_markdown_files(destination: Path, actions: list[str]) -> None:
    candidates = [
        path
        for path in PROJECT_ROOT.rglob('*.md')
        if path.name.lower() != 'readme.md' and destination not in path.parents
    ]
    for path in sorted(candidates):
        relative_path = path.relative_to(PROJECT_ROOT)
        target = destination / relative_path
        move_file(path, target, actions)


def move_root_scripts(destination: Path, actions: list[str]) -> None:
    for pattern in SCRIPT_PATTERNS:
        for path in sorted(PROJECT_ROOT.glob(f'{pattern}*.py')):
            if path.parent != PROJECT_ROOT:
                continue
            move_file(path, destination / path.name, actions)


def move_root_tests(destination: Path, actions: list[str]) -> None:
    for path in sorted(PROJECT_ROOT.glob('test_*.py')):
        if path.parent != PROJECT_ROOT:
            continue
        move_file(path, destination / path.name, actions)


def move_database(destination: Path, actions: list[str]) -> None:
    database_dir = PROJECT_ROOT / 'database'
    if database_dir.exists():
        move_tree(database_dir, destination / 'database', actions)
    sqlite_db = PROJECT_ROOT / 'db.sqlite3'
    if sqlite_db.exists():
        move_file(sqlite_db, destination / 'db.sqlite3', actions)


def rewrite_python_file(path: Path, actions: list[str]) -> None:
    if path.name == Path(__file__).name:
        return
    original = read_text(path)
    updated = original
    for pattern, replacement in IMPORT_REWRITES:
        updated = pattern.sub(replacement, updated)

    if updated != original:
        write_text(path, updated)
        log(actions, f'REWRITE imports: {path.relative_to(PROJECT_ROOT)}')


def rewrite_python_files(actions: list[str]) -> None:
    for path in sorted(PROJECT_ROOT.rglob('*.py')):
        rewrite_python_file(path, actions)


def main() -> int:
    parser = argparse.ArgumentParser(description='Reorganize the smart-home-chef Django project.')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without changing files.')
    args = parser.parse_args()

    actions: list[str] = []

    targets = {name: PROJECT_ROOT / folder for name, folder in TARGET_DIRS.items()}

    if args.dry_run:
        print('Dry run mode enabled. No files will be moved or rewritten.')

    for path in targets.values():
        if not args.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(f'Would move {PROJECT_ROOT / "smart_chef"} -> {targets["smart_chef"]}')
        print(f'Would move {PROJECT_ROOT / "apps"} -> {targets["apps"]}')
        print(f'Would move {PROJECT_ROOT / "app"} -> {targets["app"]} and services -> {targets["app_services"]}')
        print(f'Would merge {PROJECT_ROOT / "services"} -> {targets["services"]}')
        print(f'Would move root scripts -> {targets["scripts"]}')
        print(f'Would move database -> {targets["database"]}')
        print(f'Would move markdown files -> {targets["markdowns"]}')
        print(f'Would move tests -> {targets["tests"]}')
        return 0

    move_tree(PROJECT_ROOT / 'smart_chef', targets['smart_chef'], actions)
    move_tree(PROJECT_ROOT / 'apps', targets['apps'], actions)
    move_services_tree(PROJECT_ROOT / 'services', targets['services'], actions)
    move_app_tree(PROJECT_ROOT / 'app', targets['app'], targets['app_services'], actions)
    move_root_scripts(targets['scripts'], actions)
    move_database(targets['database'], actions)
    move_markdown_files(targets['markdowns'], actions)
    move_root_tests(targets['tests'], actions)
    rewrite_python_files(actions)

    print('\nSummary:')
    for action in actions:
        print(action)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())