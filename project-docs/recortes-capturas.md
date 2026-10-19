# Recortes de capturas: contrato y validación

El bloque `documentation-images-v1` conserva versión 1 y sus seis campos
obligatorios. Una entrada puede añadir `crop` con exactamente `left`, `top`,
`right`, `bottom`, `original_width`, `original_height` (enteros JSON, sin booleanos)
y `original_sha256` (64 caracteres hexadecimales minúsculos). Los límites derecho
e inferior son exclusivos. Las dimensiones corresponden al raster original, con
origen arriba a la izquierda. Se exige `0 <= left < right <= original_width` y
`0 <= top < bottom <= original_height`. Véase el ejemplo en
[la referencia portable de la skill](../skills/create-documentation-epic/references/imagenes-publicacion.md).

La skill muestra en el plan A una preview recortada realmente del original,
con motivo y coordenadas, y conserva su hash y dimensiones. La aprobación del
plan cubre esos recortes sin confirmaciones redundantes; ejecutar el agente
requiere autorización independiente. Antes de registrar `crop`, la skill verifica
los bytes del adjunto Jira definitivo contra el archivo inspeccionado. Si no hay
herramientas visuales o de recorte, ofrece original o captura preparada. No usa
generación de imágenes ni da coordenadas desde miniaturas.

## Procesamiento y orientación

`documentation_images.process_image` se ejecuta dentro del catálogo compartido
por generación y diagnóstico, después de las comprobaciones existentes de lote,
pertenencia, tipo, tamaño y descarga con redirecciones y credenciales acotadas.
Verifica estructura y decodifica el original antes de recortar. Comprueba hash
y dimensiones exactos y aborta antes de Claude ante discrepancias, sin fallback.

No aplica rotación EXIF. Para un recorte solo admite orientación ausente o 1;
rechaza 2–8 y valores desconocidos, incluso si ancho y alto no cambian. Esto evita
que una vista autoorientada produzca coordenadas incompatibles. Para usar una
imagen orientada, prepara una copia normalizada y repite inspección/aprobación
con los bytes de esa copia. Una selección sin recorte conserva los bytes exactos
y los metadatos originales, incluida su orientación.

Pillow está fijado en `.github/requirements-documentation.txt`. El recorte genera
PNG sin pérdida con compresión fija, sin redimensionado ni retoques ni gestión de
color. Para JPEG se conservan los píxeles decodificados sin recomprimir JPEG.
Paletas y transparencia se representan con colores equivalentes RGB/RGBA cuando
hace falta. Se rechazan PNG de 16 bits y modos que perderían precisión. El
derivado se crea desde píxeles en una imagen nueva para eliminar EXIF, ICC,
comentarios y DPI. Para capturas que dependan de un perfil ICC, prepara y revisa
previamente un original apropiado. No se altera el adjunto original de Jira.

Los límites son diez imágenes, 2.000.000 bytes por archivo, 8.000.000 por lote y
20.000.000 píxeles por imagen, tanto para originales como para resultados.
Se rechazan archivos multiframe y decodificaciones malformadas o excesivas;
las advertencias de bomba de descompresión son errores. Las selecciones y
catálogos anteriores siguen siendo válidos. Las dependencias se instalan desde
el manifiesto extraído del SHA capturado, antes de importar/procesar imágenes y
antes de exponer credenciales. Los dos jobs conservan el staging de confianza.

## Trazabilidad y archivos

En el catálogo, `original` contiene `width`, `height`, `size`, `mime_type` y
`sha256` del adjunto. Los campos superiores con esos nombres describen los bytes
publicados. `crop` conserva el rectángulo vinculado al original. El validador
comprueba los tipos, relaciones entre ambas dimensiones, hash del archivo y
decodificación real; preparación de PR vuelve a verificar los archivos e incluye
la trazabilidad en su descripción.

La ruta conserva `static/img/jira/<ticket>-<id>-<sha256-resultado>.png` (o `.jpg`
para JPEG sin recorte). Mismo contenido derivado produce la misma ruta; resultados
distintos no colisionan. Dos recortes que produzcan bytes idénticos pueden
compartir ruta legítimamente entre ejecuciones. No se sobrescriben archivos
preexistentes: solo se reutilizan si están versionados e idénticos. Se mantiene
la aplicación atómica de documentos y binarios, con rollback ante fallo. El
catálogo y los archivos completos utilizados quedan en el artefacto de propuesta
para recuperación. Una abstención no incorpora imágenes al repositorio.

## Prueba real pendiente: diagnóstico primero

Estas instrucciones no autorizan ejecutar acciones externas. Las pruebas locales
usan imágenes sintéticas y transportes Jira/Claude simulados. No demuestran una
integración real ni el comportamiento de todas las cuentas de ChatGPT.

1. En un lote de prueba autorizado, prepara un original PNG/JPEG sin datos
   sensibles, muestra su preview en fase A y aprueba el plan. Tras adjuntarlo,
   verifica bytes, hash y dimensiones; registra `crop` con su ID real. Mantén
   evidencia textual suficiente y mide el lote con el bloque incluido.
2. Cuando este código esté disponible en una referencia de Actions, ejecuta
   **Documentation agent PoC** con esa referencia, `mode=diagnose-images`,
   `issue_key` y `issue_summary` de la solicitud, `jira_epic_key` y
   `jira_task_keys` del lote autorizado. En modo estructurado se lee la
   descripción canónica de la solicitud desde Jira; `issue_description` puede
   estar vacío en diagnóstico. Las fuentes deben cumplir el contrato existente.
3. Descarga el artefacto `documentation-image-diagnostic-<run_id>-<attempt>`.
   Comprueba `status=success`, identidades, `images_count`, `total_bytes`,
   `original_total_bytes` y por imagen `original`, `crop`, dimensiones/tamaño/hash
   superiores y `validation=valid`. El informe usa una allowlist explícita, sin
   textos de tickets, credenciales, URLs firmadas ni binarios. Los temporales se
   eliminan al terminar. Un fallo produce `technical_error` sin detalles sensibles;
   no llega a Claude, publicación ni notificación. Corrige errores antes de seguir.
4. Con autorización independiente para ejecutar el agente y este código en
   `main` (la generación usa `main`), dispara una vez el mecanismo existente
   verificado para esa solicitud. Si se usa el formulario autorizado, selecciona
   `mode=generate` y aporta también `issue_description` no vacío según el contrato
   del job. Revisa decisión, catálogo, artefactos, validación, PR y preview; no
   deduzcas éxito solo por un job verde ni vuelvas a disparar automáticamente.
5. Revisa visualmente que el PNG derivado elimina solo interfaz externa, mantiene
   contexto del producto y se renderiza tanto en producción como en preview.
   Compara los binarios recuperados con sus hashes. Merge y publicación siguen
   requiriendo el procedimiento de revisión existente.

## Actualizar la skill en ChatGPT

Sustituye exactamente estos recursos de `skills/create-documentation-epic/`:

- `SKILL.md`
- `references/imagenes-publicacion.md`
- `references/plantillas.md`
- `references/ejecucion-y-seguimiento.md`
- `references/escenarios-prueba.md`

El resto de recursos y el medidor no cambia. Si la distribución usa un paquete
completo, vuelve a empaquetar la carpeta conservando también los recursos sin
cambios; los scripts del agente y su manifiesto permanecen en el repositorio.

## Inventario del cambio

- Procesamiento y validación compartida: `.github/scripts/documentation_images.py`.
- Generación y diagnóstico: `.github/scripts/generate-documentation-proposal.py`.
- Preparación de PR: `.github/scripts/prepare-documentation-pull-request.py`.
- Contrato textual del modelo: `.github/prompts/documentation-agent-poc.md`.
- Jobs y dependencia fijada: `.github/workflows/documentation-agent-poc.yml` y
  `.github/requirements-documentation.txt`.
- Pruebas del agente: `.github/scripts/tests/test_documentation_crops.py`,
  `.github/scripts/tests/test_documentation_images.py` y
  `.github/scripts/tests/test_documentation_agent_workflow.py`.
- Renderizado y guía de pruebas: `tests/jira-images-build.cjs` y `tests/README.md`.
- Skill: los cinco recursos enumerados en la sección anterior.
- Documentación interna: `project-docs/README.md` y esta guía.
- Exclusión de dependencias locales de validación: `.gitignore`.

El validador de propuestas consume la validación y verificación de binarios del
módulo compartido; no necesita duplicar la implementación del recorte.
