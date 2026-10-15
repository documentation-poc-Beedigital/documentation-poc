"""Build a real proposal in an isolated repository, never in published docs."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = load("generate-documentation-proposal")
VALIDATOR = load("validate-documentation-proposal")
CATEGORY = "docs/centro-de-ayuda/inicio-y-acceso/"
REGISTER = "registrarte-probar-beesible-y-activar-el-plan-start.md"
ACCESS = "acceder-a-la-plataforma.md"
TITLE = "Registrarte, probar Beesible y activar el Plan Start"


def fixture(root):
    category = root / CATEGORY
    category.mkdir(parents=True)
    bodies = {
        "index.md": f"# Inicio y acceso\n\n[Acceder a la plataforma]({ACCESS})\n\n[{TITLE}]({REGISTER})\n\nTexto editorial ajeno.\n",
        REGISTER: f"# {TITLE}\n\nRegistro confirmado.\n",
        ACCESS: "# Acceder a la plataforma\n\nAcceso recurrente.\n",
    }
    for name, body in bodies.items():
        title = TITLE if name == REGISTER else "Acceder a la plataforma" if name == ACCESS else "Inicio y acceso"
        front = GENERATOR.create_frontmatter(CATEGORY + name, title)
        if name == "index.md":
            front = front.replace("version: 1.0", "version: 1.0\nsidebar_position: 1")
        (category / name).write_text(front + body, encoding="utf-8", newline="")
    (root / "docs/index.md").write_text("---\ntitle: Inicio\nslug: /\n---\n\n# Inicio\n", encoding="utf-8", newline="")
    for args in [("init", "--quiet"), ("config", "user.name", "Fixture"),
                 ("config", "user.email", "fixture@example.invalid"),
                 ("config", "core.autocrlf", "false"), ("add", "."), ("commit", "--quiet", "-m", "Fixture")]:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    def item(name, body, **extra):
        return dict(operation="update", path=CATEGORY + name, title=TITLE if name == REGISTER else "Inicio y acceso",
                    reason="Registro antes del acceso recurrente; conservar contenido ajeno",
                    evidence="Índice y recorrido de Inicio y acceso", proposed_body=body, **extra)
    index = f"# Inicio y acceso\n\n[{TITLE}]({REGISTER})\n\n[Acceder a la plataforma]({ACCESS})\n\nTexto editorial ajeno.\n"
    proposal = dict(decision="proposal", summary="Orden lógico", reason="Primeros pasos antes del acceso",
                    evidence="Fixtures locales", documents=[item("index.md", index),
                    item(REGISTER, bodies[REGISTER], sidebar_position=2)])
    return proposal, base


def apply(root, report):
    proposal, base = fixture(root)
    changes = GENERATOR.prepare_changes(root, GENERATOR.parse_proposal(json.dumps(proposal)))
    report.write_text(GENERATOR.render_agent_report(proposal, changes), encoding="utf-8")
    GENERATOR.apply_changes_atomically(changes)
    result = VALIDATOR.validate_repository(root, report, base)
    if not result["valid"]:
        raise AssertionError(result)
    return result


if __name__ == "__main__":
    apply(Path(sys.argv[1]), Path(sys.argv[2]))
