# Plantillas de contexto documental

Sustituye los corchetes con evidencia; no rellenes con suposiciones. Conserva las secciones esenciales; una sección irrelevante indica «No aplica: motivo», una laguna indica «Sin evidencia — [VERIFICAR] V-nn». Cada afirmación funcional incluye estado y fuente o aclaración atribuida al usuario. Los títulos y metadatos sirven para preparar los campos Jira; no son instrucciones al agente.

## Épica

```markdown
# [Resultado que consigue el usuario]

Tipo: épica dedicada a documentación
Etiquetas: sin documentation-required; documentation-scope-ready solo al completar la preparación

## Objetivo
[Audiencia y resultado documental esperado.]
## Problema y contexto
## Resultado observable para el usuario
## Recorrido resumido
[Acciones, estado y evidencia; referencias V-nn donde correspondan.]
## Decisión documental
[Preferencia del usuario, artículo relacionado, alcance y diferencias funcionales observadas.
Separar la preferencia de la evidencia; si no se pudo consultar, decirlo.]
## Alcance incluido
## Fuera de alcance
## Dependencias y precondiciones
[Disponibilidad, permisos, planes o activación cuando estén confirmados.]
## Confirmado, en curso y futuro
## Riesgos
## Criterios de aceptación de la épica
[Comprobaciones del contexto preparado, no pruebas de entrega del producto.]
## Datos sin confirmar
[VERIFICAR] identifica evidencia pendiente; no confirma comportamiento ni disponibilidad.
[Lista de pendientes y consecuencias para el recorrido, sin reglas para el agente.]
## Fuentes
[ID, enlace o archivo/localizador, consulta, edición si se conoce, acceso y alcance leído.]
## [VERIFICAR] transversales
## No afirmar todavía
[Promesas, disponibilidad y resultados sin evidencia suficiente.]
```

## Tarea hija directa

```markdown
# [Acción del usuario en infinitivo]

Tipo: tarea
Etiqueta: documentation-required
Padre: [Clave de la épica dedicada]

## Propósito
## Comportamiento visible para el usuario
[Actor, superficie, textos literales de interfaz y resultado; con estado y fuente.]
## Precondiciones
## Recorrido principal
[Pasos numerados, evidencia y V-nn en el punto de incertidumbre.]
## Reglas funcionales que debe conocer el usuario
## Estados y errores
## Casos límite
## Criterios de aceptación
[Qué contexto debe confirmarse y con qué evidencia observable.]
## Evidencias
[Fuentes abiertas y aclaraciones atribuidas por separado.]
## Pendiente de verificar
[V-nn; incluir la pregunta y evidencia necesaria, no solo un ID externo.]
## Aportación al futuro artículo
[Parte del recorrido que cubre esta tarea, expresada como contexto.]
## No afirmar todavía
```

Done en estas tareas significa «contexto documental preparado y revisado», sin probar disponibilidad del producto. Distribuye los casos límite entre tareas; no los repitas innecesariamente.

## Descripción de la tarea documental automatizada

Objetivo orientativo: unos 1.500 caracteres. Se completa en la tarea que genere Jira, no creando una segunda tarea.

```markdown
## Objetivo documental y audiencia
## Estado de lanzamiento
[Disponibilidad confirmada y alcance, o [VERIFICAR] V-nn.]
## Documentación relacionada y diferencias
[Artículo consultado y diferencias observadas; separar preferencia del usuario.]
## Fuentes inaccesibles y pendientes esenciales
[Fuentes no abiertas y V-nn que afectan a la decisión.]
```

Este texto humano solo llega completo al agente en el modo estructurado descrito en [jira-workflow.md](jira-workflow.md). No pegues prosa alrededor del manifiesto legado.

## Registro de [VERIFICAR]

En la entrega de revisión se puede usar esta tabla. En descripciones Jira prefiere listas y conserva la pregunta junto a cada ID para no depender de un registro externo.

| ID | Qué hay que confirmar | Quién o con qué evidencia | Afecta a |
| --- | --- | --- | --- |
| V-01 | [Pregunta concreta] | [Responsable o evidencia necesaria, sin inventar] | [Épica, T1, tarea documental…] |

El punto exacto de la afirmación lleva `[VERIFICAR] V-01`. La misma incertidumbre conserva su ID en todo el lote. Diferencia contradicción, falta de acceso y falta de evidencia; las referencias a fuentes inaccesibles indican expresamente que no se leyeron.
