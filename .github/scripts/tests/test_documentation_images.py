from __future__ import annotations

import copy
import base64
import hashlib
import importlib.util
import io
import json
import socket
import struct
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zlib
from contextlib import nullcontext
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import documentation_images as IMAGES


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = load("images_generator", "generate-documentation-proposal.py")
VALIDATOR = load("images_validator", "validate-documentation-proposal.py")
PREPARER = load("images_preparer", "prepare-documentation-pull-request.py")


def png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0")) + chunk(b"IEND", b""))


PNG = png()
# One red pixel encoded by Windows GDI+, kept inline to avoid image library dependencies.
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD50ooor8MP9Uz/2Q==")
CONFIG = {"base_url": "https://tenant.atlassian.net", "email": "test@example.invalid", "token": "test-only"}


def item(identity="11", key="APP-2"):
    return {"issue_key": key, "attachment_id": identity, "description": "Pantalla de acceso vigente",
            "alt": "Formulario de acceso", "placement": "Después del primer paso", "reason": "Localizar el botón"}


def block(items):
    return "```documentation-images-v1\n" + json.dumps({"version": 1, "images": items}) + "\n```"


class Response(io.BytesIO):
    pass


class ImageContractTests(unittest.TestCase):
    def test_binary_negotiation_and_406_are_safe(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request)
            # Simulate an endpoint which offers application/octet-stream.
            if request.get_header("Accept") != "*/*":
                raise urllib.error.HTTPError(request.full_url, 406, "Not acceptable", {}, io.BytesIO())
            return Response(PNG)
        self.assertEqual(PNG, IMAGES.download("https://tenant.atlassian.net/file", *CONFIG.values(), 30, opener=opener))
        error = urllib.error.HTTPError("https://api.media.atlassian.com/file?token=secret", 406,
                                      "secret", {}, io.BytesIO(b"private body"))
        with self.assertRaisesRegex(IMAGES.ImageError, "^Jira image download returned HTTP 406$"):
            IMAGES.download("https://tenant.atlassian.net/file", *CONFIG.values(), 30,
                            opener=mock.Mock(side_effect=error))
        self.assertTrue(error.fp.closed)

    def test_old_description_and_strict_json(self):
        self.assertEqual([], IMAGES.selection("Descripción histórica"))
        self.assertEqual([item()], IMAGES.selection(block([item()])))
        for bad in (block([dict(item(), url="https://evil.invalid")]), block([dict(item(), path="../x")]),
                    block([dict(item(), attachment_id=11)]), block([dict(item(), issue_key="app-2")]),
                    block([dict(item(), alt="")]), block([]).replace('"version": 1', '"version": true'),
                    block([]).replace('"version": 1', '"version": 1, "version": 1'),
                    block([]) + "\n" + block([]), block([]).replace("```", "")):
            with self.subTest(bad=bad), self.assertRaises(IMAGES.ImageError):
                IMAGES.selection(bad)

    def test_png_validation_rejects_spoof_and_corruption(self):
        self.assertEqual("image/png", IMAGES.image_type(PNG))
        for data in (b"<svg/>", b"<html/>", PNG[:-1], PNG + b"payload", PNG[:40] + b"x" + PNG[41:],
                     b"\xff\xd8not-a-jpeg\xff\xd9", b"x" * (IMAGES.MAX_IMAGE_BYTES + 1)):
            with self.subTest(size=len(data)), self.assertRaises(IMAGES.ImageError):
                IMAGES.image_type(data)

    def test_jpeg_actual_fixture(self):
        self.assertEqual("image/jpeg", IMAGES.image_type(JPEG))
        for data in (JPEG[:-1], JPEG[:20], JPEG[:2] + b"broken" + JPEG[-2:]):
            with self.assertRaises(IMAGES.ImageError):
                IMAGES.image_type(data)

    def test_redirect_auth_scope_and_relative_redirect(self):
        requests = []
        def opener(request, **kwargs):
            requests.append(request)
            if len(requests) == 1:
                raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "/download/11"}, io.BytesIO())
            if len(requests) == 2:
                raise urllib.error.HTTPError(request.full_url, 303, "redirect",
                    {"Location": "https://api.media.atlassian.com/file/signed?token=opaque"}, io.BytesIO())
            return Response(PNG)
        self.assertEqual(PNG, IMAGES.download("https://tenant.atlassian.net/rest/api/3/attachment/content/11",
            *CONFIG.values(), 30, opener=opener))
        self.assertTrue(requests[0].get_header("Authorization").startswith("Basic "))
        self.assertIsNotNone(requests[1].get_header("Authorization"))
        self.assertIsNone(requests[2].get_header("Authorization"))
        self.assertTrue(all(r.get_header("Accept") == "*/*" for r in requests))

    def test_rejected_redirects_timeouts_http_and_loops(self):
        for target in ("http://tenant.atlassian.net/file", "https://evil.invalid/file",
                       "https://api.media.atlassian.com.evil.invalid/file", "https://user:pass@tenant.atlassian.net/file",
                       "https://tenant.atlassian.net:444/file", "https://tenant.atlassian.net/file"):
            calls = []
            def opener(request, **kwargs):
                calls.append(request)
                raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": target}, io.BytesIO())
            with self.subTest(target=target), self.assertRaises(IMAGES.ImageError):
                IMAGES.download("https://tenant.atlassian.net/file", *CONFIG.values(), 30, opener=opener)
            self.assertTrue(all("tenant.atlassian.net" in r.full_url for r in calls))
        for error in (socket.timeout(), urllib.error.URLError("offline"),
                      urllib.error.HTTPError("https://tenant.atlassian.net/file", 404, "not found", {}, io.BytesIO())):
            with self.subTest(error=type(error)), self.assertRaises(IMAGES.ImageError):
                IMAGES.download("https://tenant.atlassian.net/file", *CONFIG.values(), 30,
                                opener=mock.Mock(side_effect=error))

    def test_download_size_bound(self):
        with self.assertRaises(IMAGES.ImageError):
            IMAGES.download("https://tenant.atlassian.net/file", *CONFIG.values(), 30,
                            opener=lambda *a, **k: Response(b"x" * (IMAGES.MAX_IMAGE_BYTES + 1)))

    def test_unsafe_paths(self):
        for path in ("../image.png", "/static/img/jira/x.png", "static/img/jira/../x.png", "static/img/jira/x.png"):
            with self.subTest(path=path), self.assertRaises(IMAGES.ImageError):
                IMAGES.asset_path(Path.cwd(), path)


class ImageWorkflowTests(unittest.TestCase):
    def prepare_crop(self):
        from test_documentation_crops import raster, crop_for
        data = raster()
        crop = crop_for(data)
        self.set_selection([{**item(), "crop": crop}])
        self.issues["APP-2"]["attachment"][0]["size"] = len(data)
        self.downloader = mock.Mock(return_value=data)
        return data, crop

    def test_crop_catalogue_markdown_artifacts_validation_and_pr(self):
        data, crop = self.prepare_crop()
        self.run_proposal()
        image = json.loads(self.report.read_text(encoding="utf-8"))["images"][0]
        self.assertEqual(crop, image["crop"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), image["original"]["sha256"])
        self.assertEqual((6, 3), (image["width"], image["height"]))
        derived = (self.root / image["path"]).read_bytes()
        self.assertNotEqual(data, derived)
        self.assertEqual(derived, (self.artifacts / "files" / image["path"]).read_bytes())
        self.assertIn(f"![{image['alt']}]({image['url']})", self.doc.read_text(encoding="utf-8"))
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        output = Path(self.temp.name) / "validation.json"
        output.write_text(json.dumps(validation), encoding="utf-8")
        body = Path(self.temp.name) / "pr.md"
        publication = PREPARER.prepare_publication(self.root, output, self.ticket, self.report, body,
            self.base, "123", "1", "example/repo", "https://github.com")
        self.assertIn(image["path"], json.loads(publication["files_json"]))
        self.assertIn(image["original"]["sha256"], body.read_text(encoding="utf-8"))
        self.assertIn("left=1, top=2, right=7, bottom=5", body.read_text(encoding="utf-8"))
        # Restore using only the recoverable artifact, then revalidate.
        (self.root / image["path"]).unlink()
        (self.root / image["path"]).write_bytes((self.artifacts / "files" / image["path"]).read_bytes())
        self.assertTrue(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_crop_failure_aborts_before_claude_and_without_publication(self):
        data, crop = self.prepare_crop()
        for changes in ({"original_sha256": "0" * 64}, {"original_width": 9}, {"original_height": 7},
                        {"left": True}, {"bottom": 99}):
            self.set_selection([{**item(), "crop": {**crop, **changes}}])
            with self.subTest(changes=changes), self.assertRaises(IMAGES.ImageError):
                self.run_proposal()
            self.assertEqual([], self.requests)
            self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
            self.assertFalse(self.artifacts.exists())
            self.assertFalse((self.root / "static").exists())

    def test_crop_application_failure_rolls_back(self):
        self.prepare_crop()
        with mock.patch.object(GENERATOR.os, "link", side_effect=OSError("Simulated failure")), \
             self.assertRaises(GENERATOR.ProposalError):
            self.run_proposal()
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "static").exists())

    def test_crop_diagnosis_matches_production_without_claude_or_publication(self):
        data, crop = self.prepare_crop()
        with mock.patch.object(GENERATOR, "http_transport", side_effect=AssertionError("Claude forbidden")), \
             mock.patch.object(GENERATOR, "apply_changes_atomically", side_effect=AssertionError("Apply forbidden")):
            diagnostic = GENERATOR.diagnose_images(self.root, self.ticket, self.base, CONFIG,
                jira_epic_key="APP-1", jira_task_keys="APP-2", jira_transport=self.jira,
                image_downloader=self.downloader)
        self.assertFalse(self.artifacts.exists())
        self.assertEqual("", self.git("status", "--porcelain"))
        self.run_proposal()
        image = json.loads(self.report.read_text(encoding="utf-8"))["images"][0]
        safe = diagnostic["images"][0]
        for field in ("sha256", "size", "width", "height", "original", "crop"):
            self.assertEqual(image[field], safe[field])
        self.assertEqual("valid", safe["validation"])
        for forbidden in (CONFIG["token"], CONFIG["base_url"], item()["description"], item()["reason"]):
            self.assertNotIn(forbidden, json.dumps(diagnostic))

    def test_post_claude_failure_cannot_retain_a_valid_abstention(self):
        generate = GENERATOR.generate_and_apply
        def simulated(*args, **kwargs):
            return generate(*args, **kwargs) if args else self.run_proposal(abstain=True)
        with mock.patch.object(GENERATOR, "generate_and_apply", side_effect=simulated), \
             mock.patch.object(GENERATOR, "apply_changes_atomically", side_effect=OSError("apply failed")), \
             mock.patch("sys.stderr", new_callable=io.StringIO):
            result = GENERATOR.main(["--repo-root", str(self.root), "--ticket-file", str(self.ticket),
                "--prompt-file", str(self.prompt), "--agent-report", str(self.report)])
        self.assertEqual(1, result)
        self.assertEqual(1, len(self.requests))
        self.assertEqual("technical_error", json.loads(self.report.read_text())["status"])
        self.assertFalse(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_cli_technical_failures_replace_even_an_existing_abstention(self):
        for error in (IMAGES.ImageError("Jira image download returned HTTP 406"),
                      GENERATOR.ProposalError("private context must not reach report"),
                      OSError("https://signed.invalid/?token=private")):
            with self.subTest(error=type(error).__name__):
                self.run_proposal(abstain=True)
                with mock.patch.object(GENERATOR, "generate_and_apply", side_effect=error), \
                     mock.patch("sys.stderr", new_callable=io.StringIO):
                    result = GENERATOR.main(["--repo-root", str(self.root), "--ticket-file", str(self.ticket),
                        "--prompt-file", str(self.prompt), "--agent-report", str(self.report)])
                self.assertEqual(1, result)
                report = json.loads(self.report.read_text(encoding="utf-8"))
                self.assertEqual("technical_error", report["status"])
                self.assertNotIn("decision", report)
                self.assertNotIn("private", json.dumps(report))
                self.assertFalse(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_diagnostic_cli_cannot_enter_generation_or_model_transport(self):
        diagnostic = Path(self.temp.name) / "safe.json"
        with mock.patch.object(GENERATOR, "diagnose_images", side_effect=IMAGES.ImageError("Jira image download returned HTTP 406")), \
             mock.patch.object(GENERATOR, "generate_and_apply", side_effect=AssertionError("Generation forbidden")), \
             mock.patch.object(GENERATOR, "http_transport", side_effect=AssertionError("Claude forbidden")), \
             mock.patch("sys.stderr", new_callable=io.StringIO):
            result = GENERATOR.main(["--ticket-file", str(self.ticket), "--diagnose-images",
                "--base-sha", self.base, "--diagnostic-report", str(diagnostic)])
        self.assertEqual(1, result)
        self.assertEqual({"status": "technical_error", "error_type": "ImageError", "http_status": 406},
                         json.loads(diagnostic.read_text()))
        self.assertFalse(self.report.exists())
        with mock.patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit):
            GENERATOR.main(["--ticket-file", str(self.ticket), "--diagnose-images", "--diagnose-jira-context"])

    def test_image_diagnostic_uses_canonical_incident_without_model_or_mutations(self):
        self.incident_fixture()
        before = self.git("status", "--porcelain")
        temp_paths = []
        temporary_directory = tempfile.TemporaryDirectory
        def temporary(*args, **kwargs):
            directory = temporary_directory(*args, **kwargs)
            temp_paths.append(Path(directory.name))
            return directory
        with mock.patch.object(GENERATOR, "http_transport", side_effect=AssertionError("Claude forbidden")), \
             mock.patch.object(GENERATOR, "generate_and_apply", side_effect=AssertionError("Generation forbidden")), \
             mock.patch.object(GENERATOR, "build_request", side_effect=AssertionError("Model request forbidden")), \
             mock.patch.object(GENERATOR, "apply_changes_atomically", side_effect=AssertionError("Apply forbidden")), \
             mock.patch.object(GENERATOR.tempfile, "TemporaryDirectory", side_effect=temporary):
            report = GENERATOR.diagnose_images(self.root, self.ticket, self.base, CONFIG,
                jira_transport=self.jira, image_downloader=self.downloader, **self.source_references)
        self.assertEqual(4, report["images_count"])
        self.assertEqual(8, len(self.jira_calls))
        self.assertEqual(4, len(self.downloads))
        for image in report["images"]:
            self.assertEqual({"issue_key", "attachment_id", "size", "mime_type", "sha256", "width", "height",
                              "original", "crop", "validation"}, set(image))
            self.assertEqual(hashlib.sha256(PNG).hexdigest(), image["sha256"])
        self.assertEqual(before, self.git("status", "--porcelain"))
        self.assertTrue(temp_paths)
        self.assertTrue(all(not p.exists() for p in temp_paths))
        self.assertFalse(self.report.exists())
        self.assertFalse(self.artifacts.exists())

    def test_image_diagnostic_rejects_invalid_content_and_406_before_claude(self):
        self.incident_fixture()
        for data in (b"<html>unauthorized</html>", b"<svg/>", PNG[:-1], JPEG):
            with self.subTest(data=data[:10]), self.assertRaises(IMAGES.ImageError):
                GENERATOR.diagnose_images(self.root, self.ticket, self.base, CONFIG,
                    jira_transport=self.jira, image_downloader=mock.Mock(return_value=data), **self.source_references)
        self.downloader = mock.Mock(side_effect=IMAGES.ImageError("Jira image download returned HTTP 406"))
        with self.assertRaisesRegex(IMAGES.ImageError, "HTTP 406"):
            self.run_proposal()
        self.assertEqual([], self.requests)
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.doc = self.root / "docs/centro-de-ayuda/cuenta/acceder.md"
        self.doc.parent.mkdir(parents=True)
        self.before = "---\narticle_id: TEST\ntitle: Acceder\nversion: 1.0\n---\n\n# Acceder\n\nPaso previo.\n"
        self.doc.write_text(self.before, encoding="utf-8", newline="")
        (self.doc.parent / "index.md").write_text(self.before.replace("Acceder", "Cuenta"), encoding="utf-8", newline="")
        self.git("add", "docs")
        self.git("commit", "--quiet", "-m", "Fixture base")
        self.base = self.git("rev-parse", "HEAD")
        self.ticket = Path(self.temp.name) / "ticket.json"
        self.prompt = Path(self.temp.name) / "prompt.md"
        self.prompt.write_text("Trusted prompt", encoding="utf-8")
        self.report = Path(self.temp.name) / "report.json"
        self.artifacts = Path(self.temp.name) / "artifacts"
        self.set_selection([item()])
        attachment = {"id": "11", "filename": "captura-001.png", "mimeType": "image/png", "size": len(PNG),
                      "content": "https://evil.invalid/ignored"}
        self.issues = {
            "APP-1": {"summary": "Contexto", "issuetype": {"name": "Epic"}, "description": None, "attachment": []},
            "APP-2": {"summary": "Acceso", "parent": {"key": "APP-1"}, "labels": ["documentation-required"],
                      "status": {"statusCategory": {"key": "done"}}, "description": None, "attachment": [attachment]},
        }
        self.downloads = []
        self.requests = []

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    def set_selection(self, selected):
        self.ticket.write_text(json.dumps({"issue_key": "DOC-1", "issue_summary": "Documentar acceso",
            "issue_description": "Contexto textual.\n" + block(selected)}), encoding="utf-8")

    def jira(self, endpoint, *args):
        self.assertIn("attachment", endpoint)
        key = endpoint.split("/issue/")[1].split("?")[0]
        if key == "DOC-1":
            return {"key": key, "fields": {"summary": "Solicitud actual",
                "description": {"type": "doc", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": json.loads(self.ticket.read_text(encoding="utf-8"))["issue_description"]}]}]}}}
        return {"key": key, "fields": self.issues[key]}

    def downloader(self, endpoint, *args):
        self.downloads.append(endpoint)
        self.assertTrue(endpoint.startswith("https://tenant.atlassian.net/rest/api/3/attachment/content/"))
        return PNG

    def run_proposal(self, body=None, abstain=False):
        def model(endpoint, key, payload, timeout):
            self.requests.append(payload)
            catalogue = json.loads(payload["messages"][0]["content"]).get("images", [])
            rendered = "\n# Acceder\n\n1. Abre el formulario.\n"
            if body is None:
                rendered += "\n".join(f"![{i['alt']}]({i['url']})" for i in catalogue) + "\n"
            else:
                rendered += body
            proposal = {"decision": "abstention" if abstain else "proposal", "summary": "Acceso", "reason": "Contexto",
                        "evidence": "APP-2", "documents": [] if abstain else [{"operation": "update",
                        "path": self.doc.relative_to(self.root).as_posix(), "title": "Acceder", "reason": "Contexto",
                        "evidence": "APP-2", "proposed_body": rendered}]}
            return {"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(proposal)}]}
        return GENERATOR.generate_and_apply(self.root, self.ticket, self.prompt, self.report, "test-only", model,
            base_sha=self.base, jira_configuration=CONFIG, jira_transport=self.jira,
            **getattr(self, "source_references", {"jira_epic_key": "APP-1", "jira_task_keys": "APP-2"}),
            image_downloader=self.downloader,
            image_artifacts=self.artifacts)

    def incident_fixture(self):
        """Synthetic equivalents only; no incident descriptions or downloaded assets."""
        selected = [dict(item(identity, "DOC-95"), alt=f"Vista aprobada {number}")
                    for number, identity in enumerate(("10109", "10110", "10111", "10117"), 1)]
        literal = json.dumps({"version": 1, "images": selected})
        automation = "Contexto Automation sin identificador.\n```\n" + literal + "\n```"
        self.ticket.write_text(json.dumps({"issue_key": "DOC-104", "issue_summary": "Solicitud sintética",
                                          "issue_description": automation}), encoding="utf-8")
        request_adf = {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Contexto canónico sintético."}]},
            {"type": "codeBlock", "attrs": {"language": "documentation-images-v1"},
             "content": [{"type": "text", "text": literal}]}]}
        self.issues = {
            "DOC-104": {"summary": "Solicitud API", "description": request_adf},
            "DOC-95": {"summary": "Épica sintética", "issuetype": {"name": "Epic"}, "description": None,
                       "attachment": [{"id": entry["attachment_id"], "size": len(PNG),
                                       "mimeType": "image/png", "filename": "fixture.png"} for entry in selected]},
            **{f"DOC-{n}": {"summary": f"Tarea sintética {n}", "parent": {"key": "DOC-95"},
                           "labels": ["documentation-required"], "status": {"statusCategory": {"key": "done"}},
                           "description": None, "attachment": []} for n in range(96, 102)},
        }
        self.source_references = {"jira_epic_key": "DOC-95",
                                  "jira_task_keys": ",".join(f"DOC-{n}" for n in range(96, 102))}
        self.jira_calls = []
        previous_jira = self.jira
        def jira(endpoint, *args):
            self.jira_calls.append(endpoint.split("/issue/")[1].split("?")[0])
            return previous_jira(endpoint, *args)
        self.jira = jira
        for target in ("urllib.request.urlopen", "socket.create_connection"):
            patcher = mock.patch(target, side_effect=AssertionError("Real network forbidden"))
            patcher.start()
            self.addCleanup(patcher.stop)
        return selected, automation

    def test_incident_four_images_in_captured_request_and_recoverable_proposal(self):
        selected, automation = self.incident_fixture()
        # Reproduces the pre-fix empty selection when the language marker is absent.
        self.assertEqual([], IMAGES.selection(automation))
        with mock.patch.object(IMAGES, "selection", wraps=IMAGES.selection) as extract, \
             mock.patch.object(GENERATOR, "convert_jira_description", wraps=GENERATOR.convert_jira_description) as convert:
            self.run_proposal()
        self.assertEqual(["DOC-104", "DOC-95", *[f"DOC-{n}" for n in range(96, 102)]], self.jira_calls)
        self.assertEqual(8, convert.call_count)
        # Eight source descriptions, then strict validation of the combined
        # selection before downloads (including callers supplying selected=).
        self.assertEqual(9, extract.call_count)
        payload = json.loads(self.requests[0]["messages"][0]["content"])
        self.assertEqual({"issue_key", "issue_summary", "issue_description"}, set(payload["ticket"]))
        context = payload["ticket"]["issue_description"]
        self.assertNotIn("Contexto Automation", context)
        self.assertEqual(1, context.count("Contexto canónico sintético."))
        self.assertEqual(1, context.count("documentation-images-v1"))
        self.assertEqual(1, context.count("Documentation task DOC-104:"))
        catalogue = payload["images"]
        self.assertEqual(4, len(catalogue))
        sha = hashlib.sha256(PNG).hexdigest()
        self.assertEqual([f"/img/jira/doc-95-{i['attachment_id']}-{sha}.png" for i in selected],
                         [i["url"] for i in catalogue])
        self.assertEqual([i["alt"] for i in selected], [i["alt"] for i in catalogue])
        self.assertEqual([f"{CONFIG['base_url']}/rest/api/3/attachment/content/{i['attachment_id']}" for i in selected],
                         self.downloads)
        artifacts = json.loads((self.artifacts / "catalogue.json").read_text(encoding="utf-8"))
        self.assertEqual(catalogue, artifacts["available"])
        self.assertEqual(catalogue, artifacts["published"])
        proposed = self.doc.read_text(encoding="utf-8")
        for image in catalogue:
            self.assertIn(f"![{image['alt']}]({image['url']})", proposed)
            self.assertEqual(PNG, (self.artifacts / "files" / image["path"]).read_bytes())
            self.assertEqual(sha, hashlib.sha256((self.root / image["path"]).read_bytes()).hexdigest())
        self.assertEqual(self.doc.read_bytes(),
                         (self.artifacts / "files" / self.doc.relative_to(self.root)).read_bytes())
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        self.assertEqual(4, len(validation["images"]))

    def test_incident_api_description_without_selection_overrides_automation_selection(self):
        self.incident_fixture()
        value = json.loads(self.ticket.read_text(encoding="utf-8"))
        value["issue_description"] = block([item("999", "FOREIGN-1")])
        self.ticket.write_text(json.dumps(value), encoding="utf-8")
        self.issues["DOC-104"]["description"]["content"].pop()
        self.run_proposal()
        self.assertEqual([], self.downloads)
        self.assertNotIn("images", json.loads(self.requests[0]["messages"][0]["content"]))

    def test_incident_invalid_selection_and_api_conversion_failures_abort_before_claude(self):
        selected, _ = self.incident_fixture()
        original = copy.deepcopy(self.issues["DOC-104"]["description"])
        for failure in ("malformed", "foreign", "request_attachment", "missing_attachment", "api", "conversion", "lost_text"):
            with self.subTest(failure=failure):
                adf = copy.deepcopy(original)
                self.issues["DOC-104"]["description"] = adf
                chosen = copy.deepcopy(selected)
                if failure == "foreign":
                    chosen[0]["issue_key"] = "OTHER-999"
                if failure == "request_attachment":
                    chosen[0]["issue_key"] = "DOC-104"
                    self.issues["DOC-104"]["attachment"] = self.issues["DOC-95"]["attachment"]
                if failure == "missing_attachment":
                    chosen[0]["attachment_id"] = "99999"
                adf["content"][1]["content"][0]["text"] = ("{" if failure == "malformed" else
                    json.dumps({"version": 1, "images": chosen}))
                if failure == "conversion":
                    self.issues["DOC-104"]["description"] = "Invalid ADF"
                patcher = (mock.patch.object(self, "jira", side_effect=GENERATOR.ProposalError("Jira API failed"))
                           if failure == "api" else mock.patch.object(GENERATOR, "adf_to_markdown", return_value="")
                           if failure == "lost_text" else nullcontext())
                with patcher, self.assertRaises((GENERATOR.ProposalError, IMAGES.ImageError)):
                    self.run_proposal()
                self.assertEqual([], self.requests)
                self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
                self.assertFalse(self.artifacts.exists())

    def test_incident_nonempty_selection_cannot_produce_empty_catalogue(self):
        self.incident_fixture()
        with mock.patch.object(IMAGES, "catalogue", return_value=([], {})), \
             self.assertRaisesRegex(GENERATOR.ProposalError, "selection was lost"):
            self.run_proposal()
        self.assertEqual([], self.requests)

    def test_incident_diagnosis_uses_canonical_context_without_download_or_claude(self):
        self.incident_fixture()
        with mock.patch.object(IMAGES, "download", side_effect=AssertionError("No download")), \
             mock.patch.object(GENERATOR, "http_transport", side_effect=AssertionError("No Claude")):
            report = GENERATOR.diagnose_jira_context(self.ticket, CONFIG, self.jira,
                repo_root=self.root, prompt_file=self.prompt, base_sha=self.base, **self.source_references)
        self.assertTrue(report["contexts_match"])
        self.assertEqual(8, len(self.jira_calls))
        safe = json.dumps(report)
        for forbidden in ("Contexto canónico", "Vista aprobada", "documentation-images-v1", CONFIG["token"],
                          CONFIG["email"], CONFIG["base_url"]):
            self.assertNotIn(forbidden, safe)
        self.assertEqual([], self.requests)
        self.assertEqual([], self.downloads)
        self.assertEqual("", self.git("status", "--porcelain"))

    def test_valid_image_publication_artifacts_and_unchanged_model_schema(self):
        self.run_proposal()
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        image = validation["images"][0]
        self.assertEqual("APP-2/11", image["id"])
        self.assertEqual(PNG, (self.root / image["path"]).read_bytes())
        self.assertEqual(PNG, (self.artifacts / "files" / image["path"]).read_bytes())
        self.assertEqual(self.doc.read_bytes(), (self.artifacts / "files" / self.doc.relative_to(self.root)).read_bytes())
        self.assertEqual(image["sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(GENERATOR.MODEL, self.requests[0]["model"])
        self.assertEqual(16384, self.requests[0]["max_tokens"])
        self.assertEqual(GENERATOR.PROPOSAL_SCHEMA, self.requests[0]["output_config"]["format"]["schema"])
        self.assertIsInstance(self.requests[0]["messages"][0]["content"], str)
        output = Path(self.temp.name) / "validation.json"
        output.write_text(json.dumps(validation), encoding="utf-8")
        body = Path(self.temp.name) / "pr.md"
        publication = PREPARER.prepare_publication(self.root, output, self.ticket, self.report, body,
            self.base, "123", "1", "example/repo", "https://github.com")
        self.assertIn(image["path"], json.loads(publication["files_json"]))
        self.assertEqual(1, len(json.loads(publication["documents_json"])))
        self.assertIn("APP-2/11", body.read_text(encoding="utf-8"))
        self.assertIn(image["sha256"], body.read_text(encoding="utf-8"))
        (self.root / image["path"]).write_bytes(PNG[:-1])
        with self.assertRaises(IMAGES.ImageError):
            PREPARER.prepare_publication(self.root, output, self.ticket, self.report, body,
                self.base, "123", "1", "example/repo", "https://github.com")

    def test_old_request_has_no_images_or_downloads(self):
        value = json.loads(self.ticket.read_text())
        value["issue_description"] = "Texto antiguo sin imágenes."
        self.ticket.write_text(json.dumps(value), encoding="utf-8")
        self.run_proposal(body="\nMás contexto.\n")
        self.assertEqual([], self.downloads)
        self.assertNotIn("images", json.loads(self.report.read_text()))
        self.assertNotIn("images", json.loads(self.requests[0]["messages"][0]["content"]))
        self.assertTrue(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_foreign_attachment_and_missing_real_id_rejected_before_model(self):
        for selected in ([item(key="OTHER-3")], [item("999")]):
            self.set_selection(selected)
            with self.subTest(selected=selected), self.assertRaises(IMAGES.ImageError):
                self.run_proposal()
        self.assertEqual([], self.requests)
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))

    def test_invalid_metadata_mime_size_and_binary(self):
        attachment = self.issues["APP-2"]["attachment"][0]
        original = copy.deepcopy(attachment)
        for fields in ({"size": IMAGES.MAX_IMAGE_BYTES + 1}, {"size": True}, {"mimeType": "image/svg+xml"},
                       {"size": len(PNG) + 1}, {"mimeType": "image/jpeg"}):
            attachment.update(original)
            attachment.update(fields)
            with self.subTest(fields=fields), self.assertRaises(IMAGES.ImageError):
                self.run_proposal()
        self.assertEqual([], self.requests)
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))

    def test_download_failure_has_no_partial_changes(self):
        self.downloader = mock.Mock(side_effect=IMAGES.ImageError("Download failed"))
        with self.assertRaises(IMAGES.ImageError):
            self.run_proposal()
        self.assertEqual([], self.requests)
        self.assertEqual("", self.git("status", "--porcelain"))

    def test_missing_unauthorized_alt_and_private_urls_rejected(self):
        url = f"/img/jira/app-2-11-{hashlib.sha256(PNG).hexdigest()}.png"
        for body in ("![Formulario](/img/jira/missing.png)\n", "![](https://tenant.atlassian.net/private)\n",
                     f"![Texto incorrecto]({url})\n", f'<img alt="Formulario" src="{url}" />\n',
                     f'![Formulario de acceso][capture]\n\n[capture]: {url}\n'):
            with self.subTest(body=body), self.assertRaises(IMAGES.ImageError):
                self.run_proposal(body=body)
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "static").exists())

    def test_same_filename_has_distinct_stable_paths(self):
        self.issues["APP-2"]["attachment"].append(dict(self.issues["APP-2"]["attachment"][0], id="12"))
        self.set_selection([item(), item("12")])
        self.run_proposal()
        images = json.loads(self.report.read_text())["images"]
        self.assertEqual(2, len({i["path"] for i in images}))
        self.assertEqual(2, len(self.downloads))
        self.assertTrue(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_downloaded_unused_and_code_example_not_published(self):
        url = f"/img/jira/app-2-11-{hashlib.sha256(PNG).hexdigest()}.png"
        self.run_proposal(body=f"\nEjemplo: `![Formulario de acceso]({url})`\n")
        self.assertEqual(1, len(self.downloads))
        self.assertNotIn("images", json.loads(self.report.read_text()))
        self.assertFalse((self.root / "static").exists())
        self.assertFalse((self.artifacts / "files/static").exists())
        catalogue = json.loads((self.artifacts / "catalogue.json").read_text())
        self.assertEqual([], catalogue["published"])
        self.assertEqual(1, len(catalogue["available"]))

    def test_abstention_never_publishes_images(self):
        self.run_proposal(abstain=True)
        self.assertEqual("", self.git("status", "--porcelain"))
        self.assertFalse((self.root / "static").exists())
        self.assertFalse((self.artifacts / "files").exists())
        result = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(result["valid"], result)
        self.assertEqual([], result["images"])

    def test_apply_failure_rolls_back_documents_images_and_directories(self):
        original = GENERATOR.os.link
        calls = 0
        def fail_second_image(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated image write failure")
            return original(source, target)
        self.issues["APP-2"]["attachment"].append(dict(self.issues["APP-2"]["attachment"][0], id="12"))
        self.set_selection([item(), item("12")])
        with mock.patch.object(GENERATOR.os, "link", side_effect=fail_second_image), self.assertRaises(GENERATOR.ProposalError):
            self.run_proposal()
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "static").exists())
        self.assertEqual("", self.git("status", "--porcelain"))

    def test_preexisting_image_reused_only_if_identical_and_tracked(self):
        path = f"static/img/jira/app-2-11-{hashlib.sha256(PNG).hexdigest()}.png"
        candidate = self.root / path
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(PNG)
        with self.assertRaisesRegex(GENERATOR.ProposalError, "untracked"):
            self.run_proposal()
        candidate.write_bytes(b"unrelated data")
        with self.assertRaises(IMAGES.ImageError):
            self.run_proposal()
        self.assertEqual(b"unrelated data", candidate.read_bytes())
        candidate.write_bytes(PNG)
        self.git("add", path)
        self.git("commit", "--quiet", "-m", "Fixture existing image")
        self.base = self.git("rev-parse", "HEAD")
        self.run_proposal()
        image = json.loads(self.report.read_text())["images"][0]
        self.assertEqual("reuse", image["operation"])
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        self.assertNotIn(path, validation["changed_files"])
        self.assertEqual(PNG, candidate.read_bytes())

    def test_adf_selection_and_legacy_manifest_kept_separate(self):
        value = json.loads(self.ticket.read_text())
        value["issue_description"] = "DOCUMENTATION_SOURCE_V1\nEPIC_KEY: APP-1\nTASK_KEYS:\n- APP-2\n"
        self.ticket.write_text(json.dumps(value), encoding="utf-8")
        self.issues["APP-2"]["description"] = {"type": "doc", "content": [{"type": "codeBlock",
            "attrs": {"language": "documentation-images-v1"}, "content": [{"type": "text",
            "text": json.dumps({"version": 1, "images": [item()]})}]}]}
        # Use the legacy source fields without appending any text to its strict manifest.
        with mock.patch.object(GENERATOR, "parse_jira_source_inputs", return_value=None):
            self.run_proposal()
        self.assertEqual(1, len(json.loads(self.report.read_text())["images"]))

    def test_validator_rejects_missing_tampered_and_unused_report_images(self):
        self.run_proposal()
        image = json.loads(self.report.read_text())["images"][0]
        candidate = self.root / image["path"]
        candidate.unlink()
        self.assertFalse(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])
        candidate.write_bytes(PNG[:-1])
        self.assertFalse(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])
        candidate.write_bytes(PNG)
        current = self.doc.read_text(encoding="utf-8")
        self.doc.write_text(current.replace(f"![{image['alt']}]({image['url']})", "Captura omitida"), encoding="utf-8")
        self.assertFalse(VALIDATOR.validate_repository(self.root, self.report, self.base)["valid"])

    def test_batch_count_and_duplicate_selection(self):
        self.set_selection([item()] * 2)
        with self.assertRaisesRegex(IMAGES.ImageError, "Duplicate"):
            self.run_proposal()
        self.set_selection([item(str(i + 1)) for i in range(IMAGES.MAX_IMAGES + 1)])
        with self.assertRaises(IMAGES.ImageError):
            self.run_proposal()

    def test_jpeg_download_reference_and_validation(self):
        attachment = self.issues["APP-2"]["attachment"][0]
        attachment.update({"mimeType": "image/jpeg", "size": len(JPEG), "filename": "captura.jpeg"})
        self.downloader = mock.Mock(return_value=JPEG)
        self.run_proposal()
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        self.assertTrue(validation["images"][0]["path"].endswith(".jpg"))

    def test_batch_byte_limit_and_large_binary_separate_from_markdown_limit(self):
        size = 1_800_000
        padding = b"padding\0" + b"x" * (size - len(PNG) - 20)
        kind = b"tEXt"
        chunk = struct.pack(">I", len(padding)) + kind + padding + struct.pack(">I", zlib.crc32(kind + padding) & 0xffffffff)
        data = PNG[:33] + chunk + PNG[33:]
        attachment = self.issues["APP-2"]["attachment"][0]
        attachment["size"] = len(data)
        self.downloader = mock.Mock(return_value=data)
        self.run_proposal()
        validation = VALIDATOR.validate_repository(self.root, self.report, self.base)
        self.assertTrue(validation["valid"], validation)
        self.assertGreater(validation["images"][0]["size"], validation["limits"]["max_diff_bytes"])
        attachments = [dict(attachment, id=str(i)) for i in range(11, 16)]
        self.issues["APP-2"]["attachment"] = attachments
        self.set_selection([item(str(i)) for i in range(11, 16)])
        with self.assertRaisesRegex(IMAGES.ImageError, "byte limit"):
            self.run_proposal()

    def test_image_appearing_during_apply_is_not_overwritten(self):
        original = GENERATOR.os.link
        appeared = b"Concurrent unrelated image"
        def appearing_image(source, target):
            target.write_bytes(appeared)
            return original(source, target)
        with mock.patch.object(GENERATOR.os, "link", side_effect=appearing_image), self.assertRaises(GENERATOR.ProposalError):
            self.run_proposal()
        self.assertEqual(self.before, self.doc.read_text(encoding="utf-8"))
        self.assertEqual(appeared, next((self.root / "static/img/jira").glob("*.png")).read_bytes())

    def test_symlink_image_directory_is_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            (self.root / "static").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Windows does not allow creating symlinks")
        with self.assertRaises(IMAGES.ImageError):
            self.run_proposal()
        self.assertEqual([], list(outside.iterdir()))


class ImageWorkflowWiringTests(unittest.TestCase):
    def test_workflow_stages_module_and_includes_recoverable_binaries(self):
        workflow = (SCRIPTS.parent / "workflows/documentation-agent-poc.yml").read_text(encoding="utf-8")
        # The shared startup regression executes this staging list via git show.
        self.assertIn('"scripts/documentation_images.py"', workflow)
        self.assertIn('--image-artifacts "${RUNNER_TEMP}/documentation-proposal-files"', workflow)
        self.assertIn('${{ runner.temp }}/documentation-proposal-files/', workflow)
        self.assertIn('FILES_JSON: ${{ steps.publication.outputs.files_json }}', workflow)
        self.assertIn('os.environ["FILES_JSON"]', workflow)
        self.assertIn('git add -- "${documents[@]}"', workflow)
        self.assertNotIn("git add .", workflow)


if __name__ == "__main__":
    unittest.main()
