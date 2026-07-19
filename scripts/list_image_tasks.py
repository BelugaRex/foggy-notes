from __future__ import annotations

import re
from dataclasses import dataclass

from prepare_site import PAGES, ROOT


IMAGE_METADATA_PATTERN = re.compile(
    r"<!-- image-id: (?P<image_id>FN-\d{3}-\d{2}) \| "
    r"path: (?P<path>images/[a-z0-9-]+/[a-z0-9-]+\.png) -->"
)
PLACEHOLDER_PATTERN = re.compile(
    r"> \[此处应有：图 (?P<image_id>FN-\d{3}-\d{2})——(?P<description>.+)\]"
)
IMAGE_PATTERN = re.compile(r"!\[(?P<description>[^]]+)\]\((?P<path>[^)]+)\)")


@dataclass(frozen=True)
class ImageTask:
    source_name: str
    image_id: str
    asset_path: str
    description: str
    uses_placeholder: bool

    @property
    def asset_exists(self) -> bool:
        return (ROOT / self.asset_path).is_file()

    @property
    def status(self) -> str:
        if not self.asset_exists:
            return "[ ]"
        if self.uses_placeholder:
            return "[~]"
        return "[x]"


def parse_image_tasks(source_name: str) -> list[ImageTask]:
    source = ROOT / source_name
    lines = source.read_text(encoding="utf-8").splitlines()
    tasks: list[ImageTask] = []

    for line_index, line in enumerate(lines):
        metadata_match = IMAGE_METADATA_PATTERN.fullmatch(line)
        if metadata_match is None:
            continue

        image_id = metadata_match.group("image_id")
        asset_path = metadata_match.group("path")
        article_id = image_id.rsplit("-", maxsplit=1)[0].lower()
        expected_path = f"images/{article_id}/{image_id.lower()}.png"
        if asset_path != expected_path:
            raise ValueError(
                f"{source_name}:{line_index + 1}: {image_id} should use {expected_path}"
            )

        if line_index + 1 >= len(lines):
            raise ValueError(f"{source_name}:{line_index + 1}: missing image task body")

        task_line = lines[line_index + 1]
        placeholder_match = PLACEHOLDER_PATTERN.fullmatch(task_line)
        image_match = IMAGE_PATTERN.fullmatch(task_line)

        if placeholder_match is not None:
            task_image_id = placeholder_match.group("image_id")
            if task_image_id != image_id:
                raise ValueError(
                    f"{source_name}:{line_index + 2}: expected figure {image_id}, "
                    f"found {task_image_id}"
                )
            description = placeholder_match.group("description")
            uses_placeholder = True
        elif image_match is not None:
            referenced_path = image_match.group("path")
            if referenced_path != asset_path:
                raise ValueError(
                    f"{source_name}:{line_index + 2}: expected image path {asset_path}, "
                    f"found {referenced_path}"
                )
            description = image_match.group("description")
            uses_placeholder = False
        else:
            raise ValueError(
                f"{source_name}:{line_index + 2}: image metadata must be followed by "
                "a placeholder or Markdown image"
            )

        tasks.append(
            ImageTask(
                source_name=source_name,
                image_id=image_id,
                asset_path=asset_path,
                description=description,
                uses_placeholder=uses_placeholder,
            )
        )

    return tasks


def main() -> None:
    tasks_by_source = {
        source_name: tasks
        for source_name in PAGES
        if (tasks := parse_image_tasks(source_name))
    }

    for source_name, tasks in tasks_by_source.items():
        print(f"\n{source_name}")
        for task in tasks:
            print(f"  {task.status} {task.image_id} -> {task.asset_path}")
            print(f"      {task.description}")

    all_tasks = [task for tasks in tasks_by_source.values() for task in tasks]
    pending_count = sum(not task.asset_exists for task in all_tasks)
    replacement_count = sum(
        task.asset_exists and task.uses_placeholder for task in all_tasks
    )
    completed_count = sum(
        task.asset_exists and not task.uses_placeholder for task in all_tasks
    )

    print(
        f"\n汇总：{pending_count} 张待准备，{replacement_count} 张待替换，"
        f"{completed_count} 张已完成。"
    )


if __name__ == "__main__":
    main()