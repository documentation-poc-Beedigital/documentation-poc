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
            return {"content": [{"type": "text", "text": json.dumps(proposal)}]}
        return GENERATOR.generate_and_apply(self.root, self.ticket, self.prompt, self.report, "test-only", model,
            base_sha=self.base, jira_configuration=CONFIG, jira_transport=self.jira,
            jira_epic_key="APP-1", jira_task_keys="APP-2", image_downloader=self.downloader,
            image_artifacts=self.artifacts)

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
        self.assertIn('${BASE_SHA}:.github/scripts/documentation_images.py', workflow)
        self.assertIn('--image-artifacts "${RUNNER_TEMP}/documentation-proposal-files"', workflow)
        self.assertIn('${{ runner.temp }}/documentation-proposal-files/', workflow)
        self.assertIn('FILES_JSON: ${{ steps.publication.outputs.files_json }}', workflow)
        self.assertIn('os.environ["FILES_JSON"]', workflow)
        self.assertIn('git add -- "${documents[@]}"', workflow)
        self.assertNotIn("git add .", workflow)


if __name__ == "__main__":
    unittest.main()
