from __future__ import annotations

import importlib.util
import stat
import sys
import unittest
import zipfile
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "migrate-notion-public-docs.py"
)
SPEC = importlib.util.spec_from_file_location("migrate_notion_public_docs", MIGRATION_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load migration from {MIGRATION_PATH}")
MIGRATION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MIGRATION
SPEC.loader.exec_module(MIGRATION)


class NotionAsideConversionTests(unittest.TestCase):
    def test_one_line_aside(self) -> None:
        self.assertEqual(
            ":::note\nContenido\n:::",
            MIGRATION.convert_asides("<aside>Contenido</aside>"),
        )

    def test_multiline_aside(self) -> None:
        source = "<aside>\nPrimera línea\n\nSegunda línea\n</aside>"
        self.assertEqual(
            ":::note\nPrimera línea\n\nSegunda línea\n:::",
            MIGRATION.convert_asides(source),
        )

    def test_multiple_asides_in_one_document(self) -> None:
        source = "Antes\n\n<aside>Uno</aside>\n\nCentro\n\n<aside>Dos</aside>\n"
        converted = MIGRATION.convert_asides(source)
        self.assertEqual(2, converted.count(":::note"))
        self.assertIn(":::note\nUno\n:::", converted)
        self.assertIn(":::note\nDos\n:::", converted)

    def test_indented_aside_is_dedented_without_changing_text(self) -> None:
        source = "<aside>\n    Línea uno\n    \n    - elemento\n    </aside>"
        self.assertEqual(
            ":::note\nLínea uno\n\n- elemento\n:::",
            MIGRATION.convert_asides(source),
        )

    def test_internal_content_is_preserved_exactly(self) -> None:
        inner = "Texto **exacto**, con ñ y [enlace](https://example.com)."
        converted = MIGRATION.convert_asides(f"<aside>{inner}</aside>")
        self.assertEqual(inner, converted.splitlines()[1])

    def test_markdown_normalization_removes_only_trailing_whitespace(self) -> None:
        source = "Texto con espacio. \n    \nTexto sin cambios."
        self.assertEqual(
            "Texto con espacio.\n\nTexto sin cambios.",
            MIGRATION.normalize_markdown(source),
        )


class NotionMigrationSafetyTests(unittest.TestCase):
    def zip_info(self, name: str, mode: int = 0) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name)
        info.external_attr = mode << 16
        return info

    def test_absolute_zip_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(MIGRATION.MigrationError, "unsafe path"):
            MIGRATION.validate_member(self.zip_info("/absolute/page.md"))

    def test_traversal_zip_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(MIGRATION.MigrationError, "unsafe path"):
            MIGRATION.validate_member(self.zip_info("../outside.md"))

    def test_zip_symlink_is_rejected(self) -> None:
        with self.assertRaisesRegex(MIGRATION.MigrationError, "symlink"):
            MIGRATION.validate_member(self.zip_info("page.md", stat.S_IFLNK | 0o777))

    def test_slug_is_utf8_derived_and_path_safe(self) -> None:
        self.assertEqual(
            "anadir-informacion-y-analitica",
            MIGRATION.slugify("Añadir información y analítica"),
        )

    def test_link_is_resolved_by_uuid_not_title(self) -> None:
        source = MIGRATION.PurePosixPath("docs/centro-de-ayuda/a/index.md")
        target_id = "0123456789abcdef0123456789abcdef"
        destinations = {
            target_id: MIGRATION.PurePosixPath(
                "docs/centro-de-ayuda/a/titulo-real.md"
            )
        }
        content = f"[Nombre incorrecto](texto-mal-codificado-{target_id}.md)"
        self.assertEqual(
            "[Nombre incorrecto](titulo-real.md)",
            MIGRATION.rewrite_links(content, source, destinations),
        )

    def test_external_link_is_preserved(self) -> None:
        source = MIGRATION.PurePosixPath("docs/centro-de-ayuda/a/index.md")
        link = "[Google](https://support.google.com/?hl=es#ayuda)"
        self.assertEqual(link, MIGRATION.rewrite_links(link, source, {}))

    def test_frontmatter_uses_deterministic_uuid_identity(self) -> None:
        page = MIGRATION.Page(
            notion_id="0123456789abcdef0123456789abcdef",
            title="Título español",
            source_name="ignored.md",
            content="# Título español\n",
            created=None,
            category_id="category",
            destination=MIGRATION.PurePosixPath("docs/example.md"),
            is_category=False,
        )
        frontmatter = MIGRATION.render_frontmatter(page)
        self.assertIn(
            "article_id: NOTION-0123456789ABCDEF0123456789ABCDEF", frontmatter
        )
        self.assertIn('title: "Título español"', frontmatter)
        self.assertIn("version: 1.0", frontmatter)
        self.assertIn("status: published", frontmatter)
        self.assertIn("owner: Product", frontmatter)
        self.assertIn("last_reviewed: 2026-09-09", frontmatter)
        self.assertIn(
            "notion_id: 0123456789abcdef0123456789abcdef", frontmatter
        )


if __name__ == "__main__":
    unittest.main()
