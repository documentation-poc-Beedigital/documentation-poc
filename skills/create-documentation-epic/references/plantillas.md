# Plantillas de contexto documental

Lee estas plantillas antes de redactar. Sustituye los corchetes con evidencia; no rellenes con suposiciones. Presenta la épica y cada tarea con todos sus encabezados, también en el borrador del chat. Una sección irrelevante indica «No aplica: motivo», una laguna indica «Sin evidencia — [VERIFICAR] V-nn». Cada afirmación funcional incluye estado (PROD, IMPL, CURSO, FUTURO, OFICIAL o POC) y fuente o aclaración atribuida al usuario. Conserva también evidencia y pendientes de partes aplazadas. Los títulos y metadatos sirven para preparar los campos Jira; no son instrucciones al agente.

## Épica

```markdown
# [Resultado que consigue el usuario]

Tipo: épica dedicada a documentación
Etiquetas: sin documentation-required; documentation-scope-ready solo al completar la preparación

## Objetivo
[Audiencia y resultado documental esperado; actualización vigente o preparación de lanzamiento futuro.]
## Problema y contexto
## Resultado observable para el usuario
## Recorrido resumido
[Acciones, estado y evidencia; referencias V-nn donde correspondan.
En FUTURO son pasos y resultados previstos, no funcionamiento observado o implementado.]
## Decisión documental
[Preferencia del usuario, artículo relacionado, alcance y diferencias funcionales observadas.
Separar la preferencia de la evidencia; si no se pudo consultar, decirlo.]
## Alcance incluido
## Fuera de alcance
[Partes excluidas o aplazadas, motivo y pendientes conservados; no excluir silenciosamente.]
## Dependencias y precondiciones
[Disponibilidad, permisos, planes o activación cuando estén confirmados.]
## Confirmado, en curso y futuro
[Separar detalle del plan, decisiones de lanzamiento y confirmación de implementación o producción.]
## Riesgos
[Riesgos restantes también tras reducir el alcance; la reducción no garantiza propuesta.]
## Criterios de aceptación de la épica
[Comprobaciones del contexto preparado, no pruebas de entrega del producto.]
## Datos sin confirmar
[VERIFICAR] identifica evidencia pendiente; no confirma comportamiento ni disponibilidad.
[V-nn por pregunta con evidencia de resolución propia; clase indispensable/secundaria/fuera de alcance, motivo y consecuencias
para el recorrido; respuesta y procedencia si existen. Sin reglas para el agente.]
## Fuentes
[ID, enlace o archivo/localizador, consulta, edición si se conoce, acceso y alcance leído.]
## [VERIFICAR] transversales
## No afirmar todavía
[Promesas, disponibilidad y resultados sin evidencia suficiente.]
```

## Tarea hija directa

```markdown
# [Acción del usuario en infinitivo]

Tipo: Task (tarea hija directa, no Subtask)
Etiqueta: documentation-required
Padre: [Clave de la épica dedicada]

## Propósito
## Comportamiento visible para el usuario
[Actor, superficie, textos literales de interfaz y resultado; con estado y fuente.
Observaciones de capturas con nombre/localizador, separadas de inferencias.]
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
[V-nn, clase y efecto en este recorrido; incluir pregunta y evidencia necesaria,
respuesta y procedencia o estado pendiente, no solo un ID externo.]
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
[Disponibilidad confirmada y audiencia, o Sin evidencia — [VERIFICAR] V-nn.
Distinguir lanzamiento futuro y recorrido vigente; Done no confirma producción.]
## Documentación relacionada y diferencias
[Artículo consultado y diferencias observadas; separar preferencia del usuario.]
## Fuentes inaccesibles y pendientes esenciales
[Fuentes no abiertas, pendientes indispensables y secundarios omisibles, con efecto
en el alcance. La falta de consulta no ordena abstenerse: el agente revisa el repositorio.]
```

Este texto humano solo llega completo al agente en el modo estructurado descrito en [jira-workflow.md](jira-workflow.md). No pegues prosa alrededor del manifiesto legado.

## Registro de [VERIFICAR]

En la entrega de revisión se puede usar esta tabla. En descripciones Jira prefiere listas y conserva la pregunta junto a cada ID para no depender de un registro externo.

| ID | Pregunta y clase | Motivo y efecto en el alcance | Fuentes o evidencia necesaria | Respuesta, procedencia y estado | Afecta a |
| --- | --- | --- | --- | --- | --- |
| V-01 | [Pregunta; indispensable/secundario/fuera de alcance] | [Qué impide u omite] | [Fuentes en conflicto o evidencia necesaria, sin inventar] | [Pendiente o respuesta atribuida con fecha/localizador] | [Épica, T1, tarea documental…] |

El punto exacto de la afirmación lleva `[VERIFICAR] V-01`. La misma incertidumbre conserva su ID en todo el lote. Diferencia contradicción, falta de acceso y falta de evidencia; las referencias a fuentes inaccesibles indican expresamente que no se leyeron.

Separa los pendientes que requieren evidencias diferentes, conservando la relación con el ID anterior si estaba agrupado. Distingue el resultado esperado descrito en un plan FUTURO de la evidencia de implementación o del resultado observado: preparar documentación futura no confirma funcionamiento vigente.

Un «no lo sé» conserva el pendiente. Una autorización CREAR se registra como permiso de operación, nunca como respuesta funcional. La clasificación sigue [evidencia-y-alcance.md](evidencia-y-alcance.md); mantener todos los encabezados no obliga a inventar errores ni convierte cada sección sin evidencia en indispensable.
