# Comprobación, resultado y recuperación

Lee esta referencia al preparar la ejecución y tras el disparo. Usa [jira-workflow.md](jira-workflow.md) para las operaciones y sus comprobaciones técnicas.

## Antes de ejecutar

Entrega una revisión breve y comprensible con:

- Alcance preparado y excluido o aplazado, audiencia y estado de lanzamiento.
- Evidencia disponible, artículos consultados y fuentes que no se pudieron abrir.
- Pendientes secundarios que se omiten y pendientes indispensables que siguen afectando al recorrido, con sus V-nn y consecuencias.
- Verificación por lectura de descripción de la solicitud, referencias de origen y orden, selección de imágenes e identidades reales (o ausencia), relaciones, etiquetas, estados pertinentes y medición del contexto recuperado. Done y `documentation-required` se exigen a las fuentes del contrato, no como preparación de la solicitud ejecutable. Una solicitud `documentation-task` con padre se ejecuta directamente por su disparador verificado.
- Riesgo de abstención y siguiente paso recomendado, también tras reducir el alcance. Explica qué está suficientemente descrito y qué funcionalidad está confirmada; un plan FUTURO no confirma implementación ni elimina el riesgo.

No presentes la clasificación de pendientes como garantía de resultado. Si todo el alcance está bloqueado por datos indispensables, recomienda completar los tickets o reducirlo antes de ejecutar. Puede ejecutarse con esos pendientes solo si el usuario lo solicita expresamente tras conocer el riesgo y se cumplen las comprobaciones técnicas. No sustituyas esas comprobaciones por aceptación del riesgo.

La aprobación de creación cubre solo las acciones mostradas en esa revisión, también al crear una solicitud dentro de una épica existente. Acepta lenguaje natural: «Crea un ticket nuevo con lo que hemos acordado» permite crear, no ejecutar. Una vez verificada y preparada la solicitud, si falta permiso termina con una oferta explícita: «¿Quieres que ejecute el agente para [clave]?» y espera. Si faltan datos o configuración, identifica el bloqueo y el siguiente paso concreto. «Ejecuta el agente» concede permiso para la solicitud y alcance/riesgo identificados; continúa sin otra confirmación equivalente. Conserva las autorizaciones ya concedidas; una nueva pregunta solo es necesaria si la acción o el riesgo quedan fuera de ellas. Una reejecución posterior requiere autorización propia, no se deduce de la ejecución anterior.

Antes de cualquier disparo o repetición, comprueba ejecuciones asociadas, comentarios de inicio y PRs de la solicitud y el intento. Si ya hay ejecución, recupera y sigue su estado; un comentario de inicio sin resultado localizable o un timeout no permiten repetir a ciegas. Usa una vez el disparador existente verificado. Si su resultado es ambiguo, investiga el estado antes de repetir y conserva el bloqueo si no puedes determinarlo. No alternes entre transición, etiqueta y workflow directo para probar cuál funciona.

## Consultar el resultado

Tras el disparo consulta la tarea documental, ejecución vinculada y enlaces de salida con las herramientas autorizadas disponibles. Usa las claves y el identificador de ejecución para no atribuir un resultado antiguo al intento actual. Realiza una consulta inicial y, si sigue activo, como máximo dos consultas adicionales espaciadas según la duración conocida; si no se conoce, entrega el estado pendiente tras la primera consulta. No mantengas polling indefinido.

Si no hay acceso, indica exactamente qué se confirmó: solicitud de disparo enviada o cambio Jira leído no equivalen a ejecución confirmada. Solo afirma inicio cuando exista ejecución identificada o comentario de inicio atribuible al intento; un comentario no prueba su resultado final. Indica dónde comprobarlo (tarea de Jira y, si está disponible, workflow **Documentation agent PoC** en GitHub Actions) y qué identificador, logs o informe aportar para retomar. No inventes URLs, preview ni finalización. Un estado Done o un job verde por sí solos no prueban una propuesta: consulta la decisión y los enlaces.

## Orientar según la evidencia del resultado

| Resultado comprobado | Qué comunicar y hacer a continuación |
| --- | --- |
| Solicitud enviada | La herramienta aceptó el disparador, pero aún no se verificó el inicio. Busca ejecución o comentario de inicio antes de afirmar que el agente arrancó o de volver a disparar. |
| Ejecución confirmada | Identifica ejecución o comentario de inicio del intento y su estado observado; continúa el seguimiento acotado. No implica resultado ni llamada a Claude confirmada. |
| Propuesta | Entrega la PR y preview si existen y están disponibles. Explica que debe revisar pasos, audiencia, disponibilidad y diferencias con el recorrido vigente. Si no hay preview, dilo. El siguiente paso es la revisión humana; no apruebes, fusiones ni publiques por iniciativa propia. |
| Abstención | Explica el motivo del informe, identifica los datos que faltan y relaciónalos con V-nn y las tareas existentes. Lee nueva evidencia y pregunta de una en una por los indispensables. Ayuda a completar las descripciones existentes dentro de la autorización, preservando fuentes y contradicciones; vuelve a verificar y medir antes de ofrecer otra ejecución. No crees otro lote para eludir la abstención. |
| Fallo técnico | Identifica el paso fallido a partir de logs/informes: entrada, acceso, conversión, transporte, validación, build, publicación o notificación. Explica solo opciones de recuperación verificadas y el siguiente dato necesario. No inventes una causa ni lo llames abstención si no hay esa decisión. |
| Pendiente o desconocido | Explica lo verificado, lo que sigue pendiente y dónde consultar. Guarda claves, intento y siguiente comprobación; no afirmes que terminó. |

Una abstención válida puede coexistir con un fallo de notificación. Una PR puede existir aunque falle una notificación posterior. Revisa decisión, informe, validación y PR antes de recomendar otra ejecución: un job rojo no determina por sí solo el resultado funcional.

Un error de arranque anterior a Claude, por ejemplo `ModuleNotFoundError: No module named 'documentation_contract'`, es un fallo técnico. No lo presentes como abstención de Claude aunque exista un informe de emergencia con `decision=abstention`: contrasta el paso de generación, logs y procedencia del informe. Solo atribuye abstención al modelo si se confirma su respuesta y la validación correspondiente. Comunica el paso fallido y guía la revisión de dependencias del workflow por el responsable; no repitas automáticamente.

Para recuperar, reutiliza los tickets y las operaciones comprobadas. Verifica si una rama, PR, adjunto o transición ya existe antes de repetir. No borres ni dupliques para resolver incertidumbre. Si el fallo requiere cambios en automatizaciones, secretos, agente o despliegues, explica el bloqueo y deriva al responsable; esta skill no modifica esos componentes.

## Pausar o cerrar

Mantén fase, claves/enlaces, completado, pendientes y permisos. En cada respuesta ofrece un siguiente paso concreto en lenguaje sencillo, por ejemplo «Confirmar para qué clientes está disponible», «Preparar la solicitud documental» o «Revisar la propuesta en esta PR». Si el usuario para, entrega ese registro para retomar. Cierra al completar el alcance pedido, ante un bloqueo explicado o por decisión del usuario; no uses la entrega de claves como cierre automático del recorrido completo.
