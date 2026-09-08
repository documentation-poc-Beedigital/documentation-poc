#!/usr/bin/env python3
"""Prepare safe metadata for publishing a validated documentation proposal."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


ISSUE_KEY_PATTERN = re.compile(
    r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[1-9][0-9]*"
)
FULL_SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
POSITIVE_INTEGER_PATTERN = re.compile(r"[1-9][0-9]*")
DOCUMENTATION_PREFIX_PATTERN = re.compile(r"^\[documentación\]", re.IGNORECASE)
REPOSITORY_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
)
ALLOWED_SUFFIXES = {".md", ".mdx"}
MAX_AGENT_REPORT_BYTES = 262_144
FRONTMATTER_VERSION_PATTERN = re.compile(
    r"^version: ([0-9]+\.[0-9]+)\r?$", re.MULTILINE
)


class PublicationPreparationError(ValueError):
    """Raised when publication inputs do not match the validated repository state."""


def load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationPreparationError(f"Could not read {label}: {error}") from error
    if not isinstance(value, dict):
        raise PublicationPreparationError(f"{label} must contain a JSON object")
    return value


def load_ticket(path: Path) -> dict[str, str]:
    value = load_json_object(path, "ticket JSON")
    expected = {"issue_key", "issue_summary", "issue_description"}
    if set(value) != expected:
        raise PublicationPreparationError(
            "Ticket JSON must contain exactly issue_key, issue_summary and issue_description"
        )

    issue_key = value["issue_key"]
    issue_summary = value["issue_summary"]
    issue_description = value["issue_description"]
    if not isinstance(issue_key, str) or not ISSUE_KEY_PATTERN.fullmatch(issue_key):
        raise PublicationPreparationError("issue_key is not a validated Jira-style key")
    if not 3 <= len(issue_key) <= 64:
        raise PublicationPreparationError("issue_key must contain between 3 and 64 characters")
    if (
        not isinstance(issue_summary, str)
        or not issue_summary.strip()
        or len(issue_summary) > 200
        or any(ord(character) < 32 for character in issue_summary)
    ):
        raise PublicationPreparationError("issue_summary is not a safe single-line value")
    if (
        not isinstance(issue_description, str)
        or not issue_description.strip()
        or len(issue_description) > 20_000
        or any(
            ord(character) < 32 and character not in "\r\n\t"
            for character in issue_description
        )
    ):
        raise PublicationPreparationError("issue_description is not a safe Jira description")
    return {
        "issue_key": issue_key,
        "issue_summary": issue_summary,
        "issue_description": issue_description,
    }


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
        details = process.stderr.decode("utf-8", errors="replace").strip()
        raise PublicationPreparationError(
            f"git {' '.join(args)} failed: {details or 'no error output'}"
        )
    return process


def decode_git_path(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationPreparationError("Git returned a non-UTF-8 path") from error


def changed_entries(root: Path, base_sha: str) -> list[tuple[str, str]]:
    raw = run_git(
        root,
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        base_sha,
        "--",
    ).stdout
    tokens = raw.split(b"\0")
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status_token = decode_git_path(tokens[index])
        index += 1
        if "\t" in status_token:
            status, path = status_token.split("\t", 1)
        else:
            if index >= len(tokens) or not tokens[index]:
                raise PublicationPreparationError("Could not parse Git changed paths")
            status = status_token
            path = decode_git_path(tokens[index])
            index += 1
        entries.append((status, path))
    return entries


def untracked_paths(root: Path) -> list[str]:
    raw = run_git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    return [decode_git_path(token) for token in raw.split(b"\0") if token]


def validate_base_state(root: Path, base_sha: str) -> None:
    top_level = run_git(root, "rev-parse", "--show-toplevel").stdout.decode(
        "utf-8", errors="strict"
    ).strip()
    if Path(top_level).resolve(strict=True) != root:
        raise PublicationPreparationError("repo_root must be the Git repository top level")
    if not FULL_SHA_PATTERN.fullmatch(base_sha):
        raise PublicationPreparationError("BASE_SHA must be a full lowercase commit SHA")
    resolved = run_git(root, "rev-parse", "--verify", f"{base_sha}^{{commit}}").stdout
    if resolved.decode("ascii", errors="strict").strip() != base_sha:
        raise PublicationPreparationError("BASE_SHA does not resolve exactly to itself")
    current = run_git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout
    if current.decode("ascii", errors="strict").strip() != base_sha:
        raise PublicationPreparationError("HEAD no longer matches the trusted BASE_SHA")


def validate_document_path(root: Path, raw_path: str) -> Path:
    if (
        not raw_path
        or "\\" in raw_path
        or any(ord(character) < 32 or ord(character) == 127 for character in raw_path)
    ):
        raise PublicationPreparationError(f"Unsafe validated document path: {raw_path!r}")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PublicationPreparationError(f"Unsafe validated document path: {raw_path!r}")
    if not relative.parts or relative.parts[0] != "docs":
        raise PublicationPreparationError(f"Validated document is outside docs/: {raw_path}")
    if "production-snapshots" in relative.parts:
        raise PublicationPreparationError("production-snapshots cannot be published")
    if relative.suffix.lower() not in ALLOWED_SUFFIXES:
        raise PublicationPreparationError("Validated document is not Markdown")

    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PublicationPreparationError("Validated document path contains a symlink")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise PublicationPreparationError(
            "Validated document is not an existing repository file"
        ) from error
    if not candidate.is_file():
        raise PublicationPreparationError("Validated document is not a regular file")
    return candidate


def validate_repository_state(
    root: Path,
    base_sha: str,
    decision: str,
    changed_files: list[object],
) -> list[str]:
    validate_base_state(root, base_sha)
    entries = changed_entries(root, base_sha)
    untracked = untracked_paths(root)
    if untracked:
        raise PublicationPreparationError(
            "Untracked files prevent publication: " + ", ".join(untracked)
        )

    if decision == "abstention":
        if changed_files != []:
            raise PublicationPreparationError(
                "An abstention validation result must have no changed_files"
            )
        if entries:
            raise PublicationPreparationError("An abstention requires an empty Git diff")
        return []

    if not changed_files or any(not isinstance(path, str) for path in changed_files):
        raise PublicationPreparationError("A proposal requires Markdown paths in changed_files")
    documents = [str(path) for path in changed_files]
    if len(documents) != len(set(documents)):
        raise PublicationPreparationError("changed_files contains duplicate paths")
    for document in documents:
        validate_document_path(root, document)
    if sorted(entries) != sorted(("M", document) for document in documents):
        raise PublicationPreparationError(
            "The Git diff does not match all validated Markdown documents: "
            f"expected {documents!r}, found {entries!r}"
        )

    diff_check = run_git(root, "diff", "--check", base_sha, "--", check=False)
    if diff_check.returncode != 0:
        details = (diff_check.stdout + diff_check.stderr).decode(
            "utf-8", errors="replace"
        ).strip()
        raise PublicationPreparationError(
            f"git diff --check against BASE_SHA failed: {details or 'no error output'}"
        )
    return documents


def read_agent_report(path: Path) -> dict[str, object]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise PublicationPreparationError(f"Could not read agent report: {error}") from error
    if len(payload) > MAX_AGENT_REPORT_BYTES:
        raise PublicationPreparationError("Agent report exceeds the validated size limit")
    try:
        report = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationPreparationError("Agent report is not valid UTF-8 JSON") from error
    if not isinstance(report, dict) or set(report) != {
        "decision", "summary", "reason", "evidence", "documents"
    }:
        raise PublicationPreparationError("Agent report has an unexpected structure")
    return report


def extract_document_version(content: bytes, label: str) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationPreparationError(f"{label} is not valid UTF-8") from error
    matches = FRONTMATTER_VERSION_PATTERN.findall(text)
    if len(matches) != 1:
        raise PublicationPreparationError(
            f"{label} must contain exactly one MAJOR.MINOR version"
        )
    return matches[0]


def document_versions(root: Path, base_sha: str, document: str) -> tuple[str, str]:
    previous = run_git(root, "show", f"{base_sha}:{document}").stdout
    try:
        proposed = root.joinpath(*PurePosixPath(document).parts).read_bytes()
    except OSError as error:
        raise PublicationPreparationError("Could not read proposed document") from error
    return (
        extract_document_version(previous, "Base document"),
        extract_document_version(proposed, "Proposed document"),
    )


def escape_markdown_inline(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", r"\\\1", value)


def build_pull_request_title(issue_key: str, issue_summary: str) -> str:
    normalized_summary = issue_summary.strip()
    while match := DOCUMENTATION_PREFIX_PATTERN.match(normalized_summary):
        normalized_summary = normalized_summary[match.end() :].lstrip()
    if not normalized_summary:
        raise PublicationPreparationError(
            "issue_summary must contain meaningful text after [Documentación]"
        )
    return f"{issue_key} [Documentación] {normalized_summary}"


def build_pull_request_body(
    ticket: Mapping[str, str],
    report: Mapping[str, object],
    actions_url: str,
) -> str:
    documents = report.get("documents")
    if not isinstance(documents, list) or not documents:
        raise PublicationPreparationError("Proposal report must describe its documents")
    document_sections: list[str] = []
    for item in documents:
        if not isinstance(item, dict):
            raise PublicationPreparationError("Proposal report document is invalid")
        path = item.get("path")
        reason = item.get("reason")
        evidence = item.get("evidence")
        previous = item.get("previous_version")
        proposed = item.get("proposed_version")
        if not all(isinstance(value, str) for value in (path, reason, evidence, previous, proposed)):
            raise PublicationPreparationError("Proposal report document metadata is invalid")
        document_sections.append(
            f"### `{path}`\n\n"
            f"- Versión: `{previous}` → `{proposed}`\n"
            f"- Motivo: {escape_markdown_inline(reason)}\n"
            f"- Evidencia: {escape_markdown_inline(evidence)}\n"
        )
    summary = report.get("summary")
    reason = report.get("reason")
    evidence = report.get("evidence")
    if not all(isinstance(value, str) for value in (summary, reason, evidence)):
        raise PublicationPreparationError("Proposal report summary is invalid")
    return (
        "## Propuesta documental automatizada\n\n"
        f"**Clave Jira:** `{ticket['issue_key']}`\n\n"
        f"**Resumen:** {escape_markdown_inline(ticket['issue_summary'])}\n\n"
        "## Informe del agente\n\n"
        f"**Cambio:** {escape_markdown_inline(summary)}\n\n"
        f"**Motivo:** {escape_markdown_inline(reason)}\n\n"
        f"**Evidencia:** {escape_markdown_inline(evidence)}\n\n"
        "## Documentos afectados\n\n"
        + "\n".join(document_sections)
        + "\n"
        f"[Ver ejecución de GitHub Actions]({actions_url})\n\n"
        "> Esta propuesta fue generada por Gemini y validada "
        "determinísticamente antes de su publicación.\n"
    )


def prepare_publication(
    repo_root: Path,
    validation_result: Path,
    ticket_file: Path,
    agent_report: Path,
    body_file: Path,
    base_sha: str,
    run_id: str,
    run_attempt: str,
    repository: str,
    server_url: str,
) -> dict[str, str]:
    root = repo_root.resolve(strict=True)
    validation = load_json_object(validation_result, "validation result")
    if validation.get("valid") is not True:
        raise PublicationPreparationError("validation-result.json valid must be exactly true")
    decision = validation.get("decision")
    if decision not in {"proposal", "abstention"}:
        raise PublicationPreparationError(
            "validation-result.json decision must be proposal or abstention"
        )
    if validation.get("base_sha") != base_sha:
        raise PublicationPreparationError(
            "validation-result.json base_sha does not match the trusted BASE_SHA"
        )
    changed_files = validation.get("changed_files")
    if not isinstance(changed_files, list):
        raise PublicationPreparationError("validation-result.json changed_files must be a list")

    documents = validate_repository_state(root, base_sha, decision, changed_files)
    if decision == "abstention":
        return {"publish": "false", "decision": "abstention"}

    ticket = load_ticket(ticket_file)
    if not POSITIVE_INTEGER_PATTERN.fullmatch(run_id):
        raise PublicationPreparationError("github.run_id must be a positive integer")
    if not POSITIVE_INTEGER_PATTERN.fullmatch(run_attempt):
        raise PublicationPreparationError("github.run_attempt must be a positive integer")
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise PublicationPreparationError("github.repository is not a safe owner/repository value")
    if server_url != "https://github.com":
        raise PublicationPreparationError("Only the trusted https://github.com server is supported")

    branch = (
        "automation/documentation-"
        f"{ticket['issue_key'].lower()}-{run_id}-{run_attempt}"
    )
    title = build_pull_request_title(ticket["issue_key"], ticket["issue_summary"])
    commit_message = f"{ticket['issue_key']} Apply validated documentation proposal"
    actions_url = f"{server_url}/{repository}/actions/runs/{run_id}"
    validated_documents = validation.get("documents")
    if not isinstance(validated_documents, list) or len(validated_documents) != len(documents):
        raise PublicationPreparationError(
            "validation-result.json documents must describe every changed file"
        )
    publication_documents: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in validated_documents:
        if not isinstance(item, dict) or set(item) != {
            "path", "reason", "evidence", "previous_version", "proposed_version"
        }:
            raise PublicationPreparationError("Invalid validated document metadata")
        document = item["path"]
        if not isinstance(document, str) or document in seen or document not in documents:
            raise PublicationPreparationError("Validated document metadata paths do not match")
        seen.add(document)
        previous_version, proposed_version = document_versions(root, base_sha, document)
        if item["previous_version"] != previous_version or item["proposed_version"] != proposed_version:
            raise PublicationPreparationError("Validated document versions do not match Git")
        if not isinstance(item["reason"], str) or not isinstance(item["evidence"], str):
            raise PublicationPreparationError("Validated document explanation is invalid")
        publication_documents.append(
            {
                "path": document,
                "reason": item["reason"],
                "evidence": item["evidence"],
                "previous_version": previous_version,
                "proposed_version": proposed_version,
            }
        )
    report = read_agent_report(agent_report)
    if report.get("decision") != "proposal":
        raise PublicationPreparationError("Agent report decision does not match publication")
    report_documents = report.get("documents")
    if not isinstance(report_documents, list) or [
        item.get("path") if isinstance(item, dict) else None for item in report_documents
    ] != [item["path"] for item in publication_documents]:
        raise PublicationPreparationError("Agent report documents do not match validation")
    body = build_pull_request_body(ticket, report, actions_url)
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(body, encoding="utf-8", newline="\n")
    return {
        "publish": "true",
        "decision": "proposal",
        "branch": branch,
        "documents_json": json.dumps(
            publication_documents, ensure_ascii=False, separators=(",", ":")
        ),
        "commit_message": commit_message,
        "pr_title": title,
        "pr_body": str(body_file),
    }


def write_github_outputs(path: Path, values: Mapping[str, str]) -> None:
    for name, value in values.items():
        if not re.fullmatch(r"[a-z_]+", name) or "\n" in value or "\r" in value:
            raise PublicationPreparationError("Unsafe GitHub Actions output value")
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for name, value in values.items():
            output.write(f"{name}={value}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--validation-result", type=Path, required=True)
    parser.add_argument("--ticket-file", type=Path, required=True)
    parser.add_argument("--agent-report", type=Path, required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--server-url", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        values = prepare_publication(
            repo_root=args.repo_root,
            validation_result=args.validation_result,
            ticket_file=args.ticket_file,
            agent_report=args.agent_report,
            body_file=args.body_file,
            base_sha=args.base_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            repository=args.repository,
            server_url=args.server_url,
        )
        write_github_outputs(args.github_output, values)
    except (PublicationPreparationError, OSError) as error:
        sys.stderr.write(f"Pull request publication preparation failed: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
