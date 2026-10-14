# Ensayo conversacional independiente

## Condiciones

Solo se utilizan los datos y respuestas de herramientas simulados aportados por el coordinador. No hay llamadas externas ni escrituras reales en Jira. La skill y sus cinco referencias operativas se han leído localmente. No se modifica la skill ni el agente.

## Turno 1 — Entrada simulada

Usuario: «Créame una épica documental desde cero para cambiar el idioma. Destino https://documentacion.example.invalid proyecto DOC».

Fuentes simuladas leídas:
- S-01: nota.md, texto íntegro: «En Perfil, desplegable Idioma, elegir Español o Inglés y pulsar Guardar. Se muestra Preferencias guardadas. Pendiente confirmar cuándo sale». Consulta 2026-10-14; edición desconocida.
- S-02: preferencias.png, observación aportada de herramienta de imagen: botones Idioma y Guardar. Sin evidencia de persistencia. Consulta 2026-10-14; edición desconocida.
- S-03: artículo público completo «Mi perfil», https://documentation-poc-beedigital.github.io/documentation-poc/centro-de-ayuda/perfil/, texto: «En Perfil puedes consultar el nombre del negocio y tu correo». Consulta 2026-10-14; versión/edición no disponible. Documentación pública OFICIAL; no confirma disponibilidad del cambio de idioma.
- S-04: contrato Jira simulado: Epic, Task hija directa mediante parent, documentation-required y Done; scope-ready genera tarea con origen estructurado; In Progress de documentation-task añade agent-ready e inicia ejecución. Lectura y escritura simuladas accesibles en el destino elegido. GitHub no disponible; apoyo opcional.

## Turno 1 — Respuesta del asistente

Estoy usando la skill create-documentation-epic para preparar primero el plan y revisarlo contigo. El destino será https://documentacion.example.invalid · DOC.

La nota describe el cambio de idioma y el mensaje «Preferencias guardadas». La captura muestra «Idioma» y «Guardar», pero no demuestra que el cambio se conserve. El artículo público «Mi perfil» solo explica cómo consultar el nombre del negocio y el correo; no incluye este recorrido.

¿El cambio de idioma ya está disponible para clientes o estamos preparando un lanzamiento futuro?

## Registro tras el turno 1

- Fase A, recogida y contraste. Plan completo aún no presentado; versión de preparación 0.
- Destino aportado por el usuario: https://documentacion.example.invalid · DOC.
- Alcance inicial: cambiar el idioma desde Perfil. No se interpreta «desde cero» como prueba de ausencia de artículo ni como elección de artículo nuevo.
- V-01 indispensable: disponibilidad actual o preparación futura. Pendiente; pregunta formulada. S-01 deja sin confirmar cuándo sale; S-02 y S-03 no resuelven disponibilidad.
- V-02 indispensable: audiencia para la disponibilidad o lanzamiento. Pendiente; pregunta diferida hasta responder V-01.
- V-03 indispensable para describir resultado como observado: implementación y mensaje de éxito efectivamente observados frente a especificación prevista. Pendiente; S-01 describe el resultado, S-02 no lo demuestra. Se reevaluará con la respuesta de V-01.
- V-04 secundario omisible para un recorrido limitado a selección y guardado: persistencia tras recarga o nueva sesión. Sin evidencia; no afirmar persistencia.
- Errores y casos límite sin evidencia: secundarios omisibles para el recorrido principal, sujeto al alcance acordado.
- Operaciones completadas: lectura local de skill y referencias; consumo de respuestas simuladas de fuentes y contrato; comparación de documentación.
- Operaciones externas/reales: ninguna. Tickets, claves y adjuntos Jira: ninguno.
- Autorización: preparar plan y ensayar con simulación. Sin aprobación CREAR de un plan revisado ni autorización independiente para ejecutar agente.
- Próxima operación: registrar respuesta a V-01 y preguntar por el siguiente indispensable que siga sin responder. Sin escrituras simuladas hasta revisar y aprobar el plan completo.

## Turno 2 — Respuesta del usuario simulada

«No sé si ya está disponible y prefiero posponer esa confirmación. Preparamos el lanzamiento para todos los clientes. Mantén el recorrido completo y señala el riesgo».

## Turno 2 — Respuesta del asistente

Prepararé el recorrido completo como documentación de un lanzamiento FUTURO para todos los clientes, según tu aclaración. La disponibilidad actual queda pendiente, sin volver a pedirte esa confirmación. Los pasos de la nota servirán como recorrido previsto; no podemos presentarlos todavía como funcionamiento vigente. El agente podría abstenerse si falta evidencia del producto, incluso con un plan completo.

¿Se ha probado ya el recorrido de elegir Español o Inglés y pulsar «Guardar», viendo «Preferencias guardadas», o ese resultado es todavía lo previsto?

## Registro tras el turno 2

- Fase A, recogida y contraste. Preparación versión 0; no se ha presentado el plan completo.
- Alcance mantenido por el usuario: recorrido completo de cambio de idioma; preparación de lanzamiento FUTURO para todos los clientes.
- V-01 indispensable: disponibilidad actual desconocida y pospuesta expresamente por el usuario en el turno 2. Sigue pendiente; no repetir la pregunta sin nueva evidencia. Consecuencia: no afirmar disponibilidad vigente.
- V-02: audiencia futura confirmada por aclaración del usuario en el turno 2: todos los clientes. No confirma audiencia actualmente habilitada.
- V-03 indispensable: prueba de implementación y resultado de guardado, frente a recorrido previsto. Pregunta formulada en este turno. No se ha clasificado el producto como IMPL ni PROD. La nota y captura no confirman por sí mismas la implementación ni el mensaje efectivamente observado.
- V-04 secundario omisible: persistencia tras recarga/nueva sesión, sin evidencia. Mantener el recorrido principal y no prometer esta persistencia no reduce los pasos acordados.
- Riesgo comunicado: un recorrido FUTURO suficientemente descrito puede preparar el contexto, pero no confirma funcionamiento ni garantiza propuesta del agente.
- Herramienta de archivos simulada: no aporta datos adicionales.
- Autorizaciones: mantener alcance y preparar futuro con disponibilidad pendiente. No hay aprobación CREAR ni autorización de ejecución independiente.
- Operaciones Jira reales o simuladas: ninguna.
- Siguiente paso: registrar la respuesta de V-03, conservar cualquier limitación que el usuario no pueda resolver y presentar el plan completo con medición local y acciones explícitas para su revisión.

## Turno 3 — Respuesta del usuario simulada

«Es todavía lo previsto; no tenemos prueba de implementación. Sigue con el plan futuro completo y conserva esos pendientes».

## Turno 3 — Respuesta y artefactos

Respuesta conversacional completa: ensayo-local-turno-3.md; plan v1: ensayo-local-plan-v1.md; lote ficticio medido: ensayo-local-lote-v1.json.

- Fase A, revisión del plan v1. Se presenta Epic, una Task hija directa y descripción futura de la tarea documental automatizada, con todas las secciones de plantilla.
- V-03 se conserva como implementación sin evidencia; V-05 separa resultado observado, todavía previsto según turno 3. Ambos proceden de la pregunta de turno 2 y no se consideran resueltos por preparar futuro.
- V-01 disponibilidad desconocida/pospuesta; V-02 audiencia futura confirmada; V-04 persistencia omitida; V-06 errores/casos límite secundarios omitidos.
- Alcance completo previsto mantenido. No se promete propuesta ni se presenta como funcionalidad vigente.
- Medición: primer comando tuvo ruta relativa incorrecta y devolvió FileNotFoundError; no se consideró medición. Ruta corregida, medidor local python -B ejecutado: 10154 caracteres, exit_code 0, SHA-256 3a96a4631216cb57429cb151bc6c842747b26a49d825e2bf6052529ae935ef66. Sin tests ni llamadas externas.
- Configuración aportada distinguida de IDs/campos/estados concretos sin consultar; no se han inventado lecturas ni tickets.
- Se solicita CREAR para este plan y destino, con operaciones simuladas completas y distinción de ejecución independiente.
- Autorizaciones vigentes: preparar y revisar plan FUTURO; sin escrituras Jira reales o simuladas ni ejecución de agente.
- Próximo paso: respuesta a revisión. Tras CREAR se requerirán resultados simulados de lecturas y escrituras para verificar cada paso; no se afirmará creación sin respuesta de herramienta.

## Turno 4 — Usuario y fase B simulada

Usuario: «CREAR». Autorización de preparar plan v1 en https://documentacion.example.invalid · DOC; no autoriza agente. Ninguna operación externa real.

Resultados suministrados y progreso, en orden:
1. Configuración verificada: Epic/Task, parent, Markdown sin pérdidas, transición Completar a Done, origen estructurado y disparador In Progress.
2. Duplicados: búsqueda vacía.
3. Crear Epic devuelve DOC-101; recuperación confirma descripción exacta v1. Clave conservada.
4. Crear Task da timeout. Se consulta antes de repetir: DOC-102 existe, parent DOC-101, descripción v1 íntegra, documentation-required. No se repite la creación. Lectura posterior confirma Task y etiqueta.
5. Completar devuelve éxito; lectura confirma statusCategory.key=done. Pendientes funcionales conservados.
6. Actualizar documentation-scope-ready en Epic devuelve éxito; lectura confirma etiqueta.
7. Primera búsqueda de tarea automatizada vacía. Segunda consulta acotada devuelve DOC-103, documentation-task, jira_epic_key=DOC-101, jira_task_keys=DOC-102, entrada estructurada, descripción vacía. No se crea otra.
8. Completar descripción humana preparada devuelve éxito; recuperación confirma contenido íntegro y campos de origen conservados. Se conserva orden exacto de una única tarea.
9. Medidor local ejecutado sobre JSON ficticio con claves finales y textos confirmados: 10145 caracteres, exit_code 0, SHA-256 b5db7d416bcc0284d50e77c148894daf78ae59145f7b0db6fece98b13fe8630d. No se ha inventado lectura final de resúmenes: quedan los del plan; la medición exacta del contexto recuperado requiere confirmarlos. No se afirmó una medición intermedia histórica antes de Done; no estaba suministrada.

Pendientes técnicos explícitos:
- No se suministraron lecturas para descartar ejecución activa/PR abierta; no disparar.
- La descripción exacta v1 de Task conserva «Padre: DOC-900001 (provisional ficticio)» mientras el campo parent real confirmado es DOC-101. Se propone sustituir el texto, recuperar y medir; no se inventó escritura/corrección ni su resultado.
- No hay lectura final de resúmenes; conservar tamaño medido como lote de claves finales, pendiente certificación exacta del contexto recuperado.
- No se suministró lectura del estado inicial de DOC-103 ni consulta de transiciones disponibles en esa tarea concreta; contrato general verificado no sustituye esos datos antes del disparo.
- No hay inventario de adjuntos porque el usuario no solicitó cargarlos; contexto de imagen conservado en descripciones.

Fase B: preparación simulada completada hasta descripción automatizada; comprobaciones adicionales antes de ejecución pendientes. Turno conversacional completo en ensayo-local-turno-4.md. Se ofrece ejecución con permiso independiente, expresamente condicionada a verificaciones técnicas, con riesgo FUTURO y recomendación de evidencia. No se ejecuta agente ni se modifica automatización. Próximo paso: autorización independiente si el usuario quiere ejecutar y respuestas simuladas de las comprobaciones pendientes; mantener claves y no duplicar.

## Turno 5 — Corrección y verificación final

Usuario simulado: «No ejecutes el agente todavía. Corrige las referencias provisionales que encontraste y termina la verificación del contexto aprobado».

Operaciones exclusivamente simuladas y resultados aportados:
1. Actualizar DOC-102 sustituyendo únicamente «Padre: DOC-900001 (provisional ficticio)» por «Padre: DOC-101»: éxito. Recuperación confirma descripción íntegra sin otro cambio, parent DOC-101, tipo Task, documentation-required y categoría done. Se reutiliza el ticket y autorización vigente del plan; no se solicita otro CREAR.
2. Recuperar DOC-101, DOC-102 y DOC-103: mismos resúmenes del plan v1 y descripciones íntegras con la única sustitución de Task; etiquetas verificadas, origen DOC-101/DOC-102 conservado.
3. Leer DOC-103: To Do, transición In Progress disponible y sin ejecutar.
4. Consultar ejecuciones activas/PRs: vacío. Solo válido para la comprobación actual; antes de una futura ejecución habrá que consultar de nuevo.
5. Medición local del lote íntegro corregido y recuperado: ensayo-local-lote-verificado.json, 10119 caracteres, objetivo 45000, límite técnico 60000, exit_code 0, SHA-256 5e980f8987bebc40af25f75603658d92843bbca750d57e25ccf28faf13998388. Confirmados ahora resúmenes y textos; se cierra la limitación de la medición anterior.

Estado final de preparación: fase B completada y verificada en simulación, plan v1 con corrección de clave provisional dentro de su autorización. Claves: DOC-101 Epic, DOC-102 hija preparada Done, DOC-103 documentación automatizada To Do. Pendientes técnicos anteriores cerrados con las respuestas aportadas; pendientes funcionales V-01, V-03 y V-05 conservados. V-02 audiencia futura resuelto, V-04 persistencia y V-06 errores/casos límite secundarios omitidos.

Autorización vigente: preparación y corrección del contexto aprobado. Decisión expresa de no ejecutar todavía respetada; no se vuelve a preguntar por ejecución en este turno ni se dispara agente. No hubo llamadas externas ni escrituras Jira reales.

Respuesta completa en ensayo-local-turno-5.md. Siguiente paso recomendado: aportar prueba del producto y completar el contexto existente. Para retomar una ejecución futura: revisar riesgo, obtener permiso independiente y comprobar nuevamente intento activo/PR. Se conservan claves y artefactos sin duplicados.
