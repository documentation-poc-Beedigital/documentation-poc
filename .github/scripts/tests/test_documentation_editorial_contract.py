import json
import tempfile
import unittest
from pathlib import Path

from navigation_fixture import GENERATOR as G, VALIDATOR as V, apply, fixture, load, CATEGORY, REGISTER
import documentation_contract as contract


class EditorialContractTests(unittest.TestCase):
    def item(self, **extra):
        return dict(reason="Cambio acotado", evidence="Evidencia local", **extra)

    def test_verified_destination_and_invented_screen(self):
        contract.check_content("", "[Web](https://www.beesible.ai/)", self.item())
        for url in ["https://www.beesible.ai/register", "https://app.beesible.ai/", "https://www.beesible.ai/?token=secret"]:
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Unverified"):
                contract.check_content("", f"[Accede]({url})", self.item())

    def test_pending_included_with_marker_and_explanation(self):
        contract.check_content("", "La prueba dura X días [VERIFICAR] V-01", dict(reason="V-01 pendiente: duración", evidence="Ticket"))
        with self.assertRaisesRegex(ValueError, "explained"):
            contract.check_content("", "Dato [VERIFICAR] V-01", self.item())

    def test_secondary_omitted_and_resolved_with_evidence(self):
        before = "Mensaje de error [VERIFICAR] V-01"
        contract.check_content(before, "Recorrido principal", dict(reason="V-01 omitido: error secundario fuera del recorrido", evidence="Ticket"))
        contract.check_content(before, "Mensaje de error confirmado", dict(reason="V-01 resuelto: aclaración atribuida al PM, sección errores", evidence="Ticket"))
        with self.assertRaisesRegex(ValueError, "Removed uncertainty"):
            contract.check_content(before, "Mensaje de error", self.item())

    def test_unrelated_markers_and_occurrences_preserved(self):
        before = "Contenido ajeno [VERIFICAR] V-02\nOtro [VERIFICAR] V-02"
        contract.check_content(before, before + "\nCambio confirmado", self.item())
        with self.assertRaisesRegex(ValueError, "V-02"):
            contract.check_content(before, before.splitlines()[0], self.item())

    def test_ticket_ids_need_not_all_appear_in_article(self):
        request = G.build_request("Prompt", {"issue_description": "Error secundario [VERIFICAR] V-99"}, [])
        self.assertIn("verified_destinations", json.loads(request["messages"][0]["content"]))
        contract.check_content("", "Recorrido principal confirmado", dict(reason="V-99 omitido: secundario", evidence="Ticket"))
        self.assertEqual(16384, request["max_tokens"])
        self.assertNotIn("sidebar_position", G.DOCUMENT_SCHEMA["required"])

    def test_order_metadata_survives_report_and_independent_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repository with spaces"
            report = Path(temp) / "report.json"
            result = apply(root, report)
            self.assertTrue(result["valid"])
            preparation = load("prepare-documentation-pull-request")
            body = preparation.build_pull_request_body(
                dict(issue_key="DOC-1", issue_summary="Orden lógico"),
                json.loads(report.read_text(encoding="utf-8")), "https://github.com/example/docs/actions/runs/1")
            self.assertIn("Posición propuesta en la categoría: `2`", body)
            validation = Path(temp) / "validation.json"
            validation.write_text(json.dumps(result), encoding="utf-8")
            ticket = Path(temp) / "ticket.json"
            ticket.write_text(json.dumps(dict(issue_key="DOC-1", issue_summary="Orden lógico", issue_description="Recorrido confirmado")), encoding="utf-8")
            publication = preparation.prepare_publication(root, validation, ticket, report,
                Path(temp) / "pr-body.md", result["base_sha"], "123", "1", "example/docs", "https://github.com")
            self.assertEqual(2, json.loads(publication["documents_json"])[1]["sidebar_position"])
            tampered = json.loads(report.read_text(encoding="utf-8"))
            tampered["documents"][1]["sidebar_position"] = 99
            report.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(preparation.PublicationPreparationError, "navigation"):
                preparation.prepare_publication(root, validation, ticket, report,
                    Path(temp) / "pr-body.md", result["base_sha"], "123", "1", "example/docs", "https://github.com")

    def test_editorial_rejections_are_atomic(self):
        for change, error in [("[Accede](https://app.beesible.ai/login)", "Unverified"),
                              ("Confirmado sin marca", "Removed uncertainty")]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                proposal, _ = fixture(root)
                register = root / CATEGORY / REGISTER
                if error == "Removed uncertainty":
                    register.write_text(register.read_text(encoding="utf-8") + "\nDato ajeno [VERIFICAR] V-20\n", encoding="utf-8", newline="")
                before = {p: p.read_bytes() for p in (root / CATEGORY).glob("*.md")}
                proposal["documents"][1]["proposed_body"] += change
                with self.assertRaisesRegex(G.ProposalError, error):
                    G.prepare_changes(root, proposal)
                self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_invalid_later_operation_never_changes_earlier_document(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proposal, _ = fixture(root)
            original = (root / CATEGORY / "index.md").read_bytes()
            proposal["documents"][1]["sidebar_position"] = True
            with self.assertRaises(G.ProposalError):
                G.prepare_changes(root, proposal)
            self.assertEqual(original, (root / CATEGORY / "index.md").read_bytes())

    def test_position_limits_and_duplicate_positions(self):
        for value in [True, 1, 0, float("nan"), float("inf"), "2", 10001]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.position("---\nversion: 1.0\n---\n", dict(path=CATEGORY + REGISTER, sidebar_position=value))
        with self.assertRaises(ValueError):
            contract.position("---\n---\n", dict(path=CATEGORY + "index.md", sidebar_position=2))

    def test_position_collision_with_mdx_sibling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            category = root / CATEGORY
            category.mkdir(parents=True)
            (category / "existing.mdx").write_text("---\ntitle: Hermano\nsidebar_position: 2\n---\nContenido ajeno", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "collides"):
                contract.check_navigation(root, [dict(path=CATEGORY + REGISTER, sidebar_position=2)])
