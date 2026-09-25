from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = REPO_ROOT / "docs"
HELP_CENTER_ROOT = DOCS_ROOT / "centro-de-ayuda"
MANIFEST_PATH = (
    REPO_ROOT / ".github" / "migrations" / "notion-public-docs-manifest.json"
)

CATEGORIES = (
    ("inicio-y-acceso", "Inicio y acceso", 1),
    (
        "perfil-de-empresa-en-google",
        "Conexión Perfil de Empresa en Google",
        2,
    ),
    ("visibilidad", "Visibilidad", 3),
    ("reputacion", "Reputación", 4),
    ("fidelizacion", "Fidelización", 5),
    ("beelma", "Beelma", 6),
    ("analitica", "Analítica", 7),
    ("cuenta-y-facturacion", "Cuenta y facturación", 8),
)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"Missing frontmatter in {path}")
    block = text.split("---\n", 2)[1]
    values: dict[str, str] = {}
    for line in block.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


class PublicHelpCenterStructureTests(unittest.TestCase):
    def assert_public_docs_contract(self, docs_root: Path) -> None:
        repository_root = docs_root.parent
        help_center_root = docs_root / "centro-de-ayuda"
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        migrated_records = [
            item
            for category in manifest["categories"]
            for item in [category, *category["articles"]]
        ]
        migrated_paths = {
            repository_root / item["path"]: item for item in migrated_records
        }
        self.assertEqual(32, len(migrated_paths))

        for path, record in migrated_paths.items():
            self.assertTrue(path.is_file(), f"Missing migrated document: {record['path']}")
            metadata = frontmatter(path)
            self.assertEqual(record["article_id"], metadata.get("article_id"))
            self.assertEqual(record["notion_id"], metadata.get("notion_id"))

        public = sorted(
            path for path in docs_root.rglob("*.md")
            if "production-snapshots" not in path.relative_to(docs_root).parts
        )
        metadata_by_path = {path: frontmatter(path) for path in public}
        article_ids = [metadata.get("article_id") for metadata in metadata_by_path.values()]
        self.assertTrue(all(article_ids), "Every public document needs article_id")
        self.assertEqual(len(article_ids), len(set(article_ids)))

        notion_ids = [
            metadata["notion_id"]
            for metadata in metadata_by_path.values()
            if "notion_id" in metadata
        ]
        self.assertEqual(len(notion_ids), len(set(notion_ids)))

        category_indexes = {
            repository_root / category["path"] for category in manifest["categories"]
        }
        self.assertEqual(
            category_indexes,
            set(help_center_root.glob("*/index.md")),
        )
        category_directories = {path.parent for path in category_indexes}
        for path in help_center_root.rglob("*.md"):
            if path.name == "index.md":
                self.assertIn(path, category_indexes)
            else:
                self.assertIn(path.parent, category_directories)

            if path not in migrated_paths:
                metadata = metadata_by_path[path]
                self.assertNotIn("notion_id", metadata)
                self.assertRegex(
                    metadata["article_id"], r"^GITHUB-[0-9A-F]{32}$"
                )

        root_slugs = [
            path for path, metadata in metadata_by_path.items()
            if metadata.get("slug") == "/"
        ]
        self.assertEqual([docs_root / "index.md"], root_slugs)

    @staticmethod
    def write_native_article(path: Path, article_id: str, title: str) -> None:
        path.write_text(
            "---\n"
            f"article_id: {article_id}\n"
            f'title: "{title}"\n'
            "version: 1.0\n"
            "status: published\n"
            "owner: Product\n"
            "last_reviewed: 2026-09-23\n"
            "---\n\n"
            f"# {title}\n",
            encoding="utf-8",
            newline="",
        )

    def test_public_docs_preserve_migrated_documents_and_allow_native_articles(self) -> None:
        self.assert_public_docs_contract(DOCS_ROOT)

    def test_native_article_without_notion_id_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs_root = Path(temporary) / "docs"
            shutil.copytree(DOCS_ROOT, docs_root)
            native = docs_root / "centro-de-ayuda" / "cuenta-y-facturacion" / "articulo-nativo.md"
            self.write_native_article(native, "GITHUB-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Artículo nativo")
            self.assert_public_docs_contract(docs_root)

    def test_second_native_creation_is_valid_after_the_first_is_incorporated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs_root = Path(temporary) / "docs"
            shutil.copytree(DOCS_ROOT, docs_root)
            category = docs_root / "centro-de-ayuda" / "cuenta-y-facturacion"
            self.write_native_article(
                category / "primer-articulo.md",
                "GITHUB-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
                "Primer artículo",
            )
            self.assert_public_docs_contract(docs_root)
            self.write_native_article(
                category / "segundo-articulo.md",
                "GITHUB-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
                "Segundo artículo",
            )
            self.assert_public_docs_contract(docs_root)

    def test_home_is_independent_and_displays_category_sidebar(self) -> None:
        home = DOCS_ROOT / "index.md"
        metadata = frontmatter(home)
        self.assertEqual("Centro de Ayuda Beesible", metadata["title"])
        self.assertEqual("1.2", metadata["version"])
        self.assertEqual("published", metadata["status"])
        self.assertEqual("Product", metadata["owner"])
        self.assertEqual("2026-09-09", metadata["last_reviewed"])
        self.assertEqual("/", metadata["slug"])
        self.assertEqual("docsSidebar", metadata["displayed_sidebar"])
        self.assertNotIn("notion_id", metadata)

        body = home.read_text(encoding="utf-8")
        self.assertNotIn("Explora por categoría", body)
        self.assertNotIn("help-categories", body)
        self.assertFalse(re.findall(r"\[[^]]+]\(([^)]+)\)", body))
        self.assertIn("docsSidebar: [{type: 'autogenerated', dirName: 'centro-de-ayuda'}]",
                      (REPO_ROOT / "sidebars.js").read_text(encoding="utf-8"))

    def test_docs_contain_exactly_one_root_slug(self) -> None:
        root_slugs = [
            path
            for path in DOCS_ROOT.rglob("*.md")
            if frontmatter(path).get("slug") == "/"
        ]
        self.assertEqual([DOCS_ROOT / "index.md"], root_slugs)

    def test_internal_project_doc_is_outside_public_docs(self) -> None:
        flow = REPO_ROOT / "project-docs" / "flujo-agente-documentacion.md"
        self.assertTrue(flow.is_file())
        self.assertFalse((DOCS_ROOT / "flujo-agente-documentacion.md").exists())
        self.assertNotIn("slug", frontmatter(flow))
        self.assertIn("```mermaid\nflowchart TD", flow.read_text(encoding="utf-8"))

        readme = (REPO_ROOT / "project-docs" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("no se publica en GitHub Pages", readme)
        self.assertIn("repositorio público", readme)
        self.assertIn("repositorio o sistema privado", readme)

    def test_fictitious_poc_content_is_absent_and_snapshot_is_preserved(self) -> None:
        self.assertFalse((DOCS_ROOT / "archivos-adjuntos.md").exists())
        self.assertFalse((DOCS_ROOT / "invitaciones.md").exists())
        self.assertTrue(
            (DOCS_ROOT / "production-snapshots" / "invitations.json").is_file()
        )

        generator = (
            REPO_ROOT
            / ".github"
            / "scripts"
            / "generate-documentation-proposal.py"
        ).read_text(encoding="utf-8")
        generator_tests = (
            REPO_ROOT
            / ".github"
            / "scripts"
            / "tests"
            / "test_generate_documentation_proposal.py"
        ).read_text(encoding="utf-8")
        self.assertIn("production-snapshots", generator)
        self.assertIn("read-only", generator)
        self.assertIn("TemporaryDirectory", generator_tests)
        self.assertIn("production-snapshots", generator_tests)

    def test_sidebar_uses_category_indices_without_technical_parent(self) -> None:
        sidebar = (REPO_ROOT / "sidebars.js").read_text(encoding="utf-8")
        self.assertIn("type: 'autogenerated'", sidebar)
        self.assertIn("dirName: 'centro-de-ayuda'", sidebar)
        self.assertNotIn("dirName: '.'", sidebar)

        observed = []
        for folder, title, position in CATEGORIES:
            metadata = frontmatter(HELP_CENTER_ROOT / folder / "index.md")
            observed.append((metadata["title"], int(metadata["sidebar_position"])))
        self.assertEqual(
            [(title, position) for _, title, position in CATEGORIES],
            observed,
        )

    def test_site_identity_is_public_help_center(self) -> None:
        config = (REPO_ROOT / "docusaurus.config.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(config.count("Centro de Ayuda Beesible"), 2)
        self.assertIn("sidebarPath: './sidebars.js'", config)
        self.assertNotIn("require.resolve('./sidebars.js')", config)
        self.assertNotIn("Documentación BeeDigital", config)
        self.assertNotIn("label: 'Documentación'", config)
        self.assertNotIn("project-docs", config)

    def test_all_migrated_internal_links_resolve_without_uuids(self) -> None:
        uuid = re.compile(r"[0-9a-f]{32}", re.IGNORECASE)
        broken: list[str] = []
        for source in HELP_CENTER_ROOT.rglob("*.md"):
            text = source.read_text(encoding="utf-8")
            for target in re.findall(r"!?\[[^]]*]\(([^)]+)\)", text):
                if re.match(r"^(?:https?|mailto|tel):|^#", target, re.IGNORECASE):
                    continue
                path = target.split("#", 1)[0]
                if uuid.search(target) or not (source.parent / path).is_file():
                    broken.append(f"{source.relative_to(REPO_ROOT)} -> {target}")
        self.assertEqual([], broken)

    def test_manifest_represents_only_notion_pages(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(32, manifest["source"]["markdown_pages"])
        paths = [
            item["path"]
            for category in manifest["categories"]
            for item in [category, *category["articles"]]
        ]
        self.assertEqual(32, len(paths))
        self.assertNotIn("docs/index.md", paths)


if __name__ == "__main__":
    unittest.main()
