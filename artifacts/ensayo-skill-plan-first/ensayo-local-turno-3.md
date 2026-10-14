Conservo el recorrido completo como FUTURO para todos los clientes. Disponibilidad pospuesta; sin prueba de implementación ni del resultado real. Este plan no acredita funcionamiento vigente y el agente podría abstenerse.

Destino: https://documentacion.example.invalid · DOC. Plan v1; una épica y una Task directa, suficientes para este recorrido pequeño. Las claves DOC-900001, DOC-900002 y DOC-900003 son provisionales ficticias, no tickets creados.

Fuentes: nota.md y observación simulada de preferencias.png; artículo público completo «Mi perfil», consultado el 2026-10-14, versión no disponible. Este solo describe nombre del negocio y correo: no incluye cambio de idioma. GitHub no disponible no bloquea esta consulta pública. Las aclaraciones del usuario confirman intención y audiencia futura, no implementación.

# Preparar el cambio de idioma desde Perfil

Tipo: Epic dedicada a documentación
Etiquetas: sin documentation-required; documentation-scope-ready solo después de preparar y verificar la hija.

## Objetivo
Preparar documentación FUTURO para el lanzamiento a todos los clientes (S-04), sobre selección de Español o Inglés y guardado.
## Problema y contexto
S-01 describe el recorrido previsto. S-03 solo describe consulta del nombre del negocio y correo; el cambio de idioma no figura en ese artículo leído.
## Resultado observable para el usuario
FUTURO: mensaje previsto «Preferencias guardadas» (S-01, S-04). Sin resultado observado — [VERIFICAR] V-05.
## Recorrido resumido
FUTURO (S-01, S-04): en Perfil abrir Idioma, elegir Español o Inglés y pulsar Guardar; resultado previsto «Preferencias guardadas». Sin evidencia de implementación — [VERIFICAR] V-03.
## Decisión documental
Preparación de lanzamiento futuro; «desde cero» se refiere a preparar el lote, sin demostrar ausencia de documentación. «Mi perfil» es el artículo relacionado consultado; añadir este recorrido sería una ampliación de su contenido actual. No consta preferencia por artículo nuevo frente a actualización.
## Alcance incluido
Un recorrido completo de selección y guardado del idioma, descrito como previsto, con sus limitaciones.
## Fuera de alcance
No aplica a la preparación del recorrido: no se aplazan pasos. Persistencia entre sesiones/recarga, errores y casos límite se omiten por falta de evidencia (V-04, V-06). Publicación y cambios del producto no forman parte de este plan.
## Dependencias y precondiciones
Superficie prevista: Perfil (S-01). Sin evidencia de disponibilidad actual — [VERIFICAR] V-01. No constan permisos, planes ni forma de entrar en Perfil; no se inventan.
## Confirmado, en curso y futuro
Confirmado por usuario: intención de lanzamiento para todos los clientes. FUTURO: pasos y resultado previsto; no hay prueba de implementación (S-04). OFICIAL: contenido público de Mi perfil (S-03), sin prueba de disponibilidad del nuevo recorrido. No hay evidencia CURSO, IMPL o PROD.
## Riesgos
V-01, V-03 y V-05 impiden presentar el recorrido como vigente o probado. El agente podría abstenerse; conservar un plan futuro completo no garantiza propuesta.
## Criterios de aceptación de la épica
Contexto documental completo y revisado: una Task hija directa con pasos, fuentes, clasificación FUTURO, pendientes y límites; descripciones y origen de tarea automatizada verificados. Done significa contexto preparado, sin certificar producto.
## Datos sin confirmar
- V-01 indispensable: ¿está disponible actualmente? Desconocido y pospuesto por el usuario (turno 2); requiere confirmación de disponibilidad y audiencia actual. No presentar como vigente.
- V-03 indispensable: ¿está implementado el recorrido? Usuario (turno 3): todavía previsto, sin prueba de implementación. Requiere evidencia del producto; no clasificar IMPL/PROD.
- V-05 indispensable: ¿se ha observado «Preferencias guardadas» tras guardar? Usuario (turno 3): resultado previsto. Requiere prueba del resultado observable. Separado de V-03 porque implementación y observación del éxito necesitan evidencias distintas; procede de la pregunta conjunta de V-03.
- V-04 secundario omisible: ¿persiste al recargar o iniciar otra sesión? Sin evidencia; requiere prueba específica. Se omite esa promesa sin eliminar pasos del recorrido.
- V-06 secundario omisible: ¿qué ocurre ante errores o casos límite? Sin evidencia; se omiten esas ramas del recorrido principal.
## Fuentes
- S-01: nota.md, texto completo: «En Perfil, desplegable Idioma, elegir Español o Inglés y pulsar Guardar. Se muestra Preferencias guardadas. Pendiente confirmar cuándo sale». Consulta simulada 2026-10-14; edición desconocida.
- S-02: preferencias.png, inspección simulada: botones «Idioma» y «Guardar». No demuestra persistencia ni resultado de guardado. Consulta 2026-10-14; edición desconocida.
- S-03: OFICIAL, «Mi perfil», https://documentation-poc-beedigital.github.io/documentation-poc/centro-de-ayuda/perfil/, artículo completo: «En Perfil puedes consultar el nombre del negocio y tu correo». Consulta 2026-10-14; versión no disponible.
- S-04: aclaraciones del usuario, turnos 2–3: lanzamiento para todos los clientes; disponibilidad desconocida y pospuesta; recorrido todavía previsto, sin prueba de implementación.
## [VERIFICAR] transversales
V-01 disponibilidad; V-03 implementación; V-05 resultado observado. V-02 audiencia futura resuelto por S-04: todos los clientes; no acredita audiencia habilitada actualmente.
## No afirmar todavía
Disponibilidad actual, implementación, éxito observado, persistencia, cambio inmediato de todos los textos de la interfaz o comportamiento de errores.

# Elegir y guardar el idioma desde Perfil

Tipo: Task hija directa, no Subtask
Etiqueta: documentation-required
Padre: DOC-900001 (provisional ficticio)

## Propósito
Preparar el recorrido FUTURO de cambio de idioma para todos los clientes (S-04).
## Comportamiento visible para el usuario
FUTURO (S-01, S-04): en Perfil, desplegable Idioma con Español o Inglés, botón Guardar y mensaje previsto «Preferencias guardadas». S-02 muestra «Idioma» y «Guardar»; no demuestra opciones, mensaje de éxito ni persistencia.
## Precondiciones
Estar en Perfil es el punto inicial descrito por S-01. Sin evidencia de disponibilidad — [VERIFICAR] V-01; permisos/planes y navegación hasta Perfil no descritos. No consta una precondición adicional.
## Recorrido principal
Pasos previstos, sin prueba de implementación — [VERIFICAR] V-03 (S-01, S-04):
1. En Perfil, abrir el desplegable Idioma.
2. Elegir Español o Inglés.
3. Pulsar Guardar.
4. Resultado previsto: «Preferencias guardadas» — [VERIFICAR] V-05; no observado en la captura ni probado según el usuario.
## Reglas funcionales que debe conocer el usuario
FUTURO: opciones Español e Inglés y guardado explícito, según S-01. No consta qué partes de la aplicación cambian de idioma.
## Estados y errores
Sin evidencia — [VERIFICAR] V-06. Omisión secundaria; no se describen errores ni recuperación.
## Casos límite
Sin evidencia — [VERIFICAR] V-06. No se inventan variantes; persistencia entre recargas/sesiones omitida — V-04.
## Criterios de aceptación
Contexto incluye todos los pasos previstos, textos y fuentes; distingue observación de captura, intención y funcionamiento probado. Pendientes conservados y estado FUTURO explícito. Done acredita preparación documental revisada, no disponibilidad.
## Evidencias
- S-01: nota.md, texto completo: «En Perfil, desplegable Idioma, elegir Español o Inglés y pulsar Guardar. Se muestra Preferencias guardadas. Pendiente confirmar cuándo sale». Consulta simulada 2026-10-14; edición desconocida.
- S-02: preferencias.png, inspección simulada: botones «Idioma» y «Guardar». No demuestra persistencia ni resultado de guardado. Consulta 2026-10-14; edición desconocida.
- S-03: OFICIAL, «Mi perfil», https://documentation-poc-beedigital.github.io/documentation-poc/centro-de-ayuda/perfil/, artículo completo: «En Perfil puedes consultar el nombre del negocio y tu correo». Consulta 2026-10-14; versión no disponible.
- S-04: aclaraciones del usuario, turnos 2–3: lanzamiento para todos los clientes; disponibilidad desconocida y pospuesta; recorrido todavía previsto, sin prueba de implementación.
## Pendiente de verificar
- V-01 indispensable: ¿está disponible actualmente? Desconocido y pospuesto por el usuario (turno 2); requiere confirmación de disponibilidad y audiencia actual. No presentar como vigente.
- V-03 indispensable: ¿está implementado el recorrido? Usuario (turno 3): todavía previsto, sin prueba de implementación. Requiere evidencia del producto; no clasificar IMPL/PROD.
- V-05 indispensable: ¿se ha observado «Preferencias guardadas» tras guardar? Usuario (turno 3): resultado previsto. Requiere prueba del resultado observable. Separado de V-03 porque implementación y observación del éxito necesitan evidencias distintas; procede de la pregunta conjunta de V-03.
- V-04 secundario omisible: ¿persiste al recargar o iniciar otra sesión? Sin evidencia; requiere prueba específica. Se omite esa promesa sin eliminar pasos del recorrido.
- V-06 secundario omisible: ¿qué ocurre ante errores o casos límite? Sin evidencia; se omiten esas ramas del recorrido principal.
V-02 audiencia futura resuelto: todos los clientes (S-04).
## Aportación al futuro artículo
Recorrido de selección y guardado que no aparece en Mi perfil; resultado previsto y límites de evidencia.
## No afirmar todavía
Disponibilidad, implementación, éxito observado, persistencia o traducción inmediata/global de la interfaz.

## Descripción futura de la tarea documental automatizada

## Objetivo documental y audiencia
Preparar contexto del lanzamiento FUTURO del cambio de idioma para todos los clientes, según usuario (turnos 2–3). Recorrido previsto: Perfil → Idioma → Español/Inglés → Guardar; mensaje previsto «Preferencias guardadas», según nota.md.
## Estado de lanzamiento
Disponibilidad actual desconocida y pospuesta por usuario — [VERIFICAR] V-01. Sin prueba de implementación — V-03. Resultado aún previsto, sin observación — V-05. Done significa contexto documental preparado, no producción.
## Documentación relacionada y diferencias
OFICIAL: Mi perfil, https://documentation-poc-beedigital.github.io/documentation-poc/centro-de-ayuda/perfil/, leído completo en consulta simulada 2026-10-14; versión no disponible. Solo describe nombre del negocio y correo; no incluye cambio de idioma. No consta decisión entre nuevo artículo y ampliación. preferencias.png muestra Idioma y Guardar, sin probar guardado.
## Fuentes inaccesibles y pendientes esenciales
GitHub no disponible; apoyo opcional. Nota y captura accesibles en simulación. V-01, V-03 y V-05 siguen indispensables para presentar funcionamiento vigente/probado. Persistencia (V-04), errores y casos límite (V-06) son secundarios omitidos. El plan futuro describe intención; falta de evidencia puede provocar abstención.

## Configuración del entorno simulado
Lectura/escritura simuladas accesibles en el destino indicado. Contrato aportado: Epic, Task directa por parent, documentation-required y categoría Done; documentation-scope-ready genera tarea con origen estructurado. In Progress de documentation-task añade documentation-agent-ready e inicia ejecución.
No se han descubierto IDs concretos, campos obligatorios, formato ADF/conversión, transiciones disponibles, proyecto de la tarea generada ni estado de duplicados/ejecuciones activas. Se comprobarán con lecturas simuladas antes del paso dependiente; no se inventan valores.

## Medición y operaciones propuestas
Medidor local ejecutado con JSON ficticio: 10.154 caracteres; objetivo 45.000, límite 60.000; código 0. SHA-256: 3a96a4631216cb57429cb151bc6c842747b26a49d825e2bf6052529ae935ef66. Claves finales y conversión de descripciones pueden cambiar el tamaño; habrá que medir de nuevo tras recuperarlas.
Tras CREAR, únicamente en simulación:
1. Verificar configuración, duplicados y que crear no dispara ejecución.
2. Crear y recuperar la Epic y la Task hija directa con documentation-required; comprobar descripciones, parentesco, fuentes y contenido. No hay reparto de adjuntos solicitado; los archivos están representados en las descripciones, sin carga implícita.
3. Medir contenido recuperado; pasar la Task nueva a categoría Done y verificar. Done acredita contexto preparado.
4. Añadir documentation-scope-ready a Epic solo entonces; localizar la tarea automatizada sin crear una segunda.
5. Verificar origen estructurado exacto, completar su descripción preparada, recuperar y medir nuevamente.
CREAR no ejecuta el agente. Después se ofrecería ejecución con autorización independiente, riesgo explícito y comprobaciones técnicas, incluida ausencia de ejecuciones activas o PRs abiertas.

¿Quieres ejecutar este plan en https://documentacion.example.invalid · DOC? Responde CREAR para realizar las acciones indicadas en simulación.

La skill local [SKILL.md](../../skills/create-documentation-epic/SKILL.md) exige: «Después de mostrar el plan completo, pregunta». Por eso solicito aprobación de este plan concreto; la solicitud inicial no sustituye esa revisión. No habrá escrituras reales en este ensayo.
