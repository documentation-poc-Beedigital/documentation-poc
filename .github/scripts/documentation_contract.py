"""Offline, shared checks for editorial metadata and mechanically visible losses."""
import json
import math
import re
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence
from urllib.parse import urlsplit

DESTINATIONS = json.loads((Path(__file__).parent.parent / "documentation-destinations.json").read_text(encoding="utf-8"))
MARK = re.compile(r"\[VERIFICAR\]\s+(V-\d+)\b")
URL = re.compile(r"https?://[^\s<>\[\]()\"']+")


def position(frontmatter: str, item: Mapping[str, object]) -> str:
    """Only an explicit per-document position may supplement Python frontmatter."""
    if "sidebar_position" not in item:
        return frontmatter
    value = item["sidebar_position"]
    path = PurePosixPath(str(item["path"]))
    if (len(path.parts) != 4 or path.parts[:2] != ("docs", "centro-de-ayuda")
            or path.name == "index.md" or isinstance(value, bool)
            or not isinstance(value, (int, float)) or not 1 < value <= 10000
            or not math.isfinite(value)):
        raise ValueError("Invalid sidebar_position: only Help Center articles, finite number > 1 and <= 10000")
    lines = frontmatter.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if re.match(r"^\s*sidebar_position\s*:", line)]
    if len(indices) > 1:
        raise ValueError("Duplicate sidebar_position")
    if indices:
        lines[indices[0]] = f"sidebar_position: {value}\n"
    else:
        lines.insert(-1, f"sidebar_position: {value}\n")
    return "".join(lines)


def check_content(before: str, after: str, item: Mapping[str, object]) -> None:
    explanation = str(item["reason"]) + " " + str(item["evidence"])
    old, new = MARK.findall(before), MARK.findall(after)
    for identifier in set(old) | set(new):
        if new.count(identifier) < old.count(identifier):
            # This is an auditable declaration, not proof that the claim was resolved.
            if not re.search(rf"\b{re.escape(identifier)}\s+(?:omitido|resuelto):\s*\S.+", explanation):
                raise ValueError(f"Removed uncertainty {identifier} requires 'omitido: motivo' or 'resuelto: evidencia'")
        elif identifier not in old and not re.search(rf"\b{re.escape(identifier)}\b", explanation):
            raise ValueError(f"Pending {identifier} must be explained in reason or evidence")
    allowed = {entry["url"] for entry in DESTINATIONS}
    for url in set(URL.findall(after)) - set(URL.findall(before)):
        host = (urlsplit(url).hostname or "").lower()
        if host == "beesible.ai" or host.endswith(".beesible.ai"):
            if url not in allowed:
                raise ValueError("Unverified Beesible destination: " + url)


def check_navigation(root: Path, items: Sequence[Mapping[str, object]]) -> None:
    ordered = [item for item in items if "sidebar_position" in item]
    if not ordered:
        return
    if len(ordered) > 5 or len({str(PurePosixPath(str(item["path"])).parent) for item in ordered}) != 1:
        raise ValueError("Navigation changes are limited to five articles in one category")
    for item in ordered:
        position("---\n---\n", item)
    values = [item["sidebar_position"] for item in ordered]
    if len(values) != len(set(values)):
        raise ValueError("Duplicate proposed sidebar_position")
    category = root / str(PurePosixPath(str(ordered[0]["path"])).parent)
    changed = {item["path"] for item in ordered}
    for sibling in category.iterdir():
        if sibling.suffix not in {".md", ".mdx"} or not sibling.is_file() or sibling.is_symlink() or sibling.relative_to(root).as_posix() in changed:
            continue
        text = sibling.read_text(encoding="utf-8").split("---", 2)
        match = re.search(r"^sidebar_position:\s*([0-9.]+)\s*$", text[1] if len(text) > 2 else "", re.M)
        if match and float(match[1]) in values:
            raise ValueError("sidebar_position collides with an unchanged article")
