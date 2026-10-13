"""Offline size and CLI checks: python -B -m unittest discover -s tests -p test_medir_lote.py."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/create-documentation-epic/scripts/medir_lote.py"
SPEC = importlib.util.spec_from_file_location("medir_lote", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def batch():
    return {
        "documentation_task": {"key": "DOC-9", "summary": "Idioma", "description": "Contexto"},
        "epic": {"key": "APP-1", "summary": "Preferencias", "description": "Épica"},
        "tasks": [{"key": "APP-2", "summary": "Cambiar idioma", "description": "Guardar"}],
    }


class MeasureBatchTests(unittest.TestCase):
    def test_matches_existing_generator_with_simulated_jira(self):
        generator_path = ROOT / ".github/scripts/generate-documentation-proposal.py"
        spec = importlib.util.spec_from_file_location("epic_measure_generator", generator_path)
        generator = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = generator
        spec.loader.exec_module(generator)
        value = batch()
        value["documentation_task"]["description"] = " Contexto\r\n🚀 "
        issues = {}
        for issue in [value["epic"], *value["tasks"]]:
            adf = {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": issue["description"]}]},
                {"type": "codeBlock", "content": [{"type": "text", "text": "ñ\n  ejemplo"}]},
            ]}
            issues[issue["key"]] = {"key": issue["key"], "fields": {
                "summary": " " + issue["summary"] + " ", "description": adf,
                "issuetype": {"name": "Epic" if issue is value["epic"] else "Task"},
                "parent": {"key": value["epic"]["key"]},
                "labels": ["documentation-required"],
                "status": {"statusCategory": {"key": "done"}},
            }}
            issue["description"] = generator.adf_to_markdown(adf)

        def fake_transport(endpoint, *_args):
            key = urllib.parse.urlparse(endpoint).path.rsplit("/", 1)[1]
            return issues[key]

        human = value["documentation_task"]
        resolved = generator.resolve_jira_source(
            {"issue_key": human["key"], "issue_summary": human["summary"],
             "issue_description": human["description"]},
            {"base_url": "https://example.invalid", "email": "fixture@example.invalid",
             "token": "offline-fixture"},
            fake_transport, 1,
            jira_epic_key=value["epic"]["key"], jira_task_keys=value["tasks"][0]["key"],
        )
        self.assertEqual(resolved["issue_description"], MODULE.compose_context(value))

    def test_composition_preserves_human_and_trims_jira_markdown(self):
        value = batch()
        value["documentation_task"]["description"] = "  humano\r\n "
        value["epic"]["summary"] = " Preferencias "
        value["epic"]["description"] = "  Épica\n "
        value["tasks"][0]["description"] = " \nGuardar  "
        self.assertEqual(
            "Documentation task DOC-9: Idioma\n\n  humano\r\n "
            "\n\nEpic APP-1: Preferencias\n\nÉpica"
            "\n\nTask APP-2: Cambiar idioma\n\nGuardar",
            MODULE.compose_context(value),
        )

    def test_budget_boundaries(self):
        for size, code in [(44_999, 0), (45_000, 0), (45_001, 1), (60_000, 1), (60_001, 2)]:
            with self.subTest(size=size):
                value = batch()
                value["documentation_task"]["description"] = ""
                overhead = len(MODULE.compose_context(value))
                value["documentation_task"]["description"] = "á" * (size - overhead)
                before = copy.deepcopy(value)
                report = MODULE.measure(value)
                self.assertEqual(size, report["characters"])
                self.assertEqual(code, report["exit_code"])
                self.assertEqual(before, value)  # No silent truncation or mutation.

    def test_unicode_counts_codepoints_not_bytes_or_graphemes(self):
        value = batch()
        baseline = MODULE.measure(value)["characters"]
        text = "ñ🚀e\u0301中文"
        value["documentation_task"]["description"] += text
        self.assertEqual(baseline + 6, MODULE.measure(value)["characters"])
        self.assertGreater(len(text.encode("utf-8")), len(text))

    def test_order_and_empty_descriptions(self):
        value = batch()
        value["epic"]["description"] = ""
        value["tasks"].append({"key": "APP-3", "summary": "Revisar", "description": ""})
        context = MODULE.compose_context(value)
        self.assertIn("Epic APP-1: Preferencias\n\nTask APP-2", context)
        self.assertTrue(context.endswith("Task APP-3: Revisar"))

    def test_schema_rejects_omissions_wrong_types_and_duplicates(self):
        invalid = []
        for field in ("documentation_task", "epic", "tasks"):
            value = batch()
            del value[field]
            invalid.append(value)
        for tasks in ([], "APP-2", [None]):
            value = batch()
            value["tasks"] = tasks
            invalid.append(value)
        for field, content in [("description", None), ("summary", " "), ("key", " APP-1")]:
            value = batch()
            value["epic"][field] = content
            invalid.append(value)
        value = batch()
        value["tasks"][0]["key"] = value["epic"]["key"]
        invalid.append(value)
        value = batch()
        value["epic"]["comments"] = "omitted context"
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.measure(value)

    def run_cli(self, path):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(path)], capture_output=True, text=True)

    def test_cli_small_over_budget_over_limit_and_unicode(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lote con espacios.json"
            for text, code in [("ñ🚀中文", 0), ("x" * 45_001, 1), ("x" * 60_001, 2)]:
                value = batch()
                value["documentation_task"]["description"] = text
                path.write_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8-sig"))
                result = self.run_cli(path)
                self.assertEqual(code, result.returncode, result.stderr)
                self.assertEqual(MODULE.measure(value), json.loads(result.stdout))
                self.assertNotIn("description", result.stdout)

    def test_cli_invalid_files_do_not_leak_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            for data in (b"private-secret", b"\xff", b"{}"):
                path.write_bytes(data)
                result = self.run_cli(path)
                self.assertEqual(3, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertNotIn("private-secret", result.stderr)
            self.assertEqual(3, self.run_cli(Path(temporary) / "missing.json").returncode)


if __name__ == "__main__":
    unittest.main()
