#!/usr/bin/env python3
"""Find an existing documentation PR and notify Slack after a new PR is confirmed."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlsplit


ISSUE_KEY_PATTERN = re.compile(
    r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[1-9][0-9]*"
)
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+")
GENERIC_SEND_WARNING = (
    "::warning title=Slack notification failed::The pull request was created, "
    "but Slack could not be notified."
)
MISSING_WEBHOOK_WARNING = (
    "::warning title=Slack notification skipped::"
    "SLACK_DOCUMENTATION_WEBHOOK_URL is not configured."
)


class SlackNotificationError(ValueError):
    """Raised when notification input or delivery is invalid."""


Transport = Callable[[urllib.request.Request, float], int]


def validate_single_line(value: str, label: str, max_length: int = 500) -> str:
    if (
        not value
        or len(value) > max_length
        or "\n" in value
        or "\r" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise SlackNotificationError(f"Invalid {label}")
    return value


def validate_pr_url(value: str, repository: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        raise SlackNotificationError("Invalid pull request URL") from None
    expected_path = re.compile(rf"/{re.escape(repository)}/pull/[1-9][0-9]*")
    if (
        parts.scheme != "https"
        or parts.hostname != "github.com"
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or not expected_path.fullmatch(parts.path)
    ):
        raise SlackNotificationError("Invalid pull request URL")
    return value


def find_existing_pull_request(
    candidates: object,
    branch: str,
    issue_key: str,
    repository: str,
) -> str | None:
    """Return one open PR for the exact branch, or otherwise for the Jira key."""
    validate_single_line(branch, "branch")
    if not ISSUE_KEY_PATTERN.fullmatch(issue_key):
        raise SlackNotificationError("Invalid Jira key")
    if not isinstance(candidates, list):
        raise SlackNotificationError("Invalid GitHub pull request response")

    branch_matches: set[str] = set()
    ticket_matches: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise SlackNotificationError("Invalid GitHub pull request response")
        title = candidate.get("title")
        head = candidate.get("headRefName")
        url = candidate.get("url")
        if not all(isinstance(value, str) for value in (title, head, url)):
            raise SlackNotificationError("Invalid GitHub pull request response")
        safe_url = validate_pr_url(url, repository)
        if head == branch:
            branch_matches.add(safe_url)
        elif title.startswith(f"{issue_key} "):
            ticket_matches.add(safe_url)

    matches = branch_matches or ticket_matches
    if len(matches) > 1:
        raise SlackNotificationError("Several open pull requests match the branch or ticket")
    return next(iter(matches)) if matches else None


def should_notify(decision: str, pr_created: bool, pr_url: str | None) -> bool:
    """Keep the workflow gate explicit and independently testable."""
    return decision == "proposal" and pr_created and bool(pr_url)


def escape_slack_text(value: str) -> str:
    """Escape Slack's control characters without altering Unicode or quotes."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(
    issue_key: str,
    issue_summary: str,
    document: str,
    previous_version: str,
    proposed_version: str,
    pr_url: str,
) -> str:
    if not ISSUE_KEY_PATTERN.fullmatch(issue_key):
        raise SlackNotificationError("Invalid Jira key")
    validate_single_line(issue_summary, "ticket summary")
    validate_single_line(document, "document")
    if not VERSION_PATTERN.fullmatch(previous_version):
        raise SlackNotificationError("Invalid previous version")
    if not VERSION_PATTERN.fullmatch(proposed_version):
        raise SlackNotificationError("Invalid proposed version")
    if not pr_url.startswith("https://github.com/"):
        raise SlackNotificationError("Invalid pull request URL")
    return (
        ":books: *Nueva propuesta documental pendiente de aprobación*\n\n"
        f"*Ticket:* {issue_key}\n"
        f"*Resumen:* {escape_slack_text(issue_summary)}\n"
        f"*Documento:* `{escape_slack_text(document)}`\n"
        f"*Versión:* {previous_version} → {proposed_version}\n\n"
        f"*Revisar pull request:* {pr_url}\n"
        "La propuesta requiere aprobación humana antes de publicarse."
    )


def build_payload(**message_fields: str) -> bytes:
    return json.dumps(
        {"text": build_message(**message_fields)},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def default_transport(request: urllib.request.Request, timeout: float) -> int:
    opener = urllib.request.build_opener(NoRedirectHandler)
    with opener.open(request, timeout=timeout) as response:
        return response.getcode()


def send_notification(
    webhook_url: str,
    payload: bytes,
    *,
    timeout: float = 15.0,
    transport: Transport = default_transport,
) -> None:
    try:
        parts = urlsplit(webhook_url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
        ):
            raise SlackNotificationError("Slack notification failed")
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        status = transport(request, timeout)
    except (
        ValueError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
    ):
        raise SlackNotificationError("Slack notification failed") from None
    if not 200 <= status < 300:
        raise SlackNotificationError("Slack notification failed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    find_pr = subparsers.add_parser("find-pr")
    find_pr.add_argument("--candidates-file", type=Path, required=True, nargs="+")
    find_pr.add_argument("--branch", required=True)
    find_pr.add_argument("--issue-key", required=True)
    find_pr.add_argument("--repository", required=True)

    send = subparsers.add_parser("send")
    send.add_argument("--issue-key", required=True)
    send.add_argument("--issue-summary", required=True)
    send.add_argument("--document", required=True)
    send.add_argument("--previous-version", required=True)
    send.add_argument("--proposed-version", required=True)
    send.add_argument("--pr-url", required=True)
    send.add_argument("--timeout", type=float, default=15.0)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: Transport = default_transport,
) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "find-pr":
        try:
            candidates: list[object] = []
            for path in args.candidates_file:
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, list):
                    raise SlackNotificationError("Invalid GitHub pull request response")
                candidates.extend(value)
            url = find_existing_pull_request(
                candidates, args.branch, args.issue_key, args.repository
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, SlackNotificationError):
            sys.stderr.write("Could not safely inspect existing pull requests\n")
            return 1
        if url:
            sys.stdout.write(url + "\n")
        return 0

    webhook_url = os.environ.get("SLACK_DOCUMENTATION_WEBHOOK_URL", "")
    if not webhook_url:
        sys.stderr.write(MISSING_WEBHOOK_WARNING + "\n")
        return 0
    try:
        payload = build_payload(
            issue_key=args.issue_key,
            issue_summary=args.issue_summary,
            document=args.document,
            previous_version=args.previous_version,
            proposed_version=args.proposed_version,
            pr_url=args.pr_url,
        )
        send_notification(
            webhook_url, payload, timeout=args.timeout, transport=transport
        )
    except SlackNotificationError:
        sys.stderr.write(GENERIC_SEND_WARNING + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
