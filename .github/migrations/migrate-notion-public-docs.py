#!/usr/bin/env python3
"""Validate and deterministically migrate the approved public Notion export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import textwrap
import unicodedata
import urllib.parse
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


EXPECTED_MARKDOWN = 32
EXPECTED_CSV = 2
EXPECTED_ASIDES = 11
EXPECTED_INTERNAL_DESTINATIONS = 24
LAST_REVIEWED = "2026-09-09"
DESTINATION_ROOT = PurePosixPath("docs/centro-de-ayuda")
MANIFEST_PATH = PurePosixPath(
    ".github/migrations/notion-public-docs-manifest.json"
)
UUID_PATTERN = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])")
H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
LINK_PATTERN = re.compile(
    r"(?P<image>!)?\[(?P<label>[^\]]*)\]\((?P<target>[^)\r\n]+)\)"
)
ASIDE_PATTERN = re.compile(
    r"<aside(?:\s[^>]*)?>(?P<content>.*?)</aside\s*>",
    re.IGNORECASE | re.DOTALL,
)
HTML_PATTERN = re.compile(r"</?[A-Za-z][^>]*>")
CREATED_PATTERN = re.compile(r"^Creado:\s*(.+?)\s*$", re.MULTILINE)
PRIVATE_PATTERN = re.compile(
    r"\b(?:private|privado|privada|confidential|confidencial|internal only|no publicar)\b",
    re.IGNORECASE,
)
DRAFT_TITLE_PATTERN = re.compile(r"\b(?:draft|borrador)\b", re.IGNORECASE)

CATEGORY_CONTRACT = {
    "293b7527ac25808ab603de04e37fd7fa": (
        "Cuenta y facturación",
        "cuenta-y-facturacion",
    ),
    "29cb7527ac2580569616cb6ff64994c5": (
        "Inicio y acceso",
        "inicio-y-acceso",
    ),
    "33db7527ac258099913de0a2f8d411ce": (
        "Visibilidad",
        "visibilidad",
    ),
    "365b7527ac25801cb0adc4c3062368a8": (
        "Reputación",
        "reputacion",
    ),
    "365b7527ac258063b166cc696e9e1d76": (
        "Fidelización",
        "fidelizacion",
    ),
    "365b7527ac2580dca322c8bf8ab512e5": (
        "Analítica",
        "analitica",
    ),
    "365b7527ac2580c08c26eccd945f3ef5": (
        "Beelma",
        "beelma",
    ),
    "36eb7527ac25804da424db2e85074be7": (
        "Conexión Perfil de Empresa en Google",
        "perfil-de-empresa-en-google",
    ),
}

CATEGORY_SIDEBAR_POSITIONS = {
    "29cb7527ac2580569616cb6ff64994c5": 1,
    "36eb7527ac25804da424db2e85074be7": 2,
    "33db7527ac258099913de0a2f8d411ce": 3,
    "365b7527ac25801cb0adc4c3062368a8": 4,
    "365b7527ac258063b166cc696e9e1d76": 5,
    "365b7527ac2580c08c26eccd945f3ef5": 6,
    "365b7527ac2580dca322c8bf8ab512e5": 7,
    "293b7527ac25808ab603de04e37fd7fa": 8,
}

REVIEW_FINDINGS = (
    {
        "notion_id": "365b7527ac25803181f0e9eb44032e79",
        "kind": "possible_source_wording_error",
        "detail": (
            "The source says 'analiza automáticamente ... y obtener información'. "
            "It is preserved for human review."
        ),
    },
    {
        "notion_id": "365b7527ac2580efbfabed7d6303bd08",
        "kind": "possible_functional_inconsistency",
        "detail": (
            "The web statistics article describes Perfil de Google statistics in "
            "its introduction. It is preserved for human review."
        ),
    },
)


class MigrationError(ValueError):
    """Raised when the source export or generated migration is unsafe."""


@dataclass(frozen=True)
class Page:
    notion_id: str
    title: str
    source_name: str
    content: str
    created: str | None
    category_id: str
    destination: PurePosixPath
    is_category: bool

    @property
    def article_id(self) -> str:
        return f"NOTION-{self.notion_id.upper()}"


@dataclass(frozen=True)
class MigrationPlan:
    generated_files: Mapping[PurePosixPath, str]
    manifest: str


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).encode("ascii", errors="ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if not slug:
        raise MigrationError(f"Title cannot produce a stable slug: {title!r}")
    return slug


def validate_member(member: zipfile.ZipInfo) -> None:
    name = member.filename
    if "\\" in name:
        raise MigrationError(f"ZIP member uses unsafe path separators: {name!r}")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or re.match(r"^[A-Za-z]:", name)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise MigrationError(f"ZIP member has an unsafe path: {name!r}")
    mode = (member.external_attr >> 16) & 0xFFFF
    if stat.S_ISLNK(mode):
        raise MigrationError(f"ZIP member is a symlink: {name!r}")


def decode_utf8(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    payload = archive.read(member)
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise MigrationError(
            f"ZIP member is not valid UTF-8: {member.filename!r}"
        ) from error


def notion_id_from_name(name: str) -> str:
    matches = UUID_PATTERN.findall(PurePosixPath(name).stem)
    if len(matches) != 1:
        raise MigrationError(
            f"Markdown filename must contain exactly one Notion UUID: {name!r}"
        )
    return matches[0].lower()


def first_h1(content: str, source_name: str) -> str:
    match = H1_PATTERN.search(content)
    if match is None:
        raise MigrationError(f"Markdown page has no H1: {source_name!r}")
    title = match.group(1).strip()
    if UUID_PATTERN.search(title):
        raise MigrationError(f"Visible H1 contains a Notion UUID: {source_name!r}")
    return title


def parse_csv_exports(
    archive: zipfile.ZipFile,
    members: Sequence[zipfile.ZipInfo],
) -> tuple[set[str], dict[str, str]]:
    simple_names: set[str] | None = None
    detailed: dict[str, str] | None = None
    for member in members:
        rows = list(csv.DictReader(io.StringIO(decode_utf8(archive, member))))
        headers = set(rows[0]) if rows else set()
        if headers == {"Nombre"}:
            simple_names = {row["Nombre"] for row in rows}
        elif headers == {"Nombre", "Creado", "Etiquetas"}:
            if any(row["Etiquetas"].strip() for row in rows):
                raise MigrationError(
                    "The detailed CSV contains tagged/private/draft candidates"
                )
            detailed = {row["Nombre"]: row["Creado"] for row in rows}
        else:
            raise MigrationError(
                f"Unexpected CSV schema in {member.filename!r}: {sorted(headers)!r}"
            )
    if simple_names is None or detailed is None:
        raise MigrationError("Both expected Notion CSV metadata views are required")
    if simple_names != set(detailed):
        raise MigrationError("The two CSV exports disagree on category records")
    if len(simple_names) != len(CATEGORY_CONTRACT):
        raise MigrationError("CSV exports do not contain exactly eight categories")
    return simple_names, detailed


def extract_internal_target(target: str) -> str | None:
    if re.match(r"^(?:https?|mailto|tel):", target, re.IGNORECASE):
        return None
    if target.startswith("#"):
        return None
    decoded = urllib.parse.unquote(target)
    match = UUID_PATTERN.search(decoded)
    if match is None:
        raise MigrationError(f"Internal link has no Notion UUID: {target!r}")
    return match.group(1).lower()


def convert_asides(content: str) -> str:
    def replace(match: re.Match[str]) -> str:
        inner = textwrap.dedent(match.group("content")).strip("\r\n")
        return f":::note\n{inner}\n:::"

    return ASIDE_PATTERN.sub(replace, content)


def normalize_markdown(content: str) -> str:
    """Remove export-only trailing whitespace without rewriting visible content."""
    return "\n".join(line.rstrip() for line in content.splitlines())


def remove_created_property(content: str, expected: str | None) -> str:
    matches = CREATED_PATTERN.findall(content)
    if expected is None:
        if matches:
            raise MigrationError("Unexpected Creado property outside a category page")
        return content
    if matches != [expected]:
        raise MigrationError(
            f"Markdown Creado property does not match CSV metadata: {matches!r}"
        )
    return re.sub(
        r"(?m)^Creado:\s*[^\r\n]+\r?\n(?:\r?\n)?",
        "",
        content,
        count=1,
    )


def rewrite_links(
    content: str,
    source: PurePosixPath,
    destinations: Mapping[str, PurePosixPath],
) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group("image"):
            raise MigrationError("Images are not allowed in this public export")
        target = match.group("target")
        target_id = extract_internal_target(target)
        if target_id is None:
            return match.group(0)
        if target_id not in destinations:
            raise MigrationError(f"Internal link target is missing: {target_id}")
        _, marker, fragment = target.partition("#")
        relative = posixpath.relpath(
            destinations[target_id].as_posix(),
            source.parent.as_posix(),
        )
        rewritten = relative + (f"#{fragment}" if marker else "")
        return f"[{match.group('label')}]({rewritten})"

    return LINK_PATTERN.sub(replace, content)


def render_frontmatter(page: Page) -> str:
    title = json.dumps(page.title, ensure_ascii=False)
    sidebar_position = (
        f"sidebar_position: {CATEGORY_SIDEBAR_POSITIONS[page.notion_id]}\n"
        if page.is_category
        else ""
    )
    return (
        "---\n"
        f"article_id: {page.article_id}\n"
        f"title: {title}\n"
        "version: 1.0\n"
        "status: published\n"
        "owner: Product\n"
        f"last_reviewed: {LAST_REVIEWED}\n"
        f"notion_id: {page.notion_id}\n"
        f"{sidebar_position}"
        "---\n\n"
    )


def inspect_and_plan(archive_path: Path) -> MigrationPlan:
    try:
        archive_bytes = archive_path.read_bytes()
    except OSError as error:
        raise MigrationError(f"Could not read source ZIP: {error}") from error
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as error:
        raise MigrationError("Source is not a valid ZIP archive") from error

    with archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise MigrationError(f"ZIP integrity check failed at {corrupt!r}")
        for member in archive.infolist():
            validate_member(member)
        files = [member for member in archive.infolist() if not member.is_dir()]
        markdown = [m for m in files if PurePosixPath(m.filename).suffix.lower() == ".md"]
        csv_members = [m for m in files if PurePosixPath(m.filename).suffix.lower() == ".csv"]
        unexpected = [
            m.filename
            for m in files
            if PurePosixPath(m.filename).suffix.lower() not in {".md", ".csv"}
        ]
        if unexpected:
            raise MigrationError(f"Unexpected public export files: {unexpected!r}")
        if len(markdown) != EXPECTED_MARKDOWN or len(csv_members) != EXPECTED_CSV:
            raise MigrationError(
                f"Expected 32 Markdown and 2 CSV files; found {len(markdown)} and {len(csv_members)}"
            )

        csv_names, creation_by_title = parse_csv_exports(archive, csv_members)
        source_pages: dict[str, tuple[str, str, str | None]] = {}
        source_name_by_id: dict[str, str] = {}
        aside_count = 0
        internal_targets: set[str] = set()
        category_links: dict[str, list[str]] = {}

        for member in markdown:
            content = decode_utf8(archive, member)
            notion_id = notion_id_from_name(member.filename)
            if notion_id in source_pages:
                raise MigrationError(f"Duplicate Notion UUID: {notion_id}")
            title = first_h1(content, member.filename)
            if PRIVATE_PATTERN.search(title) or DRAFT_TITLE_PATTERN.search(title):
                raise MigrationError(f"Private or draft page title detected: {title!r}")
            if re.search(
                r"(?im)^(?:estado|status|visibilidad):\s*(?:draft|borrador|private|privado|confidencial)\s*$",
                content,
            ):
                raise MigrationError(f"Private or draft page property detected: {title!r}")
            opened = len(re.findall(r"<aside(?:\s[^>]*)?>", content, re.IGNORECASE))
            closed = len(re.findall(r"</aside\s*>", content, re.IGNORECASE))
            if opened != closed:
                raise MigrationError(f"Unbalanced aside in {member.filename!r}")
            aside_count += opened
            without_asides = ASIDE_PATTERN.sub("", content)
            if HTML_PATTERN.search(without_asides):
                raise MigrationError(f"Unexpected HTML in {member.filename!r}")
            created_matches = CREATED_PATTERN.findall(content)
            created = created_matches[0] if created_matches else None
            if len(created_matches) > 1:
                raise MigrationError(f"Duplicate Creado property in {member.filename!r}")
            source_pages[notion_id] = (title, content, created)
            source_name_by_id[notion_id] = member.filename

        if aside_count != EXPECTED_ASIDES:
            raise MigrationError(
                f"Expected {EXPECTED_ASIDES} asides; found {aside_count}"
            )
        category_ids = {
            notion_id
            for notion_id, (title, _, _) in source_pages.items()
            if title in csv_names
        }
        if category_ids != set(CATEGORY_CONTRACT):
            raise MigrationError("Category pages do not match the approved UUID contract")
        for notion_id, (expected_title, _) in CATEGORY_CONTRACT.items():
            if source_pages[notion_id][0] != expected_title:
                raise MigrationError(f"Category title mismatch for {notion_id}")

        for notion_id, (_, content, _) in source_pages.items():
            targets: list[str] = []
            for match in LINK_PATTERN.finditer(content):
                if match.group("image"):
                    raise MigrationError("The export unexpectedly contains an image")
                target_id = extract_internal_target(match.group("target"))
                if target_id is None:
                    continue
                if target_id not in source_pages:
                    raise MigrationError(f"Missing internal destination: {target_id}")
                internal_targets.add(target_id)
                targets.append(target_id)
            if notion_id in category_ids:
                category_links[notion_id] = targets

        if len(internal_targets) != EXPECTED_INTERNAL_DESTINATIONS:
            raise MigrationError(
                f"Expected 24 unique linked destinations; found {len(internal_targets)}"
            )
        article_ids = set(source_pages) - category_ids
        assigned = [target for targets in category_links.values() for target in targets]
        if set(assigned) != article_ids or len(assigned) != len(set(assigned)):
            raise MigrationError(
                "Category pages must assign each of the 24 articles exactly once"
            )

        category_for_article = {
            article_id: category_id
            for category_id, targets in category_links.items()
            for article_id in targets
        }
        pages: dict[str, Page] = {}
        destinations: dict[str, PurePosixPath] = {}
        for notion_id in sorted(source_pages):
            title, content, created = source_pages[notion_id]
            is_category = notion_id in category_ids
            category_id = notion_id if is_category else category_for_article[notion_id]
            folder = CATEGORY_CONTRACT[category_id][1]
            destination = DESTINATION_ROOT / folder / (
                "index.md" if is_category else f"{slugify(title)}.md"
            )
            if destination in destinations.values():
                raise MigrationError(f"Destination collision: {destination}")
            destinations[notion_id] = destination
            pages[notion_id] = Page(
                notion_id=notion_id,
                title=title,
                source_name=source_name_by_id[notion_id],
                content=content,
                created=created,
                category_id=category_id,
                destination=destination,
                is_category=is_category,
            )

        generated: dict[PurePosixPath, str] = {}
        for notion_id in sorted(pages):
            page = pages[notion_id]
            expected_created = creation_by_title[page.title] if page.is_category else None
            body = remove_created_property(page.content, expected_created)
            body = rewrite_links(body, page.destination, destinations)
            body = convert_asides(body)
            body = normalize_markdown(body)
            if UUID_PATTERN.search("\n".join(
                match.group("target") for match in LINK_PATTERN.finditer(body)
            )):
                raise MigrationError(f"Rewritten links retain a UUID in {page.title!r}")
            generated[page.destination] = render_frontmatter(page) + body.rstrip() + "\n"

        categories_manifest = []
        for category_id, (title, folder) in CATEGORY_CONTRACT.items():
            category = pages[category_id]
            articles = [pages[target] for target in category_links[category_id]]
            categories_manifest.append(
                {
                    "article_id": category.article_id,
                    "created": creation_by_title[title],
                    "notion_id": category_id,
                    "path": category.destination.as_posix(),
                    "title": title,
                    "articles": [
                        {
                            "article_id": article.article_id,
                            "notion_id": article.notion_id,
                            "path": article.destination.as_posix(),
                            "title": article.title,
                        }
                        for article in articles
                    ],
                }
            )
        manifest_value = {
            "schema_version": 1,
            "migration": "notion-public-docs",
            "source": {
                "archive": archive_path.name,
                "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                "markdown_pages": len(markdown),
                "csv_files": len(csv_members),
                "categories": len(category_ids),
                "articles": len(article_ids),
                "unique_internal_destinations": len(internal_targets),
                "asides": aside_count,
                "images": 0,
                "videos": 0,
                "attachments": 0,
            },
            "frontmatter": {
                "version": "1.0",
                "status": "published",
                "owner": "Product",
                "last_reviewed": LAST_REVIEWED,
                "article_id_derivation": "NOTION- + uppercase 32-character Notion UUID",
            },
            "categories": categories_manifest,
            "review_findings": list(REVIEW_FINDINGS),
        }
        manifest = json.dumps(
            manifest_value,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        return MigrationPlan(generated_files=generated, manifest=manifest)


def repository_path(root: Path, relative: PurePosixPath) -> Path:
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as error:
        raise MigrationError(f"Destination escapes repository: {relative}") from error
    return candidate


def apply_plan(root: Path, plan: MigrationPlan) -> None:
    destination_root = repository_path(root, DESTINATION_ROOT)
    manifest = repository_path(root, MANIFEST_PATH)
    if destination_root.exists() or manifest.exists():
        raise MigrationError("Migration destinations already exist; use --check")
    written: list[Path] = []
    try:
        for relative, content in sorted(
            plan.generated_files.items(), key=lambda item: item[0].as_posix()
        ):
            destination = repository_path(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
            written.append(destination)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(plan.manifest, encoding="utf-8", newline="\n")
        written.append(manifest)
    except OSError:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        if destination_root.exists():
            shutil.rmtree(destination_root)
        raise


def check_plan(root: Path, plan: MigrationPlan) -> None:
    destination_root = repository_path(root, DESTINATION_ROOT)
    manifest = repository_path(root, MANIFEST_PATH)
    expected = {relative.as_posix() for relative in plan.generated_files}
    actual = {
        path.relative_to(root).as_posix()
        for path in destination_root.rglob("*")
        if path.is_file()
    } if destination_root.is_dir() else set()
    if actual != expected:
        raise MigrationError(
            f"Migrated file set differs: missing={sorted(expected-actual)!r}, extra={sorted(actual-expected)!r}"
        )
    for relative, expected_content in plan.generated_files.items():
        path = repository_path(root, relative)
        if path.is_symlink() or path.read_text(encoding="utf-8") != expected_content:
            raise MigrationError(f"Migrated content differs: {relative}")
    if manifest.read_text(encoding="utf-8") != plan.manifest:
        raise MigrationError("Migration manifest differs from the deterministic plan")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.repo_root.resolve(strict=True)
        plan = inspect_and_plan(args.archive.resolve(strict=True))
        if args.check:
            check_plan(root, plan)
            sys.stdout.write("Notion public documentation migration is deterministic and complete.\n")
        else:
            apply_plan(root, plan)
            sys.stdout.write(
                f"Migrated {len(plan.generated_files)} Markdown pages and wrote the manifest.\n"
            )
    except (MigrationError, OSError, zipfile.BadZipFile) as error:
        sys.stderr.write(f"Notion migration failed: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
