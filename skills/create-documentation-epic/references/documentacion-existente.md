# Documentación existente: configuración portable

Lee esta referencia durante la fase A, antes de decidir crear o actualizar artículos. Esta configuración identifica fuentes; no concede acceso, instala conectores ni comparte conexiones entre usuarios. No configura el destino Jira.

| Parámetro | Valor |
| --- | --- |
| Fuente principal pública | https://documentation-poc-beedigital.github.io/documentation-poc/ |
| Repositorio de apoyo opcional | documentation-poc-Beedigital/documentation-poc |
| Rama de apoyo | main |
| Directorio de artículos | docs/centro-de-ayuda/ |

1. Consulta primero la web pública y localiza los artículos relacionados con los recorridos aportados. Lee su contenido relevante completo, siguiendo páginas relacionadas y continuaciones cuando sea necesario; resultados de búsqueda y fragmentos no equivalen a leer el artículo.
2. Registra enlace directo, título, fecha de consulta, alcance leído y acceso. Conserva fecha de revisión, versión o identificador del artículo si están disponibles; si no, indica «no disponible» sin inventarlos. Traslada al plan el recorrido vigente descrito y las diferencias con las fuentes nuevas.
3. Usa GitHub solo como apoyo si existen herramientas y acceso autorizados. Lee los archivos relacionados de la rama y directorio configurados, y registra ruta, referencia, commit y versión cuando estén disponibles. La ausencia de GitHub no bloquea si la web aporta el contenido necesario.
4. No asumas que `main` está desplegado. Distingue el contenido observado en la web del contenido del repositorio (POC sin publicación confirmada); una coincidencia sin evidencia de despliegue tampoco confirma el SHA publicado. Conserva las divergencias y su procedencia.
5. Si falla la web, explica qué no se pudo consultar y pide el artículo o material pertinente al usuario. El apoyo GitHub puede aportar contexto, pero no se convierte en prueba de publicación vigente. No declares ausencia de artículos ni una lectura realizada por un acceso fallido; puedes preparar el plan con esa limitación y su riesgo explicado.

Un artículo antiguo que contradice un cambio confirmado puede ser precisamente el candidato a actualizar. Esa diferencia no bloquea por sí sola: conserva ambos textos, sus fuentes y qué evidencia confirma el cambio. Pregunta solo por hechos indispensables todavía sin resolver, sin trasladar órdenes de abstención al agente.

Recoge URLs oficiales con fuente y alcance comprobado: que una URL responda no confirma la pantalla. No inventes rutas de registro o plataforma ni conserves sesiones, tokens o datos personales. El agente usa el catálogo local `.github/documentation-destinations.json` sin búsquedas externas durante la generación; actualmente solo confirma la web general de Beesible. Explica el recorrido cuando no haya enlace directo confirmado y evita enlaces redundantes.

Registra el lugar lógico del artículo en el índice y el recorrido de la categoría: registro y primeros pasos antes de acceso recurrente y gestión. El orden del índice no controla la sidebar ni Anterior/Siguiente; el agente puede proponer `sidebar_position` opcional y Python gestiona el frontmatter, sin renombrar rutas ni renumerar categorías. Mantén Plan Start mientras no exista evidencia de otro nombre.
