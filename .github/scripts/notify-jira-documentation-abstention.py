#!/usr/bin/env python3
"""Prepare and send a Jira notification for a validated abstention."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.parse import urlsplit


ISSUE_KEY_PATTERN = re.compile(
    r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[1-9][0-9]*"
)
POSITIVE_INTEGER_PATTERN = re.compile(r"[1-9][0-9]*")
REPOSITORY_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
)
REPORT_FIELDS = {"decision", "summary", "reason", "evidence", "documents"}
MAX_AGENT_REPORT_BYTES = 16_384
MAX_REASON_CHARACTERS = 1_000
GENERIC_SEND_ERROR = "Jira abstention notification failed"


class JiraNotificationError(ValueError):
    """Raised when a Jira abstention notification is unsafe or unsuccessful."""


Transport = Callable[[urllib.request.Request, float], int]


def load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JiraNotificationError(f"Could not read {label}") from error
    if not isinstance(value, dict):
        raise JiraNotificationError(f"{label} must contain a JSON object")
    return value


def validate_issue_key(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 3 <= len(value) <= 64
        or not ISSUE_KEY_PATTERN.fullmatch(value)
    ):
        raise JiraNotificationError("issue_key is not a validated Jira-style key")
    return value


def load_ticket_issue_key(path: Path, expected_issue_key: str) -> str:
    expected = validate_issue_key(expected_issue_key)
    ticket = load_json_object(path, "ticket JSON")
    if set(ticket) != {"issue_key", "issue_summary", "issue_description"}:
        raise JiraNotificationError("Ticket JSON has an unexpected structure")
    issue_key = validate_issue_key(ticket.get("issue_key"))
    if issue_key != expected:
        raise JiraNotificationError("Ticket issue_key does not match the validated input")
    return issue_key


def parse_agent_report(path: Path) -> dict[str, object]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise JiraNotificationError("Could not read the validated agent report") from error
    if len(payload) > MAX_AGENT_REPORT_BYTES:
        raise JiraNotificationError("Agent report exceeds the validated size limit")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JiraNotificationError("Agent report is not valid UTF-8 JSON") from error
    if not isinstance(value, dict) or set(value) != REPORT_FIELDS:
        raise JiraNotificationError("Agent report does not match the validated format")
    return value


def validate_reason(value: object) -> str:
    if not isinstance(value, str):
        raise JiraNotificationError("Abstention reason must be a string")
    reason = value.strip()
    if not reason:
        raise JiraNotificationError("Abstention reason must not be empty")
    if "\n" in reason or "\r" in reason:
        raise JiraNotificationError("Abstention reason must be a single line")
    if len(reason) > MAX_REASON_CHARACTERS:
        raise JiraNotificationError("Abstention reason exceeds 1000 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in reason):
        raise JiraNotificationError("Abstention reason contains a control character")
    return reason


def build_actions_url(server_url: str, repository: str, run_id: str) -> str:
    if server_url != "https://github.com":
        raise JiraNotificationError("Only the trusted GitHub server is supported")
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise JiraNotificationError("github.repository is not a safe owner/repository value")
    if not POSITIVE_INTEGER_PATTERN.fullmatch(run_id):
        raise JiraNotificationError("github.run_id must be a positive integer")
    return f"{server_url}/{repository}/actions/runs/{run_id}"


def prepare_notification(
    validation_result: Path,
    ticket_file: Path,
    agent_report: Path,
    payload_file: Path,
    expected_issue_key: str,
    server_url: str,
    repository: str,
    run_id: str,
) -> dict[str, str]:
    validation = load_json_object(validation_result, "validation result")
    if validation.get("valid") is not True:
        return {"notify": "false", "decision": "rejected"}

    decision = validation.get("decision")
    if decision == "proposal":
        return {"notify": "false", "decision": "proposal"}
    if decision != "abstention":
        return {"notify": "false", "decision": "rejected"}
    if validation.get("changed_files") != []:
        raise JiraNotificationError("A valid abstention must have no changed files")

    issue_key = load_ticket_issue_key(ticket_file, expected_issue_key)
    report = parse_agent_report(agent_report)
    if report["decision"] != "abstention" or report["documents"] != []:
        raise JiraNotificationError("Agent report decision is not an abstention")
    reason = validate_reason(report["reason"])
    actions_url = build_actions_url(server_url, repository, run_id)
    payload = {
        "issue_key": issue_key,
        "decision": "abstention",
        "reason": reason,
        "actions_url": actions_url,
    }
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"notify": "true", "decision": "abstention"}


def validate_webhook_url(value: str) -> None:
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
    except ValueError:
        raise JiraNotificationError(GENERIC_SEND_ERROR) from None
    if (
        parts.scheme != "https"
        or not hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise JiraNotificationError(GENERIC_SEND_ERROR)


def load_payload_bytes(path: Path) -> bytes:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JiraNotificationError(GENERIC_SEND_ERROR) from error
    if not isinstance(value, dict) or set(value) != {
        "issue_key",
        "decision",
        "reason",
        "actions_url",
    }:
        raise JiraNotificationError(GENERIC_SEND_ERROR)
    validate_issue_key(value.get("issue_key"))
    if value.get("decision") != "abstention":
        raise JiraNotificationError(GENERIC_SEND_ERROR)
    validate_reason(value.get("reason"))
    actions_url = value.get("actions_url")
    if not isinstance(actions_url, str) or not actions_url.startswith(
        "https://github.com/"
    ):
        raise JiraNotificationError(GENERIC_SEND_ERROR)
    return payload


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def default_transport(request: urllib.request.Request, timeout: float) -> int:
    opener = urllib.request.build_opener(NoRedirectHandler)
    with opener.open(request, timeout=timeout) as response:
        return response.getcode()


def send_notification(
    payload_file: Path,
    webhook_url: str,
    webhook_token: str,
    *,
    timeout: float = 30.0,
    transport: Transport = default_transport,
) -> None:
    try:
        if not webhook_url or not webhook_token:
            raise JiraNotificationError(GENERIC_SEND_ERROR)
        validate_webhook_url(webhook_url)
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in webhook_token
        ):
            raise JiraNotificationError(GENERIC_SEND_ERROR)
        payload = load_payload_bytes(payload_file)
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Automation-Webhook-Token": webhook_token,
            },
        )
        status = transport(request, timeout)
    except (
        JiraNotificationError,
        ValueError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
    ):
        raise JiraNotificationError(GENERIC_SEND_ERROR) from None
    if not 200 <= status < 300:
        raise JiraNotificationError(GENERIC_SEND_ERROR)


def write_github_outputs(path: Path, values: Mapping[str, str]) -> None:
    for name, value in values.items():
        if not re.fullmatch(r"[a-z_]+", name) or "\n" in value or "\r" in value:
            raise JiraNotificationError("Unsafe GitHub Actions output value")
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for name, value in values.items():
            output.write(f"{name}={value}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--validation-result", type=Path, required=True)
    prepare.add_argument("--ticket-file", type=Path, required=True)
    prepare.add_argument("--agent-report", type=Path, required=True)
    prepare.add_argument("--payload-file", type=Path, required=True)
    prepare.add_argument("--github-output", type=Path, required=True)
    prepare.add_argument("--expected-issue-key", required=True)
    prepare.add_argument("--server-url", required=True)
    prepare.add_argument("--repository", required=True)
    prepare.add_argument("--run-id", required=True)

    send = subparsers.add_parser("send")
    send.add_argument("--payload-file", type=Path, required=True)
    send.add_argument("--timeout", type=float, default=30.0)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: Transport = default_transport,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            values = prepare_notification(
                validation_result=args.validation_result,
                ticket_file=args.ticket_file,
                agent_report=args.agent_report,
                payload_file=args.payload_file,
                expected_issue_key=args.expected_issue_key,
                server_url=args.server_url,
                repository=args.repository,
                run_id=args.run_id,
            )
            write_github_outputs(args.github_output, values)
        else:
            send_notification(
                args.payload_file,
                os.environ.get("JIRA_AUTOMATION_WEBHOOK_URL", ""),
                os.environ.get("JIRA_AUTOMATION_WEBHOOK_TOKEN", ""),
                timeout=args.timeout,
                transport=transport,
            )
    except (JiraNotificationError, OSError):
        if args.command == "send":
            sys.stderr.write(GENERIC_SEND_ERROR + "\n")
        else:
            sys.stderr.write("Jira abstention notification preparation failed\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
