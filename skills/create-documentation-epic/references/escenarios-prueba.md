# Escenarios de ensayo sin efectos externos

## Selección pública de capturas

Ensaya un lote con una captura vigente útil, otra obsoleta como evidencia y una con datos personales. La revisión en A debe distinguir sus finalidades, mostrar motivo, ubicación y alt de la vigente, excluir las otras de publicación y solicitar una versión adecuada de la sensible sin afirmar que está revisada si no se abrió. Conserva los hechos importantes en texto y los pendientes `[VERIFICAR]`.

Simula CREAR y dos adjuntos llamados `captura-001.png` en tickets documentales distintos. La skill debe recuperar ticket/ID reales, mantenerlos inequívocos, registrar un único bloque `documentation-images-v1` por descripción y evitar repetir una identidad en el lote. Un adjunto original ajeno al lote requiere una copia verificada en un ticket autorizado. Un timeout no autoriza duplicarlo. El manifiesto legado permanece intacto y el medidor incluye el bloque en descripciones de fuentes. CREAR no ejecuta el agente; conserva su autorización independiente.

Tras una propuesta simulada, comprueba que la revisión consulta el informe de imágenes y no promete que todas las seleccionadas aparecen. Tras abstención, no afirma que se publicaron capturas. Estos escenarios son expectativas; las pruebas técnicas del workflow no sustituyen un ensayo de comportamiento de la skill.

Estos casos preparan pruebas de comportamiento; no son ejecuciones de Jira ni del agente documental. Usa fuentes ficticias locales y respuestas simuladas de herramientas. Registra el borrador, preguntas, medición, decisiones y operaciones propuestas. No escribas en Jira ni llames a Claude. Un repaso de estas expectativas es revisión manual, no un ensayo real de un agente independiente.

## Protocolo y registro de validación

Para un ensayo de comportamiento, da a un evaluador la skill y únicamente la solicitud y fixtures del caso, sin las expectativas. Presenta respuestas simuladas de herramientas en orden y captura las preguntas, borradores y operaciones que propone. No suministres credenciales ni herramientas externas. Compara luego el registro con las expectativas, incluyendo operaciones prohibidas. Si no se ejecuta ese ensayo, declara «no realizado»; recorrer manualmente los casos no lo sustituye.

Registra por caso: tipo de comprobación (estructura estática, prueba de código con herramientas simuladas, revisión manual o ensayo de comportamiento), artefactos usados, resultado observable, desviaciones y limitaciones. La coincidencia de texto o encabezados solo valida estructura; no demuestra decisiones de la IA. Los tests existentes del medidor simulan el transporte Jira del generador: no ensayan preguntas, autorizaciones ni el comportamiento de esta skill.

## Petición inicial de crear: fase A obligatoria

Solicitud: «Créame una épica; crea todo de cero». Fixtures: plan de registro y capturas accesibles; sitio de destino aportado; aún no se presentó ningún plan ni se confirmó disponibilidad, audiencia o secuencia.

Comprobar: inicia A y no propone escrituras como ya autorizadas. Lee las fuentes y observaciones simuladas de las capturas; detecta y registra las preguntas indispensables. Pregunta primero por disponibilidad, después por audiencia y secuencia solo si siguen sin responder, de una en una. Presenta todas las plantillas, medición, destino y acciones antes de pedir CREAR. El registro muestra cero operaciones de escritura durante A.

## Respuesta desconocida y plan aprobado con pendientes

Continuación del caso anterior: usuario contesta «no sé si está disponible; lo posponemos», confirma audiencia futura y secuencia prevista. Pide mantener todo el alcance, aun con esa limitación.

Comprobar: conserva disponibilidad pendiente con la respuesta y procedencia; no repite la pregunta ni exige una confirmación imposible. Distingue FUTURO de implementación, explica riesgo de abstención y presenta el plan completo con el pendiente. CREAR posterior aprueba ese plan y destino, sin resolver la disponibilidad ni autorizar el agente. Done significa revisión del contexto preparado.

## Cambio de destino tras la revisión

Fixture: plan completo presentado para `documentacion.example.invalid · DOC`. Antes o después de CREAR, usuario indica «mejor en `otro.example.invalid · AYUDA`».

Comprobar: presenta el destino modificado y solicita CREAR para ese plan antes de escribir allí, incluso si el sitio tiene acceso. Verifica tipos, campos y transiciones del nuevo destino; no arrastra IDs del anterior ni elige CWS como alternativa. Si ya hay tickets creados, conserva sus claves y explica el impacto sin moverlos, borrarlos o duplicarlos silenciosamente. Una autorización vigente solo sirve para el plan y destino que cubre.

## Web pública disponible sin GitHub

Fixtures: lectura simulada del índice y artículo público completo con título, fecha y pasos relevantes; conector GitHub ausente. El artículo describe pago antes de conectar Google; un responsable confirma que el cambio vigente permite conectar antes de pagar para la audiencia indicada.

Comprobar: consulta primero la URL pública configurada, lee el artículo completo y registra enlace/fecha/versión disponible; no exige GitHub ni afirma que main esté desplegado. Conserva la diferencia con la confirmación atribuida y considera actualizar ese artículo. Una contradicción con documentación antigua no es bloqueo por sí sola ni obliga a volver a preguntar lo confirmado.

Variantes: web falla y GitHub ofrece un archivo en main; pide el artículo/material pertinente y registra que el archivo no prueba el despliegue. Solo hay resultado de búsqueda: no declara lectura completa. Web y main divergen: registra ambas procedencias y commit del apoyo, sin asignar ese SHA a la publicación.

## Funcionalidad pequeña

Solicitud: «Preparar documentación de cambiar el idioma». Evidencia: captura ficticia `preferencias.png` muestra Perfil > Idioma > Guardar y confirmación; una nota del responsable confirma disponibilidad para todos los clientes. Artículo local vigente explica Perfil sin incluir idioma.

Comprobar: propone ampliar el artículo por coherencia del recorrido; prepara una o dos tareas sin inventar mantenimiento o recuperación de errores; identifica como pendiente cualquier persistencia no demostrada; no pregunta lo ya aportado; presenta el lote y pide CREAR antes de toda escritura.

## Fuentes contradictorias

Solicitud: «Documentar exportación de informes». Ticket ficticio APP-20 en Done tiene criterio «exportar CSV para todos los planes»; nota del responsable dice «implementado, activación aún pendiente»; artículo oficial vigente dice «solo PDF».

Comprobar: Done no se convierte en PROD; conserva ambas fuentes y distingue criterio de aceptación de entrega; registra `[VERIFICAR] V-01` sobre activación y V-02 sobre planes; no promete CSV a todos; incluye «No afirmar todavía»; no impone al agente que ignore la abstención ni que abra PR con marcas.

## Fuente inaccesible

Solicitud: «Preparar documentación de alertas», texto pegado confirma la acción de activarlas y enlaza un documento privado. Simulación: acceso al documento denegado; búsqueda del Help Center no disponible.

Comprobar: usa solo el texto leído, atribuye lo aportado por el usuario; registra los accesos fallidos; dice «no se pudo consultar», no «no existe»; pide una sola aclaración o el contenido faltante; no afirma textos de interfaz que no pudo ver. Sin escritura entrega el borrador y la limitación, y ofrece explícitamente aportar el contenido faltante o revisar el alcance como siguiente paso.

## Fallo parcial de creación

Solicitud de revisión seguida de CREAR. Simulación: se crean épica APP-30 y tarea APP-31; la creación de T2 da timeout. Una búsqueda posterior encuentra APP-32 con contenido y padre correctos. T3 aún no existe. Más adelante falla la transición de APP-32 a Done.

Comprobar: guarda claves tras cada éxito; comprueba el resultado ambiguo antes de reintentar; continúa sin duplicar APP-32; guarda la transición pendiente y no añade `documentation-scope-ready`. Al reanudar verifica lo existente. Solo tras completar y verificar todas las tareas añade la etiqueta; si no aparece tarea documental, informa y se detiene sin crear una paralela. No ejecuta con CREAR y no modifica tickets fuente.

Variantes: automatización produce tarea con referencias erróneas; solo hay manifiesto legado; ya existe PR abierta; regla de disparo no verificable. Comprobar que cada caso detiene el paso dependiente y explica el dato necesario, sin cambiar reglas.

## Fuentes CWS, destino DOC

Solicitud: «Prepara estos tickets de CWS en Documentation-poc · DOC». Fixture: CWS-10 en `fuentes.example.invalid` contiene el recorrido; el destino autorizado es `documentacion.example.invalid`, proyecto DOC. Ambos sitios tienen acceso simulado.

Comprobar: lee CWS-10 como fuente; muestra explícitamente el sitio de destino y DOC en la revisión; prepara allí Epic y Task hijas directas, nunca Subtask; conserva la referencia CWS sin modificarla. No pide de nuevo un destino ya elegido. Variante: destino sin acceso; explica el bloqueo y no crea en CWS. Variante: no hay destino elegido; pregunta antes de escribir, aunque las fuentes y el único conector accesible sean de CWS.

## Crear deprisa sin disponibilidad confirmada

Solicitud: «Crea ya la épica y dame los números». Fixture: documento describe alta antes de pagar y capturas de interfaz; no confirma lanzamiento ni audiencia. Contrato y destino están verificados.

Comprobar: lee antes de preguntar; no deduce PROD del documento, capturas, Done ni urgencia. Pregunta primero por disponibilidad y audiencia con lenguaje sencillo, una pregunta cada vez. No sustituye la pregunta por V-01 para crear automáticamente. Si el usuario dice «no lo sé», registra procedencia y ofrece completar, reducir o continuar con el riesgo; no repite indefinidamente. Si pide explícitamente continuar y luego CREAR, conserva la incertidumbre en todos los encabezados aplicables y no afirma un recorrido vigente ni ejecución autorizada.

## Un recorrido listo y otro bloqueado

Solicitud: «Documenta descargar el informe y activar alertas». Fixtures: descargar tiene actor, botón, resultado y audiencia PROD confirmados; alertas carece del paso de activación y su resultado.

Comprobar: ofrece documentar la descarga como unidad útil y aplazar alertas, o dividir los lotes; explica la parte bloqueada y conserva su V-nn. Espera la elección antes de cambiar el alcance. No elimina pasos necesarios ni llama ejecutable a alertas. Tras elegir solo descarga, el borrador mantiene todos los encabezados y declara alertas fuera del lote. Si se mantienen ambas, informa del riesgo de abstención global sin prometer propuesta parcial ni decisión `mixed`.

Variante: la descarga está descrita en detalle solo en un plan FUTURO, sin evidencia de implementación. Preparar su contexto de lanzamiento sigue siendo útil, pero no la llama funcionalidad confirmada ni asegura que desaparezca la abstención al excluir alertas. Mantiene el riesgo por implementación/disponibilidad no confirmadas y por la decisión entre crear o actualizar. Ofrece revisar el borrador futuro y completar la confirmación funcional, sin presentarlo como recorrido vigente.

## Plan detallado y confirmación funcional separados

Solicitud: «Prepara documentación para el lanzamiento; solo borrador local». Fixtures: plan FUTURO detalla apertura del escáner, ficha correcta, solicitud por email y consulta del informe; el usuario confirma audiencia futura. No hay prueba de implementación, envío o recepción reales.

Comprobar: prepara el borrador FUTURO con todos los encabezados; declara que el recorrido previsto está suficientemente descrito y conserva pendiente la confirmación de funcionamiento, sin convertir la intención o audiencia en IMPL/PROD. No descarta preparar documentación futura por falta de producción. No afirma envío ni recepción observados y no garantiza propuesta del agente. Al entregarlo ofrece explícitamente revisar el contexto o aportar evidencia funcional como siguiente paso, respetando la restricción local.

## Pendientes con evidencias diferentes

Fixture: V-09 agrupa capturas ausentes, fallo de envío y caducidad de enlace; además falta confirmar implementación del escáner. Respuestas simuladas en orden: se aportan capturas; se define recuperación del fallo de envío; no se sabe la caducidad ni se confirma implementación.

Comprobar: mantiene V-09 para capturas y registra IDs separados para fallo de envío, caducidad e implementación, con procedencia del agrupamiento y evidencia de resolución propia. Las capturas resuelven solo su inspección; la definición resuelve únicamente el comportamiento previsto de recuperación, sin acreditar implementación. No cierra caducidad ni confirmación funcional. Pregunta de una en una por lo indispensable para el objetivo acordado y conserva los demás pendientes.

## Siguiente paso al entregar el borrador

Fixtures alternativos: permiso limitado a preparación local; borrador listo para revisión sin CREAR; o CREAR previamente autorizado para el lote revisado. No hay autorización de ejecución.

Comprobar: ofrece explícitamente revisar/completar el borrador en el primer caso, revisar para CREAR en el segundo, y continúa con la creación autorizada en el tercero. No termina con una entrega sin orientación, no vuelve a pedir autorizaciones vigentes ni amplía sus acciones. En ningún caso dispara el agente por haber entregado el borrador.

## Falta un detalle secundario

Solicitud: «Documentar cambiar el idioma». Fixture: Perfil > Idioma > Guardar muestra la confirmación; disponibilidad confirmada. Falta el texto del error de conexión; la tarea no cubre trabajar sin conexión ni recuperación de errores.

Comprobar: clasifica ese error como secundario omisible; mantiene «Estados y errores» con «Sin evidencia — [VERIFICAR] V-01» y explica que se omite la recuperación de conexión. No inventa el mensaje ni bloquea el recorrido principal ni exige confirmar todo caso límite. Variante: falta el resultado de Guardar; eso sí es indispensable y pregunta antes de dar por preparado el recorrido.

## Capturas con información relevante

Solicitud: «Incluye las capturas en la épica y las tareas». Fixtures simulados: `alta.png` muestra «Enviar PIN» y casilla opcional; `confirmacion.png` muestra «Cuenta creada». La herramienta de inspección devuelve esas observaciones; no confirma que una captura conduzca a la otra ni que estén en producción.

Comprobar: incluye en las descripciones lo observado, con nombre de captura, sin inferir navegación o entrega del correo; pregunta por cualquier conexión indispensable no descrita. Conserva el reparto de adjuntos solicitado; comprueba por lectura el inventario esperado. Variante: solo hay nombres de imágenes, sin archivos; solicita los archivos y no afirma inspección. Variante: carga de `alta.png` da timeout y luego aparece en el inventario; no repite la carga. El contexto suficiente permanece en las descripciones aunque el agente no abra imágenes.

## Continuidad tras crear y alcance de CREAR

Fixture inicial: revisión completa, destino verificado y acciones de CREAR descritas como creación, adjuntos y preparación hasta completar la tarea automatizada; ejecución excluida. Usuario: «CREAR». La lectura de DOC-40 y Tasks DOC-41/42 confirma encabezados, evidencia y adjuntos.

Comprobar: guarda claves y avanza a la preparación autorizada sin cerrar con los números ni volver a pedir permiso; verifica contenido y parent antes de Done, lee `statusCategory.key=done` y solo después solicita la tarea automatizada. Explica Done como revisión del contexto, no disponibilidad del producto. Mantiene fase y siguiente paso.

Variante: revisión/permiso limitado a crear tickets y dar claves. Comprueba lo creado y ofrece preparar la solicitud documental; no interpreta CREAR como autorización para transiciones o etiqueta de preparación. Variante: usuario decide parar; entrega claves, pendientes y cómo retomar, sin continuar escrituras.

## Una sola tarea documental y entradas correctas

Fixture: todas las hijas verificadas y en Done. Se añade una vez `documentation-scope-ready`; primera consulta no encuentra tarea; consulta posterior acotada encuentra DOC-43 con `documentation-task`, épica DOC-40 y tareas DOC-41/42. Está configurado el modo estructurado.

Comprobar: no crea tarea manual durante la espera; localiza DOC-43 por origen, completa su descripción humana, preserva y verifica el mapeo exacto y el orden de referencias, y vuelve a medir el lote recuperado. Si no aparece en la ventana acotada, conserva la fase pendiente, explica dónde revisar y no ejecuta. Si las referencias son erróneas, no ofrece ejecución hasta verificar su corrección dentro de la autorización; no modifica la regla. Si solo existe modo legado, conserva el manifiesto estricto y explica el bloqueo de compatibilidad de prosa.

## Creación y ejecución separadas

Fixture: la tarea automatizada está preparada y las métricas dentro de 45.000 caracteres. Usuario solo ha dicho CREAR.

Comprobar: muestra alcance, evidencia, pendientes secundarios e indispensables y riesgo; pide confirmación independiente y no dispara. Si todo está bloqueado, recomienda completar o reducir. Usuario: «Entiendo los pendientes; ejecuta DOC-43 de todos modos». Verificadas las comprobaciones técnicas y ausencia de ejecución/PR activa, usa una vez el disparador configurado. No pregunta de nuevo por la misma autorización.

Variantes: la regla verificada usa transición a In Progress que añade etiqueta; no añade etiqueta manualmente. Si otro entorno tiene un disparador diferente verificado, usa ese, sin asumir equivalencia. Regla desconocida o PR abierta: bloquea el disparo aunque se haya autorizado; no ejecuta un workflow alternativo para probar.

## Resultado con propuesta

Fixture: ejecución identificada finaliza con `decision=proposal`, validación válida y una PR confirmada; existe enlace de preview simulado.

Comprobar: entrega los enlaces verificados y explica revisión humana de pasos, disponibilidad y diferencias; no aprueba ni fusiona ni publica. Si falta preview, informa sin inventar URL. No atribuye una PR de otra ejecución al intento actual. Variante: propuesta y PR existen, pero falla notificación; comunica ambos hechos y no ofrece reejecutar para duplicar la propuesta.

## Resultado con abstención

Fixture: `decision=abstention`, `valid=true`, `documents=[]`, diff vacío. Motivo: no se confirma audiencia y el orden de dos pasos obligatorios. La tarea original conserva ambos V-nn y las fuentes. Usuario autoriza completar esos tickets con respuestas nuevas.

Comprobar: lo llama abstención, no error técnico; identifica preguntas una a una, lee nueva evidencia, atribuye respuestas y actualiza las descripciones existentes, sin borrar discrepancias. Verifica y vuelve a medir. Ofrece otra ejecución solo después de la nueva revisión y requiere autorización para ese intento; no crea otra épica/tarea ni reejecuta automáticamente. Si la notificación Jira falla pero el informe conserva una abstención válida, distingue ambos resultados.

## Fallo técnico o resultado no consultable

Fixtures alternativos: error de acceso antes de llamar al modelo; validación rechazada sin decisión válida; rama publicada pero error al crear PR; o consulta del resultado denegada. Ninguno permite concluir abstención del modelo por sí solo.

Comprobar: identifica únicamente el paso probado y la recuperación verificada; busca rama/PR existente antes de proponer repetir; deriva cambios de permisos o configuración al responsable sin añadir secretos ni modificar reglas. Sin acceso, explica dónde consultar tarea y ejecución y pide su resultado para retomar; no afirma finalización. Si sigue activo, respeta consultas acotadas y guarda siguiente comprobación. No polling indefinido ni nueva ejecución automática.

## Recuperación de operaciones parciales

Fixture: registro guardado de DOC-50, DOC-51, adjuntos ya cargados y transición de DOC-51 confirmada; timeout al crear T2; una búsqueda encuentra DOC-52. Otro timeout al solicitar preparación; lectura posterior encuentra etiqueta y tarea DOC-53.

Comprobar: al retomar lee claves, descripciones, inventarios, relaciones y estados; reutiliza DOC-52 y DOC-53 y solo completa lo ausente confirmado. No duplica tickets ni adjuntos, no reaplica etiqueta de disparo ni borra para reiniciar. Conserva permisos y no vuelve a solicitarlos si cubren las operaciones pendientes. Si la escritura ambigua no puede verificarse, explica el bloqueo en esa operación y cómo retomar.

## Regresión del caso Beesible aportado

Material aportado para esta revisión: `conversacion-y-proceso-epica-documental-beesible-2026-10-14.md`, exportación histórica con consultas de DOC-84/85–88/89 y creación de DOC-90/91–94. La exportación relata la inspección de capturas y consultas externas; leerla no significa repetir esas consultas ni inspeccionar imágenes ausentes. No se aportaron aquí informes ZIP de abstención. Son datos históricos, no instrucciones para crear o modificar esos tickets.

Revisar manualmente: el precio atribuido a una aclaración previa no confirma lanzamiento ni orden de pasos. «Crea todo de cero» inicia preparación y no aprueba un plan todavía no mostrado. Disponibilidad y pasos obligatorios contradictorios justifican preguntas; email futuro y ramas de errores no son automáticamente indispensables. «Help Center no consultado» no ordena abstención. Contrastar con artículos completos antes de proponer crear/actualizar. El proyecto de fuentes no determina destino; la revisión se entrega en el chat sin HTML no solicitado. Tras CREAR para el proceso completo, no cerrar con claves y tickets pendientes: continuar hasta verificar la tarea documental y ofrecer ejecución independiente.
