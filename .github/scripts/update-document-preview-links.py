"""Reconcile only preview slots using the existing Cloudflare Pages bot comment.

Never executes PR code. The route manifest is data fetched from the immutable
deployment URL, with a full commit SHA supplied by Cloudflare at build time.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, urlopen

BOT_ID = 73139402
APP_ID = 85455
MANIFEST = "document-preview-routes.json"


class PreviewError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def safe_diagnostic(error: Exception) -> str:
    """Only controlled messages: never stringify transport errors or responses."""
    if isinstance(error, PreviewError):
        return f"{error.code}: {error}"
    if isinstance(error, HTTPError):
        if 300 <= error.code < 400:
            return f"redirect_rejected: redirección rechazada (HTTP {error.code})"
        return f"http_error: HTTP {error.code}"
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout: tiempo de espera agotado"
    if isinstance(error, URLError):
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return "timeout: tiempo de espera agotado"
        return "connection_error: error de conexión"
    if isinstance(error, OSError):
        return "connection_error: error de conexión"
    if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
        return "invalid_json: JSON inválido"
    return "unexpected_error: error no clasificado"


def report(outcome: str, detail: str, changed: bool = False):
    labels = {
        "updated": "Enlaces actualizados; manifiesto verificado",
        "unchanged": "Enlaces vigentes sin cambios; manifiesto verificado",
        "pending": "Enlaces pendientes; preview sin verificar",
        "unverified": "Preview no verificable",
        "skipped": "Actualización omitida; preview sin verificar",
    }
    print(f"Preview: {labels[outcome]}. {detail}")
    if outcome in {"pending", "unverified"}:
        print(f"::warning title=Preview sin verificar::{detail}")
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as summary:
            summary.write(
                f"## Preview documental\n\n**Resultado:** {labels[outcome]}.\n\n"
                f"{detail}\n\n"
                f"**Descripción de la PR modificada:** {'sí' if changed else 'no'}.\n\n"
                "El verde del job indica que el proceso terminó; por sí solo no "
                "acredita una preview verificada.\n\n"
            )
    if path := os.environ.get("GITHUB_OUTPUT"):
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(f"preview_status={outcome}\nbody_changed={'true' if changed else 'false'}\n")


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
    if not isinstance(manifest, dict) or type(manifest.get("schema")) is not int or manifest["schema"] != 1:
        raise PreviewError("incompatible_manifest", "esquema de manifiesto incompatible")
    if manifest.get("commit") != sha:
        raise PreviewError("sha_mismatch", "el manifiesto no corresponde al último commit de la PR")
    base = manifest.get("baseUrl")
    if not isinstance(base, str) or not base.startswith("/") or not base.endswith("/"):
        raise PreviewError("incompatible_manifest", "baseUrl inválida en el manifiesto")
    routes = manifest.get("routes")
    if not isinstance(routes, dict):
        raise PreviewError("incompatible_manifest", "rutas ausentes en el manifiesto")
    for source, route in routes.items():
        if (not isinstance(source, str) or not isinstance(route, str)
                or not route.startswith(base) or route.startswith("//")
                or any(char in route for char in "\r\n<>\\#?")):
            raise PreviewError("incompatible_manifest", "ruta inválida en el manifiesto")
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
        raise PreviewError("redirect_rejected", f"redirección rechazada (HTTP {code})")


def fetch_manifest(url: str) -> dict:
    if not re.fullmatch(r"https://[0-9a-f]{8}\.[a-z0-9-]+\.pages\.dev", url):
        raise PreviewError("invalid_preview_url", "URL de despliegue no permitida")
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"GH_TOKEN", "GITHUB_TOKEN"}}
    try:
        # Before 8.4, --max-filesize could rely only on Content-Length. Fail
        # closed on older curl: the 2 MB cap must also cover chunked responses.
        version = subprocess.run(["curl", "-q", "--version"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, timeout=5, env=environment,
                                 shell=False, check=False)
        match = re.match(rb"curl (\d+)\.(\d+)\.(\d+)\b", version.stdout)
        if version.returncode or not match or tuple(map(int, match.groups())) < (8, 4, 0):
            raise PreviewError("transport_error", "se requiere curl 8.4.0 o posterior")
        # No curlrc/netrc, credentials, cookies, redirects, retries or UA override.
        # curl enforces the cap DURING transfer; captured stdout is bounded body
        # plus a fixed four-byte status suffix, never printed to logs.
        result = subprocess.run(
            ["curl", "-q", "--silent", "--no-netrc", "--proto", "=https",
             "--max-redirs", "0", "--retry", "0", "--connect-timeout", "10",
             "--max-time", "20", "--max-filesize", "2000000",
             "--output", "-", "--write-out", "\n%{http_code}", url + "/" + MANIFEST],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=25,
            env=environment, shell=False, check=False)
    except subprocess.TimeoutExpired:
        raise PreviewError("timeout", "tiempo de espera agotado") from None
    except OSError:
        raise PreviewError("transport_error", "no se pudo ejecutar curl") from None
    if result.returncode == 63:
        raise PreviewError("incompatible_manifest", "manifiesto demasiado grande")
    if result.returncode == 28:
        raise PreviewError("timeout", "tiempo de espera agotado")
    if result.returncode:
        raise PreviewError("connection_error", f"curl terminó con código {result.returncode}")
    if not re.fullmatch(rb"\n[1-5][0-9]{2}", result.stdout[-4:]):
        raise PreviewError("http_error", "curl no devolvió un estado HTTP válido")
    status = int(result.stdout[-3:])
    if 300 <= status < 400:
        raise PreviewError("redirect_rejected", f"redirección rechazada (HTTP {status})")
    if status != 200:
        raise PreviewError("http_error", f"HTTP {status}")
    raw = result.stdout[:-4]
    if len(raw) > 2_000_000:
        raise PreviewError("incompatible_manifest", "manifiesto demasiado grande")
    return json.loads(raw)


def update(api, number: int):
    pr = api.request(f"/pulls/{number}")
    repo = os.environ["GITHUB_REPOSITORY"]
    if (pr["state"] != "open" or pr["head"]["repo"]["full_name"] != repo
            or not pr["head"]["ref"].startswith("automation/documentation-")
            or pr["user"]["login"] != "github-actions[bot]"):
        report("skipped", "PR fuera del ámbito del agente documental.")
        return
    sha, body = pr["head"]["sha"], pr.get("body") or ""
    state, url = cloudflare_preview(api.comments(number), sha)
    manifest = None
    outcome = "pending" if state.startswith("pendiente") else "unverified"
    detail = state
    if url:
        try:
            manifest = fetch_manifest(url)
            validated_routes(manifest, sha)
            sources = re.findall(r"^- Ruta: `(docs/[^`\r\n]+\.mdx?)`\s*$", body, re.M)
            missing = sum(source not in manifest["routes"] for source in sources)
            outcome = "unverified" if missing or not sources else "updated"
            detail = (f"Manifiesto del último commit verificado; {missing} documentos sin ruta publicada."
                      if missing else "Manifiesto del último commit verificado."
                      if sources else "Manifiesto verificado; no se identificaron documentos para enlazar.")
        except Exception as error:
            detail = safe_diagnostic(error)
            print(f"Preview no verificable: {detail}")
            outcome = "unverified"
            state, url = f"no verificable: {detail}", None
    result = reconcile(body, sha, state, url, manifest)
    # Re-read before PATCH: discard stale runs and concurrent human body edits.
    current = api.request(f"/pulls/{number}")
    if current["head"]["sha"] != sha or current.get("body") != pr.get("body") or current["state"] != "open":
        report("skipped", "PR modificada durante la ejecución; se omite la escritura.")
        return
    if result != body:
        api.request(f"/pulls/{number}", {"body": result})
    elif outcome == "updated":
        outcome = "unchanged"
    report(outcome, detail, changed=result != body)


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
    try:
        main()
    except Exception as error:
        # Also avoid leaking GitHub HTTP headers or exception payloads in a traceback.
        report("unverified", "El proceso no pudo completarse: " + safe_diagnostic(error))
        raise SystemExit(1) from None
