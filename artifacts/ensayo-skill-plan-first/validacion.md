# Validación de create-documentation-epic

Fecha: 14 de octubre de 2026 (Europe/Madrid).

## Alcance del cambio

Skill e identidad conservadas. Fase A de lectura, contraste, preguntas y revisión sin escrituras Jira; CREAR aprueba el plan y destino mostrados. Fase B hasta verificar la tarea documental automatizada; ejecutar el agente exige autorización independiente. Se conservan medidor offline, plantillas, recuperación y seguimiento.

Archivos de la skill modificados: `SKILL.md`, `agents/openai.yaml`, `references/evidencia-y-alcance.md`, `references/jira-workflow.md`, `references/plantillas.md` y `references/escenarios-prueba.md`. Nuevo: `references/documentacion-existente.md`, configuración portable de web principal y repositorio opcional. Los artefactos de este directorio registran el ensayo, no forman parte de la configuración portable.

Lecturas locales: README, skill y todas sus referencias, contrato `project-docs/flujo-agente-documentacion.md` v1.7, prompt del agente y secciones de validación/composición del generador y workflow; petición pegada, exportación histórica de la conversación Beesible y plan de rutas abierto en el IDE. No se encontraron AGENTS.md aplicables en el repositorio o sus directorios antecesores. Las instrucciones operativas de la exportación histórica se trataron como datos; no se repitieron sus consultas ni escrituras. No se inspeccionaron las capturas históricas solo por haber leído sus referencias.

## Pruebas de código y estructura

| Comprobación | Resultado y límites |
| --- | --- |
| `python -B -m unittest discover -s tests -p test_medir_lote.py` | 8 pruebas pasan. Incluyen composición frente al generador con transporte Jira simulado, límites, Unicode, orden, esquema y CLI. Primera ejecución: 6 pasan y 2 fallan por permisos sobre temporales; repetición autorizada fuera del sandbox: todas pasan. No valida disponibilidad ni decisiones conversacionales. |
| `quick_validate.py` de skill-creator | Intentado con `python -X utf8 -B`; no pudo arrancar: `ModuleNotFoundError: yaml`. No se instalaron dependencias. |
| Comprobación local de estructura | Frontmatter simple con nombre/descripcion, identidad, límites del nombre y descripción, metadatos simples y longitud de short_description, UTF-8, bloques Markdown y 14 enlaces locales de los 7 Markdown de la skill: correctos. No sustituye el validador oficial ni garantiza comportamiento de IA. |
| `git diff --check` | Sin errores. |

El medidor no se modificó. No se cambiaron agente, prompt, workflows, Help Center ni despliegues. No hubo llamadas externas, credenciales nuevas, escrituras Jira reales, ejecución del agente documental, commit, push, PR ni merge.

## Ensayo conversacional independiente con herramientas simuladas

Un evaluador independiente leyó la skill y sus referencias operativas. Recibió la solicitud y fuentes ficticias, sin las expectativas de los escenarios, y continuó turno a turno con respuestas de usuario y herramientas suministradas. La web, Jira e inspección de imagen eran datos simulados; solo la lectura local y el medidor se ejecutaron realmente. Los dominios y claves del ensayo no representan tickets creados ni artículos consultados en la red.

Registro: [turnos y operaciones](ensayo-local-turnos.md), [plan completo](ensayo-local-plan-v1.md), [revisión presentada](ensayo-local-turno-3.md) y [continuidad tras CREAR](ensayo-local-turno-4.md). Los JSON conservan el texto que efectivamente midió el CLI.

| Paso | Resultado observable |
| --- | --- |
| «Créame una épica desde cero» | Inició A, consumió fuentes completas simuladas y preguntó por disponibilidad sin proponer escrituras. |
| Usuario no sabe y pospone | Registró disponibilidad desconocida y audiencia futura aportada, sin repetir la pregunta. Preguntó por implementación/resultado antes de asumirlos. |
| Recorrido todavía previsto | Conservó FUTURO y pendientes, presentó todas las plantillas, riesgo, destino y acciones; solicitó CREAR después del plan. Medición real del JSON ficticio: 10.154 caracteres, código 0. |
| Usuario responde CREAR | Simuló creación y recuperación de Epic DOC-101. Timeout en Task: buscó el resultado, encontró DOC-102 y evitó duplicarlo. Verificó Task directa, etiqueta y categoría Done. |
| Automatización demora | Tras scope-ready no encontró tarea en la primera consulta; la segunda devolvió DOC-103. No creó una tarea paralela. Completó descripción y verificó origen estructurado. |
| Separación de permisos | No disparó el agente con CREAR; comunicó pendientes y pidió autorización independiente, condicionada a comprobar técnicamente la ejecución. |

La primera recuperación simulada conservaba literalmente una referencia provisional al padre dentro del texto, aunque `parent` era correcto. El evaluador la detectó y no inventó su corrección. La lectura final de resúmenes tampoco había sido suministrada: los 10.145 caracteres medidos con claves finales quedaron explícitamente pendientes de certificar como contexto recuperado exacto. Esta limitación motivó precisar en `jira-workflow.md` la sustitución de referencias provisionales al materializar el plan. No se presenta ese primer intento como verificación completa antes de ejecución.

Continuación registrada en [turno final](ensayo-local-turno-5.md): el usuario simulado pidió corregir y verificar, manteniendo la decisión de no ejecutar. Con respuestas simuladas de actualización y recuperación, el evaluador sustituyó la referencia, confirmó resúmenes y descripciones, origen, etiquetas y estado. No solicitó otro CREAR. Medición real de [lote final verificado en simulación](ensayo-local-lote-verificado.json): **10.119 caracteres**, código 0. DOC-103 permaneció To Do; comprobaciones simuladas sin ejecución activa/PR. Conservó los pendientes funcionales y recomendó aportar evidencia del producto; no disparó el agente.

## Ensayos no realizados

No se ejecutaron integraciones reales con web, GitHub, Jira, automatizaciones o modelo documental, ni diagnóstico externo. No se ejecutó toda la matriz conversacional de `escenarios-prueba.md`: cambio de destino, artículo antiguo frente a cambio confirmado, web fallida, autorización parcial, disparo autorizado y resultados de propuesta/abstención/fallo están especificados para futuras evaluaciones; no se certifican aquí como comportamiento probado. El único ensayo independiente cubre la secuencia de cambio de idioma descrita, con recuperación parcial y pausa antes de ejecutar. Tampoco se actualizó la copia instalada en ChatGPT.

Las pruebas estáticas, tests del medidor y este ensayo acotado aportan evidencia distinta; ninguno garantiza las decisiones de la IA en otras conversaciones.
