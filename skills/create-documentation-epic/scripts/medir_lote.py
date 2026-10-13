#!/usr/bin/env python3
"""Measure prepared Markdown using the documentary agent's structured format."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

TARGET = 45_000
TECHNICAL_LIMIT = 60_000


def validate_issue(value: object, location: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"key", "summary", "description"}:
        raise ValueError(f"{location}: expected key, summary and description")
    for field in ("key", "summary", "description"):
        if not isinstance(value[field], str):
            raise ValueError(f"{location}.{field}: expected text")
    if not value["key"].strip() or value["key"] != value["key"].strip():
        raise ValueError(f"{location}.key: expected nonempty key without outer spaces")
    if not value["summary"].strip():
        raise ValueError(f"{location}.summary: expected nonempty text")
    return value


def compose_context(batch: object) -> str:
    if not isinstance(batch, dict) or set(batch) != {"documentation_task", "epic", "tasks"}:
        raise ValueError("Expected documentation_task, epic and tasks")
    human = validate_issue(batch["documentation_task"], "documentation_task")
    epic = validate_issue(batch["epic"], "epic")
    if not isinstance(batch["tasks"], list) or not batch["tasks"]:
        raise ValueError("tasks: expected a nonempty list")
    tasks = [validate_issue(task, f"tasks[{index}]") for index, task in enumerate(batch["tasks"])]
    keys = [issue["key"] for issue in [human, epic, *tasks]]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate issue keys")
    sections = [f"Documentation task {human['key']}: {human['summary']}\n\n{human['description']}"]
    for kind, issue in [("Epic", epic), *(("Task", task) for task in tasks)]:
        sections.append(
            f"{kind} {issue['key']}: {issue['summary'].strip()}\n\n{issue['description'].strip()}".rstrip()
        )
    return "\n\n".join(sections)


def measure(batch: object) -> dict[str, object]:
    context = compose_context(batch)
    count = len(context)
    code = 2 if count > TECHNICAL_LIMIT else 1 if count > TARGET else 0
    return {
        "characters": count,
        "target": TARGET,
        "technical_limit": TECHNICAL_LIMIT,
        "within_target": count <= TARGET,
        "within_technical_limit": count <= TECHNICAL_LIMIT,
        "sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
        "exit_code": code,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path, help="Prepared batch JSON (UTF-8)")
    args = parser.parse_args(argv)
    try:
        # Read bytes so CRLF inside JSON string values is not normalized by text IO.
        batch = json.loads(args.batch.read_bytes().decode("utf-8-sig"))
        report = measure(batch)
    except (OSError, UnicodeError, ValueError) as error:
        # Do not echo file contents or paths that could carry sensitive data.
        print(f"Invalid batch ({type(error).__name__}); check UTF-8 JSON and schema.", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=True))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
