#!/usr/bin/env python3
"""Validate a complete multi-document proposal produced by an unattended agent."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

DEFAULT_MAX_DIFF_BYTES = 262_144
DEFAULT_MAX_REPORT_BYTES = 262_144
ALLOWED_SUFFIXES = {".md", ".mdx"}
REPORT_FIELDS = {"decision", "summary", "reason", "evidence", "documents"}
REPORT_DOCUMENT_FIELDS = {
    "path", "reason", "evidence", "previous_version", "proposed_version",
    "proposed_body_sha256", "proposed_document_sha256", "diff",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ValidationError(ValueError):
    """Raised when a repository change violates the proposal contract."""


class ValidationEnvironmentError(RuntimeError):
    """Raised when the repository cannot be inspected reliably."""


@dataclass(frozen=True)
class ValidationConfig:
    max_diff_bytes: int = DEFAULT_MAX_DIFF_BYTES
    max_report_bytes: int = DEFAULT_MAX_REPORT_BYTES


def safe_single_line(value: object, label: str, maximum: int = 4_000) -> str:
    if (
        not isinstance(value, str) or not value.strip() or value != value.strip()
        or "\n" in value or "\r" in value or len(value) > maximum
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValidationError(f"Agent report {label} must be a safe non-empty single line")
    return value


def parse_agent_report(path: Path, max_bytes: int) -> dict[str, object]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ValidationError(f"Could not read agent report {path}: {error}") from error
    if len(payload) > max_bytes:
        raise ValidationError(f"Agent report is too large: {len(payload)} bytes exceeds {max_bytes}")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("Agent report must be valid UTF-8 JSON") from error
    if not isinstance(value, dict) or set(value) != REPORT_FIELDS:
        raise ValidationError("Agent report has an unexpected structure")
    if value["decision"] not in {"proposal", "abstention"}:
        raise ValidationError("Agent report decision must be proposal or abstention")
    for field in ("summary", "reason", "evidence"):
        value[field] = safe_single_line(value[field], field)
    documents = value["documents"]
    if not isinstance(documents, list):
        raise ValidationError("Agent report documents must be a list")
    parsed: list[dict[str, str]] = []
    for index, item in enumerate(documents):
        if not isinstance(item, dict) or set(item) != REPORT_DOCUMENT_FIELDS:
            raise ValidationError(f"Agent report document {index} has an unexpected structure")
        normalized: dict[str, str] = {}
        for field in ("path", "reason", "evidence", "previous_version", "proposed_version"):
            normalized[field] = safe_single_line(item[field], f"documents[{index}].{field}")
        for field in ("proposed_body_sha256", "proposed_document_sha256"):
            if not isinstance(item[field], str) or not SHA256_PATTERN.fullmatch(item[field]):
                raise ValidationError(f"Agent report documents[{index}].{field} is invalid")
            normalized[field] = item[field]
        if not isinstance(item["diff"], str):
            raise ValidationError(f"Agent report documents[{index}].diff must be a string")
        normalized["diff"] = item["diff"]
        parsed.append(normalized)
    if value["decision"] == "proposal" and not parsed:
        raise ValidationError("A proposal report requires at least one document")
    if value["decision"] == "abstention" and parsed:
        raise ValidationError("An abstention report requires an empty documents list")
    value["documents"] = parsed
    return value


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and process.returncode != 0:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValidationEnvironmentError(
            f"git {' '.join(args)} failed with exit code {process.returncode}: {message or 'no error output'}"
        )
    return process


def decode_path(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("Git reported a path that is not valid UTF-8") from error


def resolve_base_commit(root: Path, base_sha: str) -> str:
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", base_sha):
        raise ValidationEnvironmentError("--base-sha must be a full lowercase hexadecimal commit SHA")
    resolved = run_git(root, "rev-parse", "--verify", f"{base_sha}^{{commit}}").stdout.decode("ascii").strip()
    if resolved != base_sha:
        raise ValidationEnvironmentError(f"--base-sha does not resolve exactly to itself: {base_sha} -> {resolved}")
    return resolved


def changed_entries(root: Path, base_sha: str) -> list[tuple[str, str]]:
    output = run_git(root, "diff", "--name-status", "-z", "--no-renames", base_sha, "--").stdout
    tokens = output.split(b"\0")
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status_token = decode_path(tokens[index]); index += 1
        if "\t" in status_token:
            status, path = status_token.split("\t", 1)
        else:
            if index >= len(tokens) or not tokens[index]:
                raise ValidationEnvironmentError("Could not parse NUL-delimited Git output")
            status, path = status_token, decode_path(tokens[index]); index += 1
        entries.append((status, path))
    return entries


def untracked_paths(root: Path) -> list[str]:
    output = run_git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
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
        raise ValidationError(f"production-snapshots is read-only and cannot be changed: {raw_path}")
    if relative.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValidationError(f"Changed file is not Markdown (.md or .mdx): {raw_path}")
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
    if not candidate.exists() or not candidate.is_file():
        raise ValidationError(f"Changed Markdown must be an existing regular file: {raw_path}")
    return candidate


def split_frontmatter(text: str, path: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").strip() != "---":
        raise ValidationError(f"Document must have frontmatter: {path}")
    closing = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n").strip() == "---"), None)
    if closing is None:
        raise ValidationError(f"Unclosed frontmatter in {path}")
    return "".join(lines[: closing + 1]), "".join(lines[closing + 1 :])


def increment_frontmatter_version(frontmatter: str, path: str) -> tuple[str, str, str]:
    lines = frontmatter.splitlines(keepends=True)
    indices = [i for i in range(1, len(lines) - 1) if re.match(r"^\s*version\s*:", lines[i].rstrip("\r\n"))]
    if len(indices) != 1:
        raise ValidationError(f"Frontmatter must contain exactly one version line: {path}")
    index = indices[0]
    match = re.fullmatch(r"version: ([0-9]+)\.([0-9]+)(\r?\n)?", lines[index])
    if match is None:
        raise ValidationError(f"Frontmatter version must use MAJOR.MINOR: {path}")
    major, minor, ending = match.groups()
    previous, proposed = f"{major}.{minor}", f"{major}.{int(minor) + 1}"
    lines[index] = f"version: {proposed}{ending or ''}"
    return "".join(lines), previous, proposed


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_base_text(root: Path, base_sha: str, path: str) -> str:
    try:
        return run_git(root, "show", f"{base_sha}:{path}").stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError(f"Base version of {path} is not valid UTF-8") from error


def read_worktree_text(path: Path, display_path: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValidationError(f"Could not read changed file {display_path}: {error}") from error


def validate_repository(
    repo_root: Path, agent_report: Path, base_sha: str,
    config: ValidationConfig | None = None,
) -> dict[str, object]:
    config = config or ValidationConfig()
    root = repo_root.resolve(strict=True)
    top_level = run_git(root, "rev-parse", "--show-toplevel").stdout.decode("utf-8").strip()
    if Path(top_level).resolve(strict=True) != root:
        raise ValidationEnvironmentError(f"--repo-root must be the Git top level: expected {top_level}, got {root}")
    base_sha = resolve_base_commit(root, base_sha)
    errors: list[str] = []
    current_sha = run_git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.decode("ascii").strip()
    if current_sha != base_sha:
        errors.append(f"HEAD changed after the trusted base was captured: expected {base_sha}, got {current_sha}")
    try:
        report = parse_agent_report(agent_report, config.max_report_bytes)
    except ValidationError as error:
        report = None
        errors.append(str(error))
    entries = changed_entries(root, base_sha)
    untracked = untracked_paths(root)
    changed_files = [path for _, path in entries]
    if untracked:
        errors.append("Added or untracked files are not allowed: " + ", ".join(untracked))
    for status, path in entries:
        if status != "M":
            errors.append(f"Only modification status M is allowed; {path} has status {status}")
    documents_result: list[dict[str, str]] = []
    if report is not None:
        reported_documents = report["documents"]
        assert isinstance(reported_documents, list)
        reported_paths = [str(item["path"]) for item in reported_documents]
        if len(reported_paths) != len(set(reported_paths)):
            errors.append("Agent report contains duplicate document paths")
        if report["decision"] == "abstention":
            if entries or untracked:
                errors.append("An abstention report requires an empty Git diff")
        elif sorted(reported_paths) != sorted(changed_files) or untracked:
            errors.append("Proposal report documents must match every modified file exactly")
        total_diff_bytes = len(run_git(root, "diff", "--binary", "--no-ext-diff", base_sha, "--").stdout)
        if total_diff_bytes > config.max_diff_bytes:
            errors.append(f"Combined diff is too large: {total_diff_bytes} bytes exceeds {config.max_diff_bytes}")
        for item in reported_documents:
            path = str(item["path"])
            try:
                candidate = validate_relative_path(root, path)
                if run_git(root, "cat-file", "-e", f"{base_sha}:{path}", check=False).returncode != 0:
                    raise ValidationError(f"Changed Markdown did not exist in the base commit: {path}")
                before = read_base_text(root, base_sha, path)
                after = read_worktree_text(candidate, path)
                before_frontmatter, before_body = split_frontmatter(before, path)
                after_frontmatter, after_body = split_frontmatter(after, path)
                expected_frontmatter, previous_version, proposed_version = increment_frontmatter_version(before_frontmatter, path)
                if after_frontmatter != expected_frontmatter:
                    raise ValidationError(f"Only the deterministic MINOR version increment is allowed in frontmatter: {path}")
                if after_body == before_body:
                    raise ValidationError(f"Proposed body is unchanged: {path}")
                if item["previous_version"] != previous_version or item["proposed_version"] != proposed_version:
                    raise ValidationError(f"Reported versions do not match {path}")
                if item["proposed_body_sha256"] != sha256_text(after_body):
                    raise ValidationError(f"Modified body does not match the validated proposal: {path}")
                if item["proposed_document_sha256"] != sha256_text(after):
                    raise ValidationError(f"Modified document does not match the validated proposal: {path}")
                expected_diff = "".join(difflib.unified_diff(
                    before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile=f"a/{path}", tofile=f"b/{path}",
                ))
                if item["diff"] != expected_diff:
                    raise ValidationError(f"Reported diff does not match the complete change: {path}")
                documents_result.append({
                    "path": path, "reason": item["reason"], "evidence": item["evidence"],
                    "previous_version": previous_version, "proposed_version": proposed_version,
                })
            except ValidationError as error:
                errors.append(str(error))
    for path in changed_files:
        try:
            validate_relative_path(root, path)
        except ValidationError as error:
            if str(error) not in errors:
                errors.append(str(error))
    diff_check = run_git(root, "diff", "--check", base_sha, "--", check=False)
    if diff_check.returncode != 0:
        details = (diff_check.stdout + diff_check.stderr).decode("utf-8", errors="replace").strip()
        errors.append(f"git diff --check failed: {details or 'no error output'}")
    valid = not errors
    decision = str(report["decision"]) if valid and report is not None else "rejected"
    return {
        "valid": valid, "decision": decision, "base_sha": base_sha,
        "summary": report["summary"] if valid and report else "",
        "evidence": report["evidence"] if valid and report else "",
        "reason": report["reason"] if valid and report else "",
        "changed_files": changed_files, "documents": documents_result if valid else [],
        "errors": errors,
        "limits": {
            "max_diff_bytes": config.max_diff_bytes,
            "max_report_bytes": config.max_report_bytes,
        },
    }


def write_report(path: Path | None, report: dict[str, object]) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(payload)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        sys.stdout.write(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--agent-report", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument(
        "--max-diff-bytes", type=int, default=DEFAULT_MAX_DIFF_BYTES,
        help="Maximum aggregate Git diff size in bytes (default: %(default)s)",
    )
    parser.add_argument(
        "--max-report-bytes", type=int, default=DEFAULT_MAX_REPORT_BYTES,
        help="Maximum structured agent report size in bytes (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_diff_bytes <= 0 or args.max_report_bytes <= 0:
        build_parser().error("diff and report limits must be positive integers")
    config = ValidationConfig(args.max_diff_bytes, args.max_report_bytes)
    try:
        report = validate_repository(args.repo_root, args.agent_report, args.base_sha, config)
        exit_code = 0 if report["valid"] else 1
    except (ValidationError, ValidationEnvironmentError, OSError) as error:
        report = {
            "valid": False, "decision": "error", "base_sha": args.base_sha,
            "summary": "", "evidence": "", "reason": "", "changed_files": [],
            "documents": [], "errors": [str(error)],
            "limits": {
                "max_diff_bytes": config.max_diff_bytes,
                "max_report_bytes": config.max_report_bytes,
            },
        }
        exit_code = 2
    write_report(args.output, report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
