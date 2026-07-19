from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".build" / "docs"

PAGES = {
    "Home.md": "index.md",
    "Windows-VS-Code-UCP-DeepSeek-Agent-工作流.md": "Windows-VS-Code-UCP-DeepSeek-Agent-工作流.md",
    "UCP-设置-VS-Code-默认模型.md": "UCP-设置-VS-Code-默认模型.md",
    "VS-Code-Agent-项目规则.md": "VS-Code-Agent-项目规则.md",
    "VS-Code-Agent-接入-MCP.md": "VS-Code-Agent-接入-MCP.md",
    "VS-Code-Agent-安全与成本.md": "VS-Code-Agent-安全与成本.md",
    "UCP-DeepSeek-常见问题.md": "UCP-DeepSeek-常见问题.md",
}

LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


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


def prepare_site() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    for source_name, output_name in PAGES.items():
        source = ROOT / source_name
        if not source.is_file():
            raise FileNotFoundError(f"Missing documentation source: {source_name}")

        content = source.read_text(encoding="utf-8")
        content = LINK_PATTERN.sub(rewrite_link, content)
        (OUTPUT / output_name).write_text(content, encoding="utf-8")

    images = ROOT / "images"
    if images.is_dir():
        shutil.copytree(images, OUTPUT / "images")

    print(f"Prepared {len(PAGES)} pages in {OUTPUT}")


if __name__ == "__main__":
    prepare_site()