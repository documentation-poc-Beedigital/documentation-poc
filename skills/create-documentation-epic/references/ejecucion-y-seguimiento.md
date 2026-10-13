# Comprobación, resultado y recuperación

Lee esta referencia al preparar la ejecución y tras el disparo. Usa [jira-workflow.md](jira-workflow.md) para las operaciones y sus comprobaciones técnicas.

## Antes de ejecutar

Entrega una revisión breve y comprensible con:

- Alcance preparado y excluido o aplazado, audiencia y estado de lanzamiento.
- Evidencia disponible, artículos consultados y fuentes que no se pudieron abrir.
- Pendientes secundarios que se omiten y pendientes indispensables que siguen afectando al recorrido, con sus V-nn y consecuencias.
- Verificación de descripciones, relaciones, etiquetas, Done, origen de la tarea automatizada y medición del contexto recuperado.
- Riesgo de abstención y siguiente paso recomendado, también tras reducir el alcance. Explica qué está suficientemente descrito y qué funcionalidad está confirmada; un plan FUTURO no confirma implementación ni elimina el riesgo.

No presentes la clasificación de pendientes como garantía de resultado. Si todo el alcance está bloqueado por datos indispensables, recomienda completar los tickets o reducirlo antes de ejecutar. Puede ejecutarse con esos pendientes solo si el usuario lo solicita expresamente tras conocer el riesgo y se cumplen las comprobaciones técnicas. No sustituyas esas comprobaciones por aceptación del riesgo.

CREAR cubre solo las acciones mostradas en la revisión de creación. Solicita una autorización independiente para ejecutar, asociada a la tarea documental y al alcance revisado. Conserva las autorizaciones ya concedidas; una nueva pregunta solo es necesaria si la acción o el riesgo quedan fuera de ellas. Una reejecución posterior requiere autorización propia, no se deduce de la ejecución anterior.

Comprueba ejecución activa o PR abierta antes del disparo. Usa una vez el disparador existente verificado. Si su resultado es ambiguo, investiga el estado antes de repetir y conserva el bloqueo si no puedes determinarlo. No alternes entre transición, etiqueta y workflow directo para probar cuál funciona.

## Consultar el resultado

Tras el disparo consulta la tarea documental, ejecución vinculada y enlaces de salida con las herramientas autorizadas disponibles. Usa las claves y el identificador de ejecución para no atribuir un resultado antiguo al intento actual. Realiza una consulta inicial y, si sigue activo, como máximo dos consultas adicionales espaciadas según la duración conocida; si no se conoce, entrega el estado pendiente tras la primera consulta. No mantengas polling indefinido.

Si no hay acceso, indica que solo se ha verificado el disparo, dónde comprobar el resultado (tarea de Jira y, si está disponible, ejecución del workflow **Documentation agent PoC** en GitHub Actions) y qué resultado o informe aportar para retomar. No inventes URLs, preview ni finalización. Un estado Done o un job verde por sí solos no prueban una propuesta: consulta la decisión y los enlaces.

## Orientar según la evidencia del resultado

| Resultado comprobado | Qué comunicar y hacer a continuación |
| --- | --- |
| Propuesta | Entrega la PR y preview si existen y están disponibles. Explica que debe revisar pasos, audiencia, disponibilidad y diferencias con el recorrido vigente. Si no hay preview, dilo. El siguiente paso es la revisión humana; no apruebes, fusiones ni publiques por iniciativa propia. |
| Abstención | Explica el motivo del informe, identifica los datos que faltan y relaciónalos con V-nn y las tareas existentes. Lee nueva evidencia y pregunta de una en una por los indispensables. Ayuda a completar las descripciones existentes dentro de la autorización, preservando fuentes y contradicciones; vuelve a verificar y medir antes de ofrecer otra ejecución. No crees otro lote para eludir la abstención. |
| Fallo técnico | Identifica el paso fallido a partir de logs/informes: entrada, acceso, conversión, transporte, validación, build, publicación o notificación. Explica solo opciones de recuperación verificadas y el siguiente dato necesario. No inventes una causa ni lo llames abstención si no hay esa decisión. |
| Pendiente o desconocido | Explica lo verificado, lo que sigue pendiente y dónde consultar. Guarda claves, intento y siguiente comprobación; no afirmes que terminó. |

Una abstención válida puede coexistir con un fallo de notificación. Una PR puede existir aunque falle una notificación posterior. Revisa decisión, informe, validación y PR antes de recomendar otra ejecución: un job rojo no determina por sí solo el resultado funcional.

Para recuperar, reutiliza los tickets y las operaciones comprobadas. Verifica si una rama, PR, adjunto o transición ya existe antes de repetir. No borres ni dupliques para resolver incertidumbre. Si el fallo requiere cambios en automatizaciones, secretos, agente o despliegues, explica el bloqueo y deriva al responsable; esta skill no modifica esos componentes.

## Pausar o cerrar

Mantén fase, claves/enlaces, completado, pendientes y permisos. En cada respuesta ofrece un siguiente paso concreto en lenguaje sencillo, por ejemplo «Confirmar para qué clientes está disponible», «Preparar la solicitud documental» o «Revisar la propuesta en esta PR». Si el usuario para, entrega ese registro para retomar. Cierra al completar el alcance pedido, ante un bloqueo explicado o por decisión del usuario; no uses la entrega de claves como cierre automático del recorrido completo.
