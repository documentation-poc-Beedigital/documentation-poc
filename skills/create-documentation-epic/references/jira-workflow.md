# Contrato de integración Jira

## Contrato observado y configuración portable

Referencia local revisada: `project-docs/flujo-agente-documentacion.md` v1.8, `.github/prompts/documentation-agent-poc.md`, `.github/scripts/generate-documentation-proposal.py` y `.github/workflows/documentation-agent-poc.yml`. Estos archivos pertenecen al repositorio anfitrión, no al paquete portable. En otro entorno descubre y verifica el contrato equivalente antes de escribir. No copies secretos ni rutas personales.

El agente consume descripciones, no comentarios ni campos de negocio adicionales. Exige una fuente de tipo Epic (el generador actual comprueba el nombre `epic` sin distinguir mayúsculas), hijas directas mediante `parent`, etiqueta `documentation-required` y `statusCategory.key=done`. No presupongas que un tipo traducido es compatible. La tarea documental puede pertenecer a otro proyecto y no necesita ser hija de la épica.

Prepara este mapa con valores descubiertos o aportados, indicando «sin verificar» cuando corresponda:

- Herramientas autorizadas de lectura y escritura, tenant/base URL y proyecto de destino de la épica, con procedencia de la configuración o elección del usuario y autorización. El sitio/proyecto de las fuentes no determina el destino.
- Proyecto de la tarea documental y regla existente que la genera.
- Tipos Epic y Task (no Subtask) y campos obligatorios, campo de parentesco y formato de descripción (ADF o conversión del conector).
- Estados de categoría Done y transiciones válidas desde el estado inicial.
- Mapeo de origen hacia `jira_epic_key` y `jira_task_keys`, campos/IDs que usa la regla y su orden de tareas.
- Disparador existente, transición válida y cómo comprobar ejecución activa o PR abierta.

No incorpores IDs fijos de tenant, proyecto o campos. Si no puedes consultar esta configuración, entrega el borrador con la limitación; no escribas basándote en supuestos.

Antes de la primera escritura establece el sitio y proyecto explícitos. Si ya están configurados y autorizados, inclúyelos en la revisión sin volver a pedirlos; si faltan o hay ambigüedad, pregunta. Tener permiso de acceso a un sitio no significa que el usuario lo haya elegido como destino. Un acceso fallido al destino no autoriza crear en el sitio de las fuentes.

## Preparación de un lote nuevo tras aprobar la creación

La fase A no escribe en Jira. Su revisión presenta el plan y destino completos y explica que la aprobación de creación cubre creación y verificación de épica y tareas, adjuntos solicitados, documentation-required, Done, documentation-scope-ready y completar/verificar la tarea automatizada. No incluye ejecución del agente. Acepta una aprobación inequívoca en lenguaje natural después de presentar el plan; CREAR es un ejemplo, no una contraseña. Una petición inicial de crear no sustituye esa revisión. Si cambian materialmente alcance o destino, presenta el cambio y solicita aprobación del plan modificado. Si el usuario autoriza solo crear y entregar claves, realiza eso y ofrece preparar el contexto como siguiente paso; no transiciones ni solicites la tarea automatizada sin autorización. Al reanudar una preparación aprobada, continúa sin pedirla de nuevo. Los pasos siguientes pertenecen a la fase B y se realizan dentro de ese alcance, únicamente para un lote nuevo.

1. Comprueba acceso, campos, tipos, relaciones, transiciones y automatizaciones antes de crear. Si preparar tickets pudiera activar por sí solo el agente, detente: CREAR no autoriza ejecución.
2. Busca duplicados en el proyecto por propósito, fuentes y títulos; revisa candidatos completos. Un título coincidente no basta. Reutiliza tickets documentales que correspondan al plan aprobado; si cambia materialmente lo aprobado, presenta la modificación antes de escribir. Una solicitud de lote nuevo no autoriza borrar el anterior. Conserva un registro de progreso con versión del plan y destino aprobados, identificadores locales, claves Jira, relaciones, acciones verificadas, fallos y siguiente paso. No marques éxito sin recuperar el ticket.
3. Crea la épica dedicada; guarda su clave inmediatamente. Sustituye las referencias provisionales del borrador por las claves verificadas en campos y texto (incluido «Padre») al materializarlo; esa sustitución no cambia el alcance aprobado. Crea cada Task hija directa mediante parent, nunca Subtask, con su descripción y `documentation-required`, guardando cada clave. Carga los adjuntos solicitados y verifica su inventario por ticket como indica [evidencia-y-alcance.md](evidencia-y-alcance.md#capturas-y-adjuntos). No cambies etiquetas, estados ni descripciones de los tickets originales usados como fuentes.
4. Recupera los tickets y verifica sitio/proyecto, todos los encabezados de plantilla, descripción convertida sin pérdidas relevantes, parent, etiqueta, tipo, completitud y adjuntos. Mide de nuevo el contenido real. Dentro de la preparación autorizada, transiciona solo las tareas nuevas preparadas a una categoría Done y confirma por lectura; no deduzcas la categoría del nombre del estado. Aquí Done significa «contexto documental preparado y revisado», no «funcionalidad disponible en producción». Un pendiente conservado no se considera resuelto por la transición.
5. Solo cuando todas las tareas previstas estén verificadas y en Done, añade `documentation-scope-ready` a la épica. No le añadas `documentation-required`. Esta etiqueta solicita a la automatización existente una tarea con `documentation-task`.
6. Localiza esa tarea por relaciones/campos de origen y claves, no solo por el resumen. Verifica que referencia exactamente la épica y todas las tareas, sin duplicados. Si aún no aparece, haz una comprobación acotada según el tiempo conocido de la regla y entrega el estado pendiente; no crees una segunda tarea ni ejecutes.
7. Comprueba el modo de entrada y completa la descripción humana preparada sin perder los campos de origen. Recupera y verifica el resultado; confirma el mapeo exacto de épica y tareas hacia `jira_epic_key` y `jira_task_keys`, incluido su orden. Repite la medición con esta descripción definitiva y el contenido recuperado. Informa las claves, fase y pendientes y continúa con [la comprobación antes de ejecutar](ejecucion-y-seguimiento.md#antes-de-ejecutar).

Ante un fallo parcial, conserva las claves verificadas y detente en la operación fallida. Si una escritura termina con timeout, busca su resultado antes de repetirla. Al continuar, lee de nuevo las claves y crea solo lo que se demuestre ausente. No borres tickets para «deshacer» el lote ni reapliques la etiqueta de disparo a ciegas. Si no puedes determinar si la operación ocurrió, informa la incertidumbre y pide el dato necesario.

## Solicitud documental en una épica existente

Este recorrido conserva A (revisar alcance, contenido, destino y acciones) y B (materializar lo aprobado), sin crear otra épica ni otro batch de fuentes. Sirve tanto para crear una nueva solicitud expresamente acordada como para recuperar una existente. Una instrucción posterior al acuerdo como «Crea un ticket nuevo con lo que hemos acordado» autoriza crear esa solicitud, no ejecutar el agente.

1. Recupera la épica, fuentes y solicitudes candidatas completas. Distingue su función por contenido, etiqueta y referencias: `documentation-required` identifica fuentes; `documentation-task` identifica la solicitud ejecutable. Tener `parent` no convierte una solicitud en fuente ni exige otro batch. Si la función es ambigua, aclárala antes de escribir o disparar.
2. Para una nueva solicitud, verifica la vía existente configurada de creación y el mapeo de origen. Si admite creación directa autorizada, crea una única Task con `documentation-task`, descripción humana revisada y referencias verificadas; conserva el padre acordado. Si depende de una automatización, usa solo la vía verificada y autorizada. No crees una solicitud manual en paralelo con una generación pendiente ni reapliques `documentation-scope-ready` para forzar otra. Si no hay vía compatible, explica la configuración pendiente y quién debe comprobarla.
3. Tras crear o recuperar, lee la solicitud y verifica descripción sin pérdidas, referencias exactas a épica y tareas en el orden esperado, imágenes seleccionadas e IDs reales según [imagenes-publicacion.md](imagenes-publicacion.md), estado/etiquetas y disparador. Verifica las fuentes contra el contrato y mide el contexto real. No pases fuentes a Done, añadas etiquetas a la épica ni crees nuevas fuentes por el mero parentesco de la solicitud. Si una fuente no cumple, comunica la clave y el requisito pendiente sin modificarla por iniciativa propia.
4. Continúa con [la comprobación de ejecución](ejecucion-y-seguimiento.md#antes-de-ejecutar). Si está preparada y falta permiso de ejecución, ofrece explícitamente ejecutarla y espera. Si ya existe autorización vigente para esa solicitud y riesgo, úsala sin pedir otra equivalente. Si falta información, acceso o configuración, explica el bloqueo y una acción concreta para resolverlo; no cierres solo con la clave.

## Entradas del agente y ejecución separada

Para adjuntos seleccionados para el artículo, usa [el contrato de imágenes](imagenes-publicacion.md) después de verificar ticket e ID real. Colócalo en una sola descripción del lote; nunca amplíes el manifiesto legado. Recupera la descripción y los metadatos para comprobar la selección y vuelve a medir antes de ejecutar.

El modo estructurado recibe juntos `jira_epic_key` y `jira_task_keys`; este último es una lista de claves separadas por comas. Rechaza vacíos, duplicados y claves inválidas. El patrón actual es `[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[1-9][0-9]*`. El ticket conserva `issue_key`, `issue_summary`, `issue_description`; las referencias se pasan por separado. Configura o descubre los campos que la automatización mapea a estos inputs, sin inventar IDs.

El modo legado acepta únicamente este manifiesto estricto en la descripción:

```text
DOCUMENTATION_SOURCE_V1
EPIC_KEY: APP-123
TASK_KEYS:
- APP-124
```

En ese modo el contexto consolidado contiene épica y tareas, sin descripción humana de la tarea documental. No combines manifiesto y prosa. Si el entorno solo ofrece el modo legado, explica que no permite completar el texto humano pedido sin perder compatibilidad; entrega ese texto preparado por separado y detente antes de ofrecer ejecución hasta verificar una vía compatible. No cambies reglas ni workflow para resolverlo.

Después de verificar todo y mostrar el riesgo, ofrece explícitamente ejecutar la solicitud y espera una autorización independiente si aún no se concedió para ese alcance y riesgo. Aprobar la creación no la sustituye; «Ejecuta el agente» sí permite continuar sin otra confirmación equivalente. Antes de cada disparo o reintento consulta ejecuciones, comentarios de inicio y PRs asociados a la clave documental y al intento. Un timeout o comentario de inicio obliga a recuperar el estado antes de repetir; una ejecución ya existente se sigue, no se duplica. Si no puedes descartar duplicados, informa y no dispares.

La documentación local describe: una tarea con `documentation-task` pasa a In Progress; Jira añade automáticamente `documentation-agent-ready`, que inicia GitHub Actions. El workflow del repositorio usa `workflow_dispatch`, pero eso por sí solo no prueba que la regla del tenant esté activa. Verifica la regla y usa el disparador que corresponda, una sola vez. No sustituyas transición por etiqueta, no apliques ambas manualmente y no despaches directamente un workflow alternativo sin verificar que sea la vía existente autorizada.

Conserva identificador, enlace y estado observado del disparo para [consultar y recuperar el resultado](ejecucion-y-seguimiento.md#consultar-el-resultado). No reejecutes automáticamente por demora, abstención o fallo.

## Medición local

`scripts/medir_lote.py` es un medidor offline de texto ya convertido a Markdown, sin API ni credenciales. Recibe JSON UTF-8 con esta forma:

```json
{
  "documentation_task": {"key": "DOC-999", "summary": "Documentar preferencias", "description": "Contexto humano"},
  "epic": {"key": "APP-123", "summary": "Preparar contexto de preferencias", "description": "Descripción de épica"},
  "tasks": [
    {"key": "APP-124", "summary": "Cambiar una preferencia", "description": "Recorrido y evidencias"}
  ]
}
```

Usa claves provisionales explícitas antes de crear y repite con claves definitivas. El medidor comprueba el esquema para evitar omisiones accidentales; no valida disponibilidad, tipos Jira ni relaciones.

Reproduce la composición estructurada actual: `Documentation task CLAVE: RESUMEN\n\nDESCRIPCIÓN`, luego `Epic CLAVE: RESUMEN\n\nDESCRIPCIÓN`, luego cada `Task CLAVE: RESUMEN\n\nDESCRIPCIÓN`, unidas por dos saltos de línea. Normaliza resúmenes y espacios exteriores de descripciones de épica/tareas como hace el generador; conserva literalmente la descripción humana. Cuenta `len(texto)` en Python y muestra solo métricas y SHA-256, sin volcar el contenido.

- Código 0: hasta 45.000 caracteres inclusive.
- Código 1: supera 45.000, sin superar 60.000; reducir antes de crear.
- Código 2: supera 60.000; el agente rechazará ese contexto.
- Código 3: archivo o esquema inválido; no es una medición válida.

El tamaño no incluye prompt, documentos existentes, serialización JSON, tokens ni la configuración que no viaja al agente. Incluye los registros/evidencias que se hayan incorporado a las descripciones. ADF convertido, resúmenes, claves definitivas y orden de inputs deben corresponder con el lote real; una medida del borrador no prueba el tamaño final. En modo legado este medidor sobreestima al incluir la sección humana, y no sirve para demostrar compatibilidad de la descripción.

Si está disponible y autorizado, `diagnose_only=true` del workflow existente usa las referencias estructuradas y contexto humano, verifica Jira y compara el contexto preparado sin llamar a Claude ni crear PRs. Es una consulta externa: los tests de la skill no la ejecutan. No ejecutes el workflow normal como prueba.
