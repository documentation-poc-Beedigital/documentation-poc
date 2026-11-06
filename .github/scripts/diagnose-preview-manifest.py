"""Read-only, fixed-target diagnosis. Never prints response bodies or raw headers."""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
from html import escape
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import build_opener

SCRIPT = Path(__file__).with_name("update-document-preview-links.py")
SPEC = importlib.util.spec_from_file_location("preview_updater_diagnostics", SCRIPT)
UPDATER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATER)

URL = "https://fdbe23fb.documentation-poc.pages.dev/document-preview-routes.json"
DEPLOYMENT = URL.rsplit("/", 1)[0]
HEADERS = ("Content-Type", "Server", "cf-ray", "cf-mitigated")


def allowed_headers(headers) -> dict[str, str]:
    # Filter before rendering. Control characters, excessive length and Markdown
    # table delimiters cannot inject extra log lines or summary content.
    return {name: re.sub(r"[^\x20-\x7e]", " ", str(headers.get(name, "")))[:256]
            for name in HEADERS}


def python_probe() -> dict:
    class DiagnosticNoRedirect(UPDATER.NoRedirect):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            self.status, self.headers = code, allowed_headers(headers)
            try:
                return super().redirect_request(req, fp, code, msg, headers, newurl)
            finally:
                fp.close()

    handler = DiagnosticNoRedirect()
    try:
        # Original urllib client retained for the read-only comparison. Production
        # fetch_manifest now uses curl. No token, cookies or credentials.
        with build_opener(handler).open(URL, timeout=20) as response:
            return {"status": response.status, "headers": allowed_headers(response.headers),
                    "result": "http_response"}
    except HTTPError as error:
        try:
            return {"status": error.code, "headers": allowed_headers(error.headers),
                    "result": "redirect_rejected" if 300 <= error.code < 400 else "http_error"}
        finally:
            error.close()
    except UPDATER.PreviewError:
        return {"status": getattr(handler, "status", None),
                "headers": getattr(handler, "headers", allowed_headers({})), "result": "redirect_rejected"}
    except Exception as error:
        return {"status": None, "headers": allowed_headers({}),
                "result": UPDATER.safe_diagnostic(error).split(":", 1)[0]}


def curl_probe() -> dict:
    # -q must be first: disable .curlrc; no netrc, cookie jar, credentials,
    # verbose logs or redirects. Discard every body, including error bodies.
    command = ["curl", "-q", "--silent", "--no-netrc", "--proto", "=https",
               "--request", "GET", "--connect-timeout", "10", "--max-time", "20",
               "--max-redirs", "0", "--dump-header", "-", "--output", os.devnull,
               "--write-out", "\n__HTTP_STATUS__:%{http_code}\n", URL]
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"GH_TOKEN", "GITHUB_TOKEN"}}
    empty = {"status": None, "headers": allowed_headers({})}
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 timeout=25, env=environment, check=False)
    except subprocess.TimeoutExpired:
        return {**empty, "result": "timeout"}
    except OSError:
        return {**empty, "result": "connection_error"}
    if process.returncode:
        return {**empty, "result": "timeout" if process.returncode == 28 else "connection_error"}
    # Raw headers stay in memory only. Select the final response, excluding
    # proxy CONNECT/informational responses, and then apply the allowlist.
    raw = process.stdout.decode("iso-8859-1")
    status = re.search(r"\n__HTTP_STATUS__:(\d{3})\s*$", raw)
    if not status or status[1] == "000":
        return {**empty, "result": "connection_error"}
    code = int(status[1])
    blocks = re.split(r"(?m)^HTTP/[^\r\n]*\r?\n", raw[:status.start()])
    headers = {}
    for line in blocks[-1].splitlines():
        key, separator, value = line.partition(":")
        if separator and key.lower() in {name.lower() for name in HEADERS}:
            headers[key.lower()] = value.strip()
    return {"status": code, "headers": allowed_headers({name: headers.get(name.lower(), "") for name in HEADERS}),
            "result": "redirect_rejected" if 300 <= code < 400 else "http_error" if code >= 400 else "http_response"}


def emit(text: str):
    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as summary:
            summary.write(text + "\n\n")


def verify_pr(api):
    pr = api.request("/pulls/121")
    sha = pr["head"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid head SHA")
    state, deployment = UPDATER.cloudflare_preview(api.comments(121), sha)
    matches = deployment == DEPLOYMENT
    emit(f"## Correspondencia con PR #121\n\nHead consultado: `{sha}`.\n\n"
         + ("La URL fija coincide con Preview URL anunciada por la app Cloudflare para este head."
            if matches else "La URL fija no se ha podido confirmar como preview del head actual. " + state)
         + "\n\nEsta comprobación compara metadatos de GitHub; no valida el contenido del manifiesto.")
    if not matches:
        print("::warning::La URL diagnosticada no está confirmada para el head actual de PR #121.")
    return matches


def compare(python: dict, curl: dict):
    def cell(value):
        return escape(str(value)).replace("|", "&#124;").replace("`", "&#96;") if value is not None else "sin respuesta"

    rows = ["## GET del manifiesto sin credenciales", f"\nURL fija: {URL}\n",
            "| Dato | Python urllib | curl |", "| --- | --- | --- |",
            f"| HTTP | {cell(python['status'])} | {cell(curl['status'])} |",
            f"| Resultado | {cell(python['result'])} | {cell(curl['result'])} |"]
    for name in HEADERS:
        rows.append(f"| {name} | {cell(python['headers'][name]) or 'ausente'} | {cell(curl['headers'][name]) or 'ausente'} |")
    rows.append("\nNo se siguen redirecciones ni se registran cuerpos o cabeceras fuera de la lista permitida. "
                "Un HTTP 200 no valida el SHA ni el contenido del manifiesto. "
                "El éxito de este job solo indica que terminó la comparación.")
    emit("\n".join(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify-pr", "probe"))
    mode = parser.parse_args().mode
    if mode == "verify-pr":
        verify_pr(UPDATER.GitHub())
    else:
        compare(python_probe(), curl_probe())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        emit("Diagnóstico no completado: " + UPDATER.safe_diagnostic(error))
        raise SystemExit(1) from None
