#!/usr/bin/env python3
"""Validate a documentation proposal produced by an unattended agent."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence


DEFAULT_MAX_DIFF_BYTES = 65_536
DEFAULT_MAX_CHANGED_LINES = 200
DEFAULT_MAX_REPORT_BYTES = 16_384
ALLOWED_SUFFIXES = {".md", ".mdx"}
REPORT_FIELDS = (
    "Decisión",
    "Documento",
    "Evidencia",
    "Texto anterior",
    "Texto propuesto",
    "Motivo",
)


class ValidationError(ValueError):
    """Raised when a repository change violates the proposal contract."""


class ValidationEnvironmentError(RuntimeError):
    """Raised when the repository cannot be inspected reliably."""


@dataclass(frozen=True)
class ValidationConfig:
    max_diff_bytes: int = DEFAULT_MAX_DIFF_BYTES
    max_changed_lines: int = DEFAULT_MAX_CHANGED_LINES
    max_report_bytes: int = DEFAULT_MAX_REPORT_BYTES


def parse_agent_report(path: Path, max_bytes: int) -> dict[str, str]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ValidationError(f"Could not read agent report {path}: {error}") from error

    if len(payload) > max_bytes:
        raise ValidationError(
            f"Agent report is too large: {len(payload)} bytes exceeds {max_bytes}"
        )

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("Agent report is not valid UTF-8") from error

    lines = text.splitlines()
    if len(lines) != len(REPORT_FIELDS):
        raise ValidationError(
            "Agent report must contain exactly these six single-line fields in order: "
            + ", ".join(REPORT_FIELDS)
        )

    fields: dict[str, str] = {}
    for expected_name, line in zip(REPORT_FIELDS, lines):
        name, separator, value = line.partition(": ")
        if not separator or name != expected_name or not value.strip():
            raise ValidationError(
                "Agent report must contain exactly these six single-line fields in order: "
                + ", ".join(REPORT_FIELDS)
            )
        fields[name] = value.strip()

    if fields["Decisión"] not in {"propuesta", "abstención"}:
        raise ValidationError(
            "Agent report Decisión must be exactly 'propuesta' or 'abstención'"
        )

    return fields


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and process.returncode != 0:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValidationEnvironmentError(
            f"git {' '.join(args)} failed with exit code "
            f"{process.returncode}: {message or 'no error output'}"
        )
    return process


def decode_path(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("Git reported a path that is not valid UTF-8") from error


def resolve_base_commit(root: Path, base_sha: str) -> str:
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", base_sha):
        raise ValidationEnvironmentError(
            "--base-sha must be a full lowercase hexadecimal commit SHA"
        )

    resolved = run_git(root, "rev-parse", "--verify", f"{base_sha}^{{commit}}").stdout
    resolved_sha = resolved.decode("ascii", errors="strict").strip()
    if resolved_sha != base_sha:
        raise ValidationEnvironmentError(
            f"--base-sha does not resolve exactly to itself: {base_sha} -> {resolved_sha}"
        )
    return resolved_sha


def changed_entries(root: Path, base_sha: str) -> list[tuple[str, str]]:
    output = run_git(
        root,
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        base_sha,
        "--",
    ).stdout
    tokens = output.split(b"\0")
    entries: list[tuple[str, str]] = []
    index = 0

    while index < len(tokens) and tokens[index]:
        status_token = decode_path(tokens[index])
        index += 1

        # Git normally separates status and path with NUL when -z is used, but
        # accept the tab form as well for compatibility with older clients.
        if "\t" in status_token:
            status, path = status_token.split("\t", 1)
        else:
            status = status_token
            if index >= len(tokens) or not tokens[index]:
                raise ValidationEnvironmentError(
                    "Could not parse the NUL-delimited git diff name-status output"
                )
            path = decode_path(tokens[index])
            index += 1

        entries.append((status, path))

    return entries


def untracked_paths(root: Path) -> list[str]:
    output = run_git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout
    return [decode_path(item) for item in output.split(b"\0") if item]


def validate_relative_path(root: Path, raw_path: str) -> Path:
    if not raw_path or "\\" in raw_path:
        raise ValidationError(f"Unsafe repository path: {raw_path!r}")

    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValidationError(f"Path traversal or absolute path is not allowed: {raw_path!r}")

    if not relative.parts or relative.parts[0] != "docs":
        raise ValidationError(f"Changed file is outside docs/: {raw_path}")

    if "production-snapshots" in relative.parts:
        raise ValidationError(
            f"production-snapshots is read-only and cannot be changed: {raw_path}"
        )

    candidate = root.joinpath(*relative.parts)
    root_resolved = root.resolve(strict=True)
    try:
        candidate.resolve(strict=False).relative_to(root_resolved)
    except ValueError as error:
        raise ValidationError(f"Path escapes the repository root: {raw_path}") from error

    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValidationError(f"Symlinks are not allowed in changed paths: {raw_path}")

    if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValidationError(f"Changed file is not Markdown (.md or .mdx): {raw_path}")

    return candidate


def extract_frontmatter(text: str, path: str) -> tuple[str, ...]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ()

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return tuple(lines[: index + 1])

    raise ValidationError(f"Unclosed frontmatter in {path}")


def read_base_text(root: Path, base_sha: str, path: str) -> str:
    process = run_git(root, "show", f"{base_sha}:{path}")
    try:
        return process.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError(f"Base version of {path} is not valid UTF-8") from error


def read_worktree_text(path: Path, display_path: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError(f"Working copy of {display_path} is not valid UTF-8") from error
    except OSError as error:
        raise ValidationError(f"Could not read changed file {display_path}: {error}") from error


def changed_line_count(root: Path, base_sha: str, path: str) -> int:
    output = run_git(root, "diff", "--numstat", base_sha, "--", path).stdout
    line = output.decode("utf-8", errors="replace").strip()
    if not line:
        return 0

    fields = line.split("\t", 2)
    if len(fields) < 2 or fields[0] == "-" or fields[1] == "-":
        raise ValidationError(f"Binary or unparsable diff is not allowed: {path}")

    try:
        return int(fields[0]) + int(fields[1])
    except ValueError as error:
        raise ValidationError(f"Could not count changed lines for {path}") from error


def validate_repository(
    repo_root: Path,
    agent_report: Path,
    base_sha: str,
    config: ValidationConfig | None = None,
) -> dict[str, object]:
    config = config or ValidationConfig()
    root = repo_root.resolve(strict=True)

    top_level = run_git(root, "rev-parse", "--show-toplevel").stdout.decode(
        "utf-8", errors="replace"
    ).strip()
    if Path(top_level).resolve(strict=True) != root:
        raise ValidationEnvironmentError(
            f"--repo-root must be the Git top level: expected {top_level}, got {root}"
        )

    base_sha = resolve_base_commit(root, base_sha)

    errors: list[str] = []
    current_sha = run_git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.decode(
        "ascii", errors="strict"
    ).strip()
    if current_sha != base_sha:
        errors.append(
            f"HEAD changed after the trusted base was captured: "
            f"expected {base_sha}, got {current_sha}"
        )

    report_fields: dict[str, str] | None = None
    try:
        report_fields = parse_agent_report(agent_report, config.max_report_bytes)
    except ValidationError as error:
        errors.append(str(error))

    entries = changed_entries(root, base_sha)
    untracked = untracked_paths(root)
    changed_files = [path for _, path in entries]

    if untracked:
        errors.append(
            "Added or untracked files are not allowed: " + ", ".join(untracked)
        )

    has_changes = bool(entries or untracked)
    if has_changes and len(entries) != 1:
        errors.append(
            f"Exactly one modified file is required; found {len(entries)}: "
            + ", ".join(changed_files)
        )

    selected_path: str | None = None
    before_text: str | None = None
    after_text: str | None = None
    if has_changes and len(entries) == 1:
        status, raw_path = entries[0]
        selected_path = raw_path

        if status != "M":
            errors.append(
                f"Only modification status M is allowed; {raw_path} has status {status}"
            )

        try:
            candidate = validate_relative_path(root, raw_path)
            if not candidate.exists() or not candidate.is_file():
                raise ValidationError(
                    f"Changed Markdown must be an existing regular file: {raw_path}"
                )

            tracked = run_git(
                root, "cat-file", "-e", f"{base_sha}:{raw_path}", check=False
            )
            if tracked.returncode != 0:
                raise ValidationError(
                    f"Changed Markdown did not exist in the base commit: {raw_path}"
                )

            before_text = read_base_text(root, base_sha, raw_path)
            after_text = read_worktree_text(candidate, raw_path)
            if extract_frontmatter(before_text, raw_path) != extract_frontmatter(
                after_text, raw_path
            ):
                raise ValidationError(f"Frontmatter changes are not allowed: {raw_path}")

            diff = run_git(
                root, "diff", "--binary", "--no-ext-diff", base_sha, "--", raw_path
            ).stdout
            if len(diff) > config.max_diff_bytes:
                raise ValidationError(
                    f"Diff is too large for {raw_path}: {len(diff)} bytes exceeds "
                    f"{config.max_diff_bytes}"
                )

            line_count = changed_line_count(root, base_sha, raw_path)
            if line_count > config.max_changed_lines:
                raise ValidationError(
                    f"Diff changes too many lines in {raw_path}: {line_count} exceeds "
                    f"{config.max_changed_lines}"
                )
        except ValidationError as error:
            errors.append(str(error))

    if report_fields is not None:
        reported_decision = report_fields["Decisión"]
        reported_document = report_fields["Documento"]
        if reported_decision == "propuesta":
            if len(entries) != 1 or untracked:
                errors.append(
                    "A propuesta report requires exactly one modified Markdown file"
                )
            if selected_path is not None and reported_document != selected_path:
                errors.append(
                    "Agent report Documento does not match the modified file: "
                    f"reported {reported_document!r}, changed {selected_path!r}"
                )
            if before_text is not None and after_text is not None:
                previous_text = report_fields["Texto anterior"]
                proposed_text = report_fields["Texto propuesto"]
                if previous_text not in before_text:
                    errors.append(
                        "Agent report Texto anterior does not exist in the base document"
                    )
                if proposed_text not in after_text:
                    errors.append(
                        "Agent report Texto propuesto does not exist in the modified document"
                    )
                if previous_text in after_text:
                    errors.append(
                        "Agent report Texto anterior still exists in the modified document"
                    )
                if proposed_text in before_text:
                    errors.append(
                        "Agent report Texto propuesto already exists in the base document"
                    )
        else:
            if has_changes:
                errors.append("An abstención report requires an empty diff")
            if reported_document != "ninguno":
                errors.append(
                    "An abstención report must use 'ninguno' as Documento"
                )
            for field_name in ("Texto anterior", "Texto propuesto"):
                if report_fields[field_name] != "no aplica":
                    errors.append(
                        f"An abstención report must use 'no aplica' as {field_name}"
                    )

    diff_check = run_git(root, "diff", "--check", base_sha, "--", check=False)
    if diff_check.returncode != 0:
        details = (
            diff_check.stdout + diff_check.stderr
        ).decode("utf-8", errors="replace").strip()
        errors.append(f"git diff --check failed: {details or 'no error output'}")

    valid = not errors
    if valid and report_fields is not None:
        decision = (
            "proposal"
            if report_fields["Decisión"] == "propuesta"
            else "abstention"
        )
    else:
        decision = "rejected"

    return {
        "valid": valid,
        "decision": decision,
        "base_sha": base_sha,
        "changed_files": [selected_path] if selected_path else changed_files,
        "errors": errors,
        "limits": {
            "max_diff_bytes": config.max_diff_bytes,
            "max_changed_lines": config.max_changed_lines,
            "max_report_bytes": config.max_report_bytes,
        },
    }


def write_report(path: Path | None, report: dict[str, object]) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(payload)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the local diff produced by the documentation agent."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Git repository root (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON validation report",
    )
    parser.add_argument(
        "--agent-report",
        type=Path,
        required=True,
        help="Path to the final Markdown report produced by the agent",
    )
    parser.add_argument(
        "--base-sha",
        required=True,
        help="Exact trusted commit SHA captured immediately after checkout",
    )
    parser.add_argument(
        "--max-diff-bytes",
        type=int,
        default=DEFAULT_MAX_DIFF_BYTES,
    )
    parser.add_argument(
        "--max-changed-lines",
        type=int,
        default=DEFAULT_MAX_CHANGED_LINES,
    )
    parser.add_argument(
        "--max-report-bytes",
        type=int,
        default=DEFAULT_MAX_REPORT_BYTES,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (
        args.max_diff_bytes <= 0
        or args.max_changed_lines <= 0
        or args.max_report_bytes <= 0
    ):
        build_parser().error("diff and report limits must be positive integers")

    config = ValidationConfig(
        max_diff_bytes=args.max_diff_bytes,
        max_changed_lines=args.max_changed_lines,
        max_report_bytes=args.max_report_bytes,
    )
    try:
        report = validate_repository(
            args.repo_root,
            args.agent_report,
            args.base_sha,
            config,
        )
        exit_code = 0 if report["valid"] else 1
    except (ValidationError, ValidationEnvironmentError, OSError) as error:
        report = {
            "valid": False,
            "decision": "error",
            "base_sha": args.base_sha,
            "changed_files": [],
            "errors": [str(error)],
            "limits": {
                "max_diff_bytes": config.max_diff_bytes,
                "max_changed_lines": config.max_changed_lines,
                "max_report_bytes": config.max_report_bytes,
            },
        }
        exit_code = 2

    write_report(args.output, report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
