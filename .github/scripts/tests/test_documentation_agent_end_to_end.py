from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = load_script("e2e_generator", "generate-documentation-proposal.py")
VALIDATOR = load_script("e2e_validator", "validate-documentation-proposal.py")
PREPARER = load_script("e2e_preparer", "prepare-documentation-pull-request.py")


class DocumentationAgentEndToEndTests(unittest.TestCase):
    def test_simulated_workflow_creates_and_updates_in_one_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            root = temporary_root / "repository with spaces"
            root.mkdir()

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                ).stdout.strip()

            def write(relative: str, content: str) -> Path:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="")
                return path

            git("init", "--quiet")
            git("config", "user.name", "E2E Tests")
            git("config", "user.email", "e2e@example.invalid")
            git("config", "core.autocrlf", "false")
            frontmatter = (
                "---\narticle_id: ART-1\ntitle: \"Acceso\"\n"
                "version: 1.0\n---\n"
            )
            write("docs/centro-de-ayuda/cuenta/index.md", frontmatter + "\n# Cuenta\n")
            write(
                "docs/centro-de-ayuda/cuenta/acceder.md",
                frontmatter + "\n# Acceso\n\nUsa tu contraseña.\n",
            )
            git("add", ".")
            git("commit", "--quiet", "-m", "Initial")
            base_sha = git("rev-parse", "HEAD")

            ticket = temporary_root / "ticket.json"
            ticket.write_text(
                json.dumps({
                    "issue_key": "DOC-1",
                    "issue_summary": "Documentar acceso y alertas",
                    "issue_description": "Añade el segundo factor y las alertas.",
                }),
                encoding="utf-8",
            )
            prompt = temporary_root / "prompt.md"
            prompt.write_text("Trusted prompt", encoding="utf-8")
            report = temporary_root / "agent-report.json"
            proposal = {
                "decision": "proposal",
                "summary": "Actualizar acceso y crear alertas",
                "reason": "El ticket contiene evidencia suficiente",
                "evidence": "Ticket DOC-1 y documentación local",
                "documents": [
                    {
                        "operation": "update",
                        "path": "docs/centro-de-ayuda/cuenta/acceder.md",
                        "title": "Acceso",
                        "reason": "Añadir segundo factor",
                        "evidence": "Ticket DOC-1",
                        "proposed_body": (
                            "\n# Acceso\n\nUsa tu contraseña y el segundo factor.\n"
                        ),
                    },
                    {
                        "operation": "create",
                        "path": "docs/centro-de-ayuda/cuenta/activar-alertas.md",
                        "title": "Activar alertas",
                        "reason": "No existe un artículo aplicable",
                        "evidence": "Ticket DOC-1",
                        "proposed_body": "\n# Activar alertas\n\nActiva las alertas.\n",
                    },
                ],
            }

            def transport(*args: object) -> dict[str, object]:
                return {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": json.dumps(proposal, ensure_ascii=False)}]
                        }
                    }]
                }

            GENERATOR.generate_and_apply(
                root, ticket, prompt, report, "fake-key", transport,
                base_sha=base_sha,
            )
            validation = VALIDATOR.validate_repository(root, report, base_sha)
            self.assertTrue(validation["valid"], validation)

            validation_file = temporary_root / "validation.json"
            validation_file.write_text(
                json.dumps(validation, ensure_ascii=False), encoding="utf-8"
            )
            body_file = temporary_root / "pull-request-body.md"
            publication = PREPARER.prepare_publication(
                root, validation_file, ticket, report, body_file, base_sha,
                "123", "1", "example/documentation", "https://github.com",
            )
            self.assertEqual("true", publication["publish"])
            operations = {
                item["operation"]
                for item in json.loads(publication["documents_json"])
            }
            self.assertEqual({"create", "update"}, operations)
            self.assertIn("Documentos creados", body_file.read_text(encoding="utf-8"))
            self.assertIn(
                "Documentos actualizados", body_file.read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
