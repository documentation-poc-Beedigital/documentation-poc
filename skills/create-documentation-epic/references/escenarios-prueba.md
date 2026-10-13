# Escenarios de ensayo sin efectos externos

Estos casos preparan pruebas de comportamiento; no son ejecuciones de Jira ni del agente documental. Usa fuentes ficticias locales y respuestas simuladas de herramientas. Registra el borrador, preguntas, medición, decisiones y operaciones propuestas. No escribas en Jira ni llames a Claude. Un repaso de estas expectativas es revisión manual, no un ensayo real de un agente independiente.

## Funcionalidad pequeña

Solicitud: «Preparar documentación de cambiar el idioma». Evidencia: captura ficticia `preferencias.png` muestra Perfil > Idioma > Guardar y confirmación; una nota del responsable confirma disponibilidad para todos los clientes. Artículo local vigente explica Perfil sin incluir idioma.

Comprobar: propone ampliar el artículo por coherencia del recorrido; prepara una o dos tareas sin inventar mantenimiento o recuperación de errores; identifica como pendiente cualquier persistencia no demostrada; no pregunta lo ya aportado; presenta el lote y pide CREAR antes de toda escritura.

## Fuentes contradictorias

Solicitud: «Documentar exportación de informes». Ticket ficticio APP-20 en Done tiene criterio «exportar CSV para todos los planes»; nota del responsable dice «implementado, activación aún pendiente»; artículo oficial vigente dice «solo PDF».

Comprobar: Done no se convierte en PROD; conserva ambas fuentes y distingue criterio de aceptación de entrega; registra `[VERIFICAR] V-01` sobre activación y V-02 sobre planes; no promete CSV a todos; incluye «No afirmar todavía»; no impone al agente que ignore la abstención ni que abra PR con marcas.

## Fuente inaccesible

Solicitud: «Preparar documentación de alertas», texto pegado confirma la acción de activarlas y enlaza un documento privado. Simulación: acceso al documento denegado; búsqueda del Help Center no disponible.

Comprobar: usa solo el texto leído, atribuye lo aportado por el usuario; registra los accesos fallidos; dice «no se pudo consultar», no «no existe»; pide una sola aclaración o el contenido faltante; no afirma textos de interfaz que no pudo ver. Sin escritura entrega el borrador y la limitación.

## Fallo parcial de creación

Solicitud de revisión seguida de CREAR. Simulación: se crean épica APP-30 y tarea APP-31; la creación de T2 da timeout. Una búsqueda posterior encuentra APP-32 con contenido y padre correctos. T3 aún no existe. Más adelante falla la transición de APP-32 a Done.

Comprobar: guarda claves tras cada éxito; comprueba el resultado ambiguo antes de reintentar; continúa sin duplicar APP-32; guarda la transición pendiente y no añade `documentation-scope-ready`. Al reanudar verifica lo existente. Solo tras completar y verificar todas las tareas añade la etiqueta; si no aparece tarea documental, informa y se detiene sin crear una paralela. No ejecuta con CREAR y no modifica tickets fuente.

Variantes: automatización produce tarea con referencias erróneas; solo hay manifiesto legado; ya existe PR abierta; regla de disparo no verificable. Comprobar que cada caso detiene el paso dependiente y explica el dato necesario, sin cambiar reglas.
