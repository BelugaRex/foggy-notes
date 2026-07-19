from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".build" / "docs"

PAGES = {
    "Home.md": "index.md",
    "Tags.md": "tags.md",
    "Windows-VS-Code-UCP-DeepSeek-Agent-工作流.md": "Windows-VS-Code-UCP-DeepSeek-Agent-工作流.md",
}

LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
FRONT_MATTER_PATTERN = re.compile(
    r"\A---\r?\n(?P<body>.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL
)


def rewrite_link(match: re.Match[str]) -> str:
    label, target = match.groups()
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return match.group(0)

    path, separator, fragment = target.partition("#")
    source_name = "Home.md" if path == "Home" else f"{path}.md"
    if path.endswith(".md"):
        source_name = path

    output_name = PAGES.get(source_name)
    if output_name is None:
        return match.group(0)

    rewritten = output_name
    if separator:
        rewritten = f"{rewritten}#{fragment}"
    return f"[{label}]({rewritten})"


def validate_front_matter(source_name: str, content: str) -> None:
    front_matter_match = FRONT_MATTER_PATTERN.match(content)
    if front_matter_match and "\t" in front_matter_match.group("body"):
        raise ValueError(
            f"{source_name}: YAML front matter must use spaces instead of tabs"
        )


def prepare_site() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    for source_name, output_name in PAGES.items():
        source = ROOT / source_name
        if not source.is_file():
            raise FileNotFoundError(f"Missing documentation source: {source_name}")

        content = source.read_text(encoding="utf-8")
        validate_front_matter(source_name, content)
        content = LINK_PATTERN.sub(rewrite_link, content)
        (OUTPUT / output_name).write_text(content, encoding="utf-8")

    for asset_directory in ("images", "stylesheets"):
        source = ROOT / asset_directory
        if source.is_dir():
            shutil.copytree(source, OUTPUT / asset_directory)

    print(f"Prepared {len(PAGES)} pages in {OUTPUT}")


if __name__ == "__main__":
    prepare_site()