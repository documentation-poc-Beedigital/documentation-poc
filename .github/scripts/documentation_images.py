"""Strict Jira image selection, bounded download and deterministic asset validation."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

MAX_IMAGES = 10
MAX_IMAGE_BYTES = 2_000_000
MAX_BATCH_BYTES = 8_000_000
MAX_PIXELS = 20_000_000
KEY = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[1-9][0-9]*"
SELECTION_FIELDS = {"issue_key", "attachment_id", "description", "alt", "placement", "reason"}
IMAGE_FIELDS = SELECTION_FIELDS | {"id", "path", "url", "sha256", "size", "mime_type", "operation"}
ASSET_PATH = re.compile(r"static/img/jira/([a-z0-9-]+)-([1-9][0-9]*)-([0-9a-f]{64})\.(png|jpg)")


class ImageError(ValueError):
    pass


def text(value: object, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or len(value) > 2000 or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ImageError(f"Invalid image {label}")
    return value


def selection(description: str) -> list[dict]:
    description = description.replace("\r\n", "\n").replace("\r", "\n")
    marker = "documentation-images-v1"
    if marker not in description:
        return []
    # Longer ADF fences are accepted; the closing fence must match exactly.
    blocks = re.findall(r"(?m)^(`{3,})documentation-images-v1\n(.*?)\n\1[ \t]*$", description, re.S)
    if len(blocks) != 1 or description.count(marker) != 1:
        raise ImageError("Expected one fenced documentation-images-v1 JSON block")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ImageError("Duplicate image JSON field")
            result[key] = value
        return result
    try:
        value = json.loads(blocks[0][1], object_pairs_hook=unique)
    except (ValueError, TypeError) as error:
        raise ImageError("Invalid image selection JSON") from error
    if (not isinstance(value, dict) or set(value) != {"version", "images"}
            or type(value["version"]) is not int or value["version"] != 1
            or not isinstance(value["images"], list) or len(value["images"]) > MAX_IMAGES):
        raise ImageError("Invalid image selection schema/version")
    result = []
    for item in value["images"]:
        if not isinstance(item, dict) or set(item) != SELECTION_FIELDS:
            raise ImageError("Invalid selected image fields")
        parsed = {field: text(item[field], field) for field in SELECTION_FIELDS}
        if not re.fullmatch(KEY, parsed["issue_key"]) or not re.fullmatch(r"[1-9][0-9]*", parsed["attachment_id"]):
            raise ImageError("Invalid image issue key or attachment ID")
        if any(c in parsed["alt"] for c in "[]\\"):
            raise ImageError("Image alt must be plain text without Markdown delimiters")
        result.append(parsed)
    return result


def image_type(data: bytes) -> str:
    """Check container structure, dimensions and PNG checksum/compressed data."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ImageError("Image exceeds size limit or is empty")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        offset, chunks, compressed = 8, [], bytearray()
        while offset + 12 <= len(data):
            size = int.from_bytes(data[offset:offset + 4], "big")
            kind = data[offset + 4:offset + 8]
            end = offset + 12 + size
            if end > len(data):
                raise ImageError("Truncated PNG")
            payload = data[offset + 8:end - 4]
            if zlib.crc32(kind + payload) & 0xffffffff != int.from_bytes(data[end - 4:end], "big"):
                raise ImageError("Invalid PNG checksum")
            chunks.append(kind)
            if kind == b"IHDR":
                if len(chunks) != 1 or len(payload) != 13:
                    raise ImageError("Invalid PNG header")
                width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
                if (not width or not height or width * height > MAX_PIXELS or compression or filtering
                        or interlace not in (0, 1) or color not in (0, 2, 3, 4, 6)
                        or depth not in {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}[color]):
                    raise ImageError("Invalid PNG dimensions/encoding")
            if kind == b"IDAT":
                compressed.extend(payload)
            offset = end
            if kind == b"IEND":
                if payload or offset != len(data):
                    raise ImageError("Invalid PNG end")
                break
        if not chunks or chunks[0] != b"IHDR" or chunks[-1] != b"IEND" or not compressed:
            raise ImageError("Incomplete PNG")
        if color == 3 and b"PLTE" not in chunks:
            raise ImageError("Indexed PNG has no palette")
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        passes = [(width, height)]
        if interlace:
            passes = [(max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy))
                      for x, y, dx, dy in ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8),
                                           (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))]
        rows = [((w * channels * depth + 7) // 8 + 1, h) for w, h in passes if w and h]
        expected_size = sum(stride * count for stride, count in rows)
        try:
            decoder = zlib.decompressobj()
            decoded = decoder.decompress(bytes(compressed), expected_size + 1)
            if not decoder.eof or decoder.unused_data or len(decoded) != expected_size:
                raise ImageError("Invalid or excessive PNG pixel data")
            cursor = 0
            for stride, count in rows:
                if any(decoded[cursor + i * stride] > 4 for i in range(count)):
                    raise ImageError("Invalid PNG scanline filter")
                cursor += stride * count
        except zlib.error as error:
            raise ImageError("Invalid PNG pixel data") from error
        return "image/png"
    if data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"):
        offset, dimensions, scan = 2, False, False
        while offset < len(data) - 2:
            if data[offset] != 255:
                raise ImageError("Invalid JPEG marker")
            while offset < len(data) and data[offset] == 255:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if marker in (0, 0xd8, 0xd9):
                raise ImageError("Invalid JPEG structure")
            length = int.from_bytes(data[offset:offset + 2], "big")
            if length < 2 or offset + length > len(data) - 2:
                raise ImageError("Truncated JPEG")
            if marker in (0xc0, 0xc1, 0xc2):
                if length < 8:
                    raise ImageError("Invalid JPEG frame")
                height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
                if not width or not height or width * height > MAX_PIXELS:
                    raise ImageError("Invalid JPEG dimensions")
                dimensions = True
            offset += length
            if marker == 0xda:
                scan = offset < len(data) - 2
                break
        if dimensions and scan:
            return "image/jpeg"
    raise ImageError("Only structurally valid PNG and JPEG images are allowed")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_url(url: str):
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise ImageError("Unsafe Jira image download URL") from error
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or port not in (None, 443)
            or any(ord(c) <= 32 for c in url)):
        raise ImageError("Unsafe Jira image download URL")
    return parsed


def download(endpoint: str, base_url: str, email: str, token: str, timeout: float, *, opener=None) -> bytes:
    """Only Jira origin receives Basic auth; redirects allow one explicit Atlassian media host."""
    base = safe_url(base_url)
    open_request = opener or urllib.request.build_opener(NoRedirect()).open
    url = endpoint
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode("ascii")
    for hop in range(6):
        parsed = safe_url(url)
        same_origin = (parsed.hostname, parsed.port or 443) == (base.hostname, base.port or 443)
        if not same_origin and parsed.hostname != "api.media.atlassian.com":
            raise ImageError("Jira image redirect host is not authorized")
        # The content endpoint can negotiate an opaque binary representation.
        # Publication types are enforced against bytes and metadata in catalogue().
        headers = {"Accept": "*/*"}
        if same_origin:
            headers["Authorization"] = f"Basic {credentials}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with open_request(request, timeout=timeout) as response:
                data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ImageError("Downloaded image exceeds size limit")
            return data
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308):
                location = error.headers.get("Location")
                error.close()
                if not location:
                    raise ImageError("Jira image redirect has no location") from error
                url = urllib.parse.urljoin(url, location)
                continue
            error.close()
            raise ImageError(f"Jira image download returned HTTP {error.code}") from None
        except (OSError, urllib.error.URLError) as error:
            raise ImageError("Jira image download failed") from error
    raise ImageError("Too many Jira image redirects")


def asset_path(root: Path, raw: str) -> Path:
    if ASSET_PATH.fullmatch(raw) is None:
        raise ImageError("Invalid deterministic image path")
    candidate = root / raw
    cursor = root
    for part in raw.split("/"):
        cursor = cursor / part
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise ImageError("Image path contains a symlink")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ImageError("Image path escapes repository") from error
    return candidate


def catalogue(descriptions: list[str], issues: dict, configuration: tuple[str, str, str], timeout: float,
              downloader=download, *, selected: list[dict] | None = None) -> tuple[list[dict], dict[str, bytes]]:
    if selected is None:
        selected = [item for description in descriptions for item in selection(description)]
    if len(selected) > MAX_IMAGES:
        raise ImageError("Image batch exceeds count limit")
    seen, result, blobs, total = set(), [], {}, 0
    base, email, token = configuration
    for item in selected:
        key, identity = item["issue_key"], item["attachment_id"]
        image_id = f"{key}/{identity}"
        if image_id in seen:
            raise ImageError("Duplicate selected attachment identity")
        seen.add(image_id)
        if key not in issues:
            raise ImageError("Selected attachment issue is outside the authorized batch")
        attachments = issues[key].get("attachment", [])
        if not isinstance(attachments, list):
            raise ImageError("Invalid Jira attachment metadata")
        matches = [a for a in attachments if isinstance(a, dict) and a.get("id") == identity]
        if len(matches) != 1:
            raise ImageError("Selected attachment does not belong to its authorized issue")
        attachment = matches[0]
        size, mime = attachment.get("size"), attachment.get("mimeType")
        if type(size) is not int or not 0 < size <= MAX_IMAGE_BYTES or mime not in ("image/png", "image/jpeg"):
            raise ImageError("Invalid attachment type or size")
        total += size
        if total > MAX_BATCH_BYTES:
            raise ImageError("Image batch exceeds byte limit")
        # Construct from the validated real ID; never consume attachment.content or filename as a URL/path.
        data = downloader(f"{base}/rest/api/3/attachment/content/{identity}", base, email, token, timeout)
        if len(data) != size or image_type(data) != mime:
            raise ImageError("Downloaded image differs from Jira metadata")
        sha = hashlib.sha256(data).hexdigest()
        extension = "png" if mime == "image/png" else "jpg"
        path = f"static/img/jira/{key.lower()}-{identity}-{sha}.{extension}"
        result.append({**item, "id": image_id, "path": path, "url": "/" + path[len("static/"):],
                       "sha256": sha, "size": size, "mime_type": mime, "operation": "create"})
        blobs[path] = data
    return result, blobs


def validate_entries(images: object) -> list[dict]:
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise ImageError("Invalid image catalogue")
    seen, identities = set(), set()
    for image in images:
        if not isinstance(image, dict) or set(image) != IMAGE_FIELDS:
            raise ImageError("Invalid image catalogue fields")
        selection("```documentation-images-v1\n" + json.dumps({"version": 1, "images": [
            {f: image[f] for f in SELECTION_FIELDS}]}) + "\n```")
        match = ASSET_PATH.fullmatch(image["path"]) if isinstance(image["path"], str) else None
        if (not match or image["id"] != f"{image['issue_key']}/{image['attachment_id']}"
                or match.group(1) != image["issue_key"].lower() or match.group(2) != image["attachment_id"]
                or match.group(3) != image["sha256"] or image["url"] != "/" + image["path"][7:]
                or image["mime_type"] != ("image/png" if match.group(4) == "png" else "image/jpeg")
                or type(image["size"]) is not int or not 0 < image["size"] <= MAX_IMAGE_BYTES
                or image["operation"] not in ("create", "reuse") or image["path"] in seen
                or image["id"] in identities):
            raise ImageError("Invalid image identity/path/hash/size")
        seen.add(image["path"])
        identities.add(image["id"])
    if sum(image["size"] for image in images) > MAX_BATCH_BYTES:
        raise ImageError("Image batch exceeds byte limit")
    return images


def verify_file(root: Path, image: dict) -> None:
    candidate = asset_path(root, image["path"])
    if not candidate.is_file() or candidate.stat().st_size != image["size"]:
        raise ImageError("Image file is missing or has an invalid size")
    data = candidate.read_bytes()
    if hashlib.sha256(data).hexdigest() != image["sha256"] or image_type(data) != image["mime_type"]:
        raise ImageError("Image file type or hash does not match catalogue")


def references(body: str, images: list[dict], before: str = "") -> set[str]:
    """New images use a single auditable inline Markdown form; preserve existing image syntax."""
    allowed = {image["url"]: image for image in images}
    used = set()
    # Remove code examples so they cannot authorize publication of an unused binary.
    def prose(value):
        value = re.sub(r"(?ms)^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", "", value)
        value = re.sub(r"(?s)<!--.*?-->|\{/\*.*?\*/\}", "", value)
        return re.sub(r"(`+)[^\n]*?\1", "", value)
    body, before = prose(body), prose(before)
    for imported in re.findall(r"(?m)^\s*import\b[^\n]*", body):
        if imported not in before:
            raise ImageError("New MDX image imports are not supported")
    pattern = r"!\[[^\n]*?\](?:\([^\n]*?\)|\[[^\n]*?\])|(?is:<(?:img|Image)\b[^>]*>)"
    existing = re.findall(pattern, before)
    for raw in re.findall(pattern, body):
        match = re.fullmatch(r"!\[([^\[\]\\\n]+)\]\((/img/jira/[a-z0-9.-]+)\)", raw)
        if match and match.group(2) in allowed:
            image = allowed[match.group(2)]
            if match.group(1) != image["alt"]:
                raise ImageError("Image alt does not match approved selection")
            used.add(image["path"])
        elif raw not in existing:
            raise ImageError("New image reference is not an authorized catalogue image")
    # Reference-style images, dynamic MDX and disguised catalogue URLs are not supported in v1.
    remainder = re.sub(pattern, "", body)
    if "/img/jira/" in remainder or re.search(r"!\[|<img\b|<Image\b", remainder, re.I):
        raise ImageError("Unsupported or malformed image reference")
    return used
