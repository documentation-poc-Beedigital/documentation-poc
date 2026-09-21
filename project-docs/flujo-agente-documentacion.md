---
article_id: ART-DOC-AGENT-001
title: Flujo del agente de documentación
version: 1.2
status: published
owner: Product
last_reviewed: 2026-09-02
---

# Flujo del agente de documentación

## Objetivo

El agente convierte una necesidad documental registrada en Jira en una propuesta revisable en GitHub. Automatiza el análisis y la preparación del cambio, pero mantiene la decisión de publicación en manos de los PM.

## Flujo completo

```mermaid
flowchart TD
    A["Cambio funcional registrado en Jira"] --> B["Creación de la tarea documental"]
    B --> C["Tarea en In Progress"]
    C --> D["Etiqueta documentation-agent-ready"]
    D --> E["Análisis del ticket y la documentación"]
    E --> F{"¿Hay una propuesta segura?"}
    F -->|Actualizar o crear| G["Rama, commit y pull request"]
    F -->|No| H["Abstención y revisión manual"]
    G --> I["Revisión de los PM"]
    I -->|Aprobada| J["Merge y documentación publicada"]
    I -->|Rechazada| K["Tarea de nuevo en In Progress"]
```

## Funcionamiento actual

Cuando una tarea con la etiqueta `documentation-task` pasa a **In Progress**, Jira añade automáticamente la etiqueta `documentation-agent-ready`.

La etiqueta inicia el workflow de GitHub Actions. El agente utiliza el ticket como evidencia de negocio, revisa la documentación existente y determina si debe actualizar artículos existentes, crear artículos nuevos dentro de categorías existentes del Centro de Ayuda o combinar ambas operaciones.

| Resultado del análisis | Acción automática | Decisión humana |
|---|---|---|
| Existe un documento aplicable | Propone actualizarlo y abre una única pull request para toda la propuesta | Un PM aprueba o rechaza la PR |
| No existe un documento aplicable, pero hay evidencia y categoría suficientes | Propone un artículo nuevo con metadatos deterministas y abre la misma pull request | Un PM aprueba o rechaza la PR |
| No puede decidir con seguridad entre crear o actualizar | Registra una abstención en Jira y no crea una PR | Se solicita revisión manual |
| El cambio es ambiguo o insuficiente | Registra una abstención en Jira y no crea una PR | Se aclara o completa el ticket |

## Controles

- La propuesta puede crear o actualizar uno o varios documentos Markdown y se aplica de forma atómica.
- El agente no inventa comportamiento, evidencia ni contenido ausente en el ticket.
- Los documentos nuevos solo se ubican en categorías existentes de `docs/centro-de-ayuda/`; el código determinista genera su frontmatter, identificador y versión inicial `1.0`.
- Una discrepancia con un snapshot se muestra como evidencia, pero el ticket validado sigue siendo la fuente de negocio para preparar la propuesta.
- El cambio se valida antes de crear la PR.
- El agente nunca aprueba ni fusiona la PR.
- Si cualquier operación falla, se restauran las actualizaciones y se eliminan las creaciones de esa ejecución.
- Si no puede proponer un cambio seguro, se abstiene y solicita revisión manual.

## Responsabilidades

| Componente | Responsabilidad |
|---|---|
| Jira | Registrar la necesidad, iniciar el proceso y mostrar el resultado |
| GitHub Actions | Orquestar el análisis, la validación y la publicación de la propuesta |
| Gemini | Analizar el ticket y proponer un cambio documental |
| Validador | Limitar el alcance y comprobar que la propuesta es segura y estructuralmente válida |
| PM | Revisar la pull request y decidir si se publica |

## Resultado esperado

El tiempo entre una necesidad de documentación y una propuesta revisable se reduce, mientras se conserva una aprobación humana explícita antes de publicar cualquier cambio.
