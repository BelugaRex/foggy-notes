from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = Path(".vscode/draft-sync.json")
STATE_VERSION = 1
DRAFT_DIRECTORY_PATTERN = re.compile(r"FN(?P<number>\d+)\Z")
ARTICLE_ID_PATTERN = re.compile(r"FN-\d{3}\Z")
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = {".bak", ".tmp", ".pyc", ".pyo"}


@dataclass(frozen=True)
class DraftStatus:
    draft: str
    status: str
    digest: str
    public_pages: tuple[str, ...]
    article_id: str | None

    @property
    def action(self) -> str:
        return {
            "NEW": "create_root_page",
            "MODIFIED": "update_root_page",
            "ORPHAN": "review_orphan",
            "UNCHANGED": "none",
        }[self.status]

    def to_json(self) -> dict[str, Any]:
        return {
            "draft": self.draft,
            "status": self.status,
            "digest": self.digest,
            "public_pages": list(self.public_pages),
            "article_id": self.article_id,
            "action": self.action,
        }


def should_ignore(path: Path) -> bool:
    return (
        path.name in IGNORED_NAMES
        or path.suffix.lower() in IGNORED_SUFFIXES
        or "__pycache__" in path.parts
    )


def draft_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and not path.is_symlink() and not should_ignore(path)
    )


def file_digest(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.digest()


def directory_digest(directory: Path, files: list[Path]) -> str:
    digest = hashlib.sha256(b"foggy-notes-draft-v1\0")
    for path in files:
        relative_path = path.relative_to(directory).as_posix().encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        digest.update(file_digest(path))
    return digest.hexdigest()


def scan_drafts(root: Path) -> dict[str, str]:
    human = root / "human"
    if not human.is_dir():
        return {}

    directories: list[tuple[int, Path]] = []
    for directory in human.iterdir():
        match = DRAFT_DIRECTORY_PATTERN.fullmatch(directory.name)
        if directory.is_dir() and match is not None:
            directories.append((int(match.group("number")), directory))

    drafts: dict[str, str] = {}
    for _, directory in sorted(directories):
        files = draft_files(directory)
        if not files:
            continue
        draft = directory.relative_to(root).as_posix()
        drafts[draft] = directory_digest(directory, files)
    return drafts


def empty_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "entries": {}}


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return empty_state()

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error}") from error

    if state.get("version") != STATE_VERSION:
        raise ValueError(
            f"{path}: unsupported state version {state.get('version')!r}"
        )
    entries = state.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"{path}: entries must be an object")

    for draft, entry in entries.items():
        if not isinstance(draft, str) or not isinstance(entry, dict):
            raise ValueError(f"{path}: invalid draft entry")
        if not isinstance(entry.get("digest"), str):
            raise ValueError(f"{path}: {draft} is missing a digest")
        if not isinstance(entry.get("public_pages"), list) or not all(
            isinstance(page, str) for page in entry["public_pages"]
        ):
            raise ValueError(f"{path}: {draft} has invalid public_pages")
        article_id = entry.get("article_id")
        if article_id is not None and not isinstance(article_id, str):
            raise ValueError(f"{path}: {draft} has an invalid article_id")
    return state


def collect_statuses(root: Path, state: dict[str, Any]) -> list[DraftStatus]:
    current = scan_drafts(root)
    entries: dict[str, dict[str, Any]] = state["entries"]
    statuses: list[DraftStatus] = []

    for draft, digest in current.items():
        entry = entries.get(draft)
        if entry is None:
            status = "NEW"
            public_pages: tuple[str, ...] = ()
            article_id = None
        else:
            status = "UNCHANGED" if entry["digest"] == digest else "MODIFIED"
            public_pages = tuple(entry["public_pages"])
            article_id = entry.get("article_id")
        statuses.append(
            DraftStatus(draft, status, digest, public_pages, article_id)
        )

    for draft, entry in entries.items():
        if draft not in current:
            statuses.append(
                DraftStatus(
                    draft,
                    "ORPHAN",
                    entry["digest"],
                    tuple(entry["public_pages"]),
                    entry.get("article_id"),
                )
            )
    return sorted(statuses, key=lambda item: item.draft.casefold())


def status_payload(statuses: list[DraftStatus]) -> dict[str, Any]:
    counts = {
        status: sum(item.status == status for item in statuses)
        for status in ("NEW", "MODIFIED", "ORPHAN", "UNCHANGED")
    }
    return {
        "version": STATE_VERSION,
        "pending": [
            item.to_json() for item in statuses if item.status != "UNCHANGED"
        ],
        "unchanged": [
            item.to_json() for item in statuses if item.status == "UNCHANGED"
        ],
        "summary": counts,
    }


def print_human_status(statuses: list[DraftStatus]) -> None:
    if not statuses:
        print("没有可检查的本地草稿。")
        return

    for item in statuses:
        target = ", ".join(item.public_pages) or "尚未映射公开页"
        print(f"[{item.status}] {item.draft} -> {target}")

    pending = sum(item.status != "UNCHANGED" for item in statuses)
    unchanged = sum(item.status == "UNCHANGED" for item in statuses)
    print(f"\n汇总：{pending} 个待处理，{unchanged} 个已同步。")


def resolve_state_path(root: Path, value: Path | None) -> Path:
    if value is None:
        return root / DEFAULT_STATE
    return value if value.is_absolute() else root / value


def resolve_draft(root: Path, value: str) -> tuple[str, Path]:
    path = Path(value)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    human = (root / "human").resolve()
    if path.parent != human or DRAFT_DIRECTORY_PATTERN.fullmatch(path.name) is None:
        raise ValueError("draft must be a direct human/FN<number> directory")
    files = draft_files(path) if path.is_dir() else []
    if not files:
        raise ValueError(f"{path}: draft directory is missing or empty")
    return path.relative_to(root).as_posix(), path


def resolve_public_pages(root: Path, values: list[str]) -> list[str]:
    pages: list[str] = []
    for value in values:
        path = Path(value)
        path = path.resolve() if path.is_absolute() else (root / path).resolve()
        try:
            relative_path = path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"{value}: public page must be inside the repository") from error
        if not path.is_file():
            raise ValueError(f"{value}: public page does not exist")
        pages.append(relative_path.as_posix())
    return pages


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def mark_synced(
    root: Path,
    state_path: Path,
    draft_value: str,
    expected_digest: str | None,
    public_page_values: list[str] | None,
    article_id_value: str | None,
) -> None:
    if expected_digest is None:
        raise ValueError("--expected-digest is required with --mark-synced")

    draft, directory = resolve_draft(root, draft_value)
    digest = directory_digest(directory, draft_files(directory))
    if digest != expected_digest:
        raise ValueError(
            f"{draft}: draft changed during synchronization; run the check again"
        )

    state = load_state(state_path)
    existing = state["entries"].get(draft, {})
    page_values = public_page_values or existing.get("public_pages", [])
    public_pages = resolve_public_pages(root, page_values)
    if not public_pages:
        raise ValueError("at least one --public-page is required for a new draft")

    article_id = (
        article_id_value
        if article_id_value is not None
        else existing.get("article_id")
    )
    if article_id is not None and ARTICLE_ID_PATTERN.fullmatch(article_id) is None:
        raise ValueError("--article-id must use the FN-000 format")

    state["entries"][draft] = {
        "digest": digest,
        "public_pages": public_pages,
        "article_id": article_id,
    }
    write_state(state_path, state)
    print(f"已标记同步：{draft} -> {', '.join(public_pages)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect unpublished changes in local human/FN* drafts."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mark-synced", metavar="DRAFT")
    parser.add_argument("--expected-digest")
    parser.add_argument("--public-page", action="append")
    parser.add_argument("--article-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    state_path = resolve_state_path(root, args.state)
    try:
        if args.mark_synced is not None:
            mark_synced(
                root,
                state_path,
                args.mark_synced,
                args.expected_digest,
                args.public_page,
                args.article_id,
            )
            return 0

        statuses = collect_statuses(root, load_state(state_path))
        if args.as_json:
            print(
                json.dumps(
                    status_payload(statuses),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print_human_status(statuses)
        if args.check and any(item.status != "UNCHANGED" for item in statuses):
            return 1
        return 0
    except (OSError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())