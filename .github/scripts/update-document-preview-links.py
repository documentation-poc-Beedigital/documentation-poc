"""Reconcile only preview slots using the existing Cloudflare Pages bot comment.

Never executes PR code. The route manifest is data fetched from the immutable
deployment URL, with a full commit SHA supplied by Cloudflare at build time.
"""
from __future__ import annotations

import json
import os
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

BOT_ID = 73139402
APP_ID = 85455
MANIFEST = "document-preview-routes.json"


def slot(key: str, value: str) -> str:
    return f"<!-- document-preview:{key}:start -->\n{value}\n<!-- document-preview:{key}:end -->"


def cloudflare_preview(comments: list[dict], sha: str) -> tuple[str, str | None]:
    trusted = [c for c in comments if c.get("user", {}).get("id") == BOT_ID
               and c.get("performed_via_github_app", {}).get("id") == APP_ID]
    if not trusted:
        return "pendiente del despliegue del último commit", None
    comment = max(trusted, key=lambda c: (c.get("updated_at", ""), c["id"]))
    body = comment.get("body", "")
    rows = dict(re.findall(
        r"<tr><td><strong>([^<]+):</strong>\s*</td><td>(.*?)</td></tr>", body, re.S))
    commit = re.fullmatch(r"\s*<code>([0-9a-f]{7,40})</code>\s*", rows.get("Latest commit", ""))
    if not commit or not sha.startswith(commit[1]):
        return "pendiente: Cloudflare aún comunica otro commit o un formato desconocido", None
    status = unescape(re.sub(r"<[^>]+>", "", rows.get("Status", ""))).strip()
    if "Deploy successful!" not in status:
        if re.search(r"fail|error|cancel", status, re.I):
            return "despliegue fallido o cancelado para el último commit", None
        return "pendiente del despliegue del último commit", None
    link = re.search(r"<a href=['\"]([^'\"]+)['\"]", rows.get("Preview URL", ""))
    url = unescape(link[1]) if link else ""
    parsed = urlsplit(url)
    # Accept only the immutable Pages URL actually supplied by the trusted app,
    # never Branch Preview URL, dashboard links, credentials or arbitrary hosts.
    if (parsed.scheme != "https" or parsed.port or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or not re.fullmatch(r"[0-9a-f]{8}\.[a-z0-9-]+\.pages\.dev", parsed.netloc)):
        return "URL de despliegue no reconocida; revisar el comentario de Cloudflare", None
    return "disponible", url.rstrip("/")


def validated_routes(manifest: dict, sha: str) -> tuple[str, dict[str, str]]:
    if manifest.get("schema") != 1 or manifest.get("commit") != sha:
        raise ValueError("El manifiesto no corresponde al último commit de la PR")
    base = manifest.get("baseUrl")
    if not isinstance(base, str) or not base.startswith("/") or not base.endswith("/"):
        raise ValueError("baseUrl inválida en el manifiesto")
    routes = manifest.get("routes")
    if not isinstance(routes, dict):
        raise ValueError("Rutas ausentes en el manifiesto")
    for source, route in routes.items():
        if (not isinstance(source, str) or not isinstance(route, str)
                or not route.startswith(base) or route.startswith("//")
                or any(char in route for char in "\r\n<>\\#?")):
            raise ValueError("Ruta inválida en el manifiesto")
    return base, routes


def reconcile(body: str, sha: str, state: str, url: str | None = None,
              manifest: dict | None = None) -> str:
    base, routes = validated_routes(manifest, sha) if url and manifest else ("/", {})
    # Existing descriptions can be adopted without regenerating their editorial
    # metadata. Only insert new managed slots, leaving every original byte intact.
    sections = re.split(r"(?=^### )", body, flags=re.M)
    for index, section in enumerate(sections):
        match = re.search(r"^- Ruta: `(docs/[^`\r\n]+\.mdx?)`\s*$", section, re.M)
        if not match:
            continue
        source = match[1]
        value = (f"[Ver en preview](<{url}{routes[source]}>)" if url and source in routes
                 else f"Ver en preview: {state if not url else 'ruta no publicada en este despliegue'}. (commit `{sha}`)")
        key = source
        start, end = f"<!-- document-preview:{key}:start -->", f"<!-- document-preview:{key}:end -->"
        if start in section or end in section:
            if section.count(start) != 1 or section.count(end) != 1:
                raise ValueError("Bloque preview ambiguo")
            section, count = re.subn(re.escape(start) + r".*?" + re.escape(end),
                                     lambda _: slot(key, value), section, flags=re.S)
            if count != 1:
                raise ValueError("Bloque preview mal formado")
        else:
            # Immediately below the document path; do not claim human prose.
            section = section[:match.end()] + "\n\n" + slot(key, value) + "\n" + section[match.end():]
        sections[index] = section
    body = "".join(sections)
    value = (f"[Ver preview general](<{url}{base}>) — commit `{sha}`" if url
             else f"Preview general: {state}. (commit `{sha}`)")
    start, end = "<!-- document-preview:general:start -->", "<!-- document-preview:general:end -->"
    if start in body or end in body:
        if body.count(start) != 1 or body.count(end) != 1:
            raise ValueError("Bloque preview general ambiguo")
        body, count = re.subn(re.escape(start) + r".*?" + re.escape(end),
                             lambda _: slot("general", value), body, flags=re.S)
        if count != 1:
            raise ValueError("Bloque preview general mal formado")
    else:
        body += "\n\n" + slot("general", value) + "\n"
    return body


class GitHub:
    def __init__(self):
        self.root = "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"]

    def request(self, path: str, data=None):
        request = Request(self.root + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                                   "Accept": "application/vnd.github+json"},
                          method="PATCH" if data is not None else "GET")
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def comments(self, number):
        result = []
        for page in range(1, 11):
            batch = self.request(f"/issues/{number}/comments?per_page=100&page={page}")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise ValueError("Demasiados comentarios; no se puede determinar el último despliegue")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_manifest(url: str) -> dict:
    # Do not forward a GitHub token to Cloudflare or follow redirects to an alias.
    with build_opener(NoRedirect).open(url + "/" + MANIFEST, timeout=20) as response:
        if response.geturl() != url + "/" + MANIFEST:
            raise ValueError("El manifiesto redirige a otro destino")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Manifiesto demasiado grande")
        return json.loads(raw)


def update(api, number: int):
    pr = api.request(f"/pulls/{number}")
    repo = os.environ["GITHUB_REPOSITORY"]
    if (pr["state"] != "open" or pr["head"]["repo"]["full_name"] != repo
            or not pr["head"]["ref"].startswith("automation/documentation-")
            or pr["user"]["login"] != "github-actions[bot]"):
        return
    sha, body = pr["head"]["sha"], pr.get("body") or ""
    state, url = cloudflare_preview(api.comments(number), sha)
    manifest = None
    if url:
        try:
            manifest = fetch_manifest(url)
            validated_routes(manifest, sha)
        except Exception as error:
            print(f"Preview no verificable: {type(error).__name__}")
            state, url = "pendiente: no se pudo verificar el manifiesto del último commit", None
    result = reconcile(body, sha, state, url, manifest)
    # Re-read before PATCH: discard stale runs and concurrent human body edits.
    current = api.request(f"/pulls/{number}")
    if current["head"]["sha"] != sha or current.get("body") != pr.get("body") or current["state"] != "open":
        print("PR modificada durante la ejecución; se omite la escritura")
        return
    if result != body:
        api.request(f"/pulls/{number}", {"body": result})


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    if "comment" in event:
        comment = event["comment"]
        if (comment.get("user", {}).get("id") != BOT_ID
                or comment.get("performed_via_github_app", {}).get("id") != APP_ID
                or "pull_request" not in event["issue"]):
            return
        number = event["issue"]["number"]
    else:
        number = event.get("number") or event.get("inputs", {}).get("pr_number")
    if not number or not str(number).isdigit():
        raise ValueError("Número de PR inválido")
    update(GitHub(), int(number))


if __name__ == "__main__":
    main()
