# Validación del Centro de Ayuda

Requiere Node 24 y Python 3. Ejecutar desde la raíz:

```sh
npm ci
python -m pip install -r .github/requirements-documentation.txt
python -B -m unittest discover -s tests
python -B -m unittest discover -s .github/scripts/tests
npm run build
node tests/verify-help-center-build.cjs
node --test tests/jira-images-build.cjs
node --test tests/documentation-navigation-build.cjs
npm run serve -- --host 127.0.0.1 --no-open
```

Con el servidor activo, ejecutar `node tests/help-center-browser.cjs` en otra
terminal. Requiere Playwright y Chrome local. `PLAYWRIGHT_MODULE` permite apuntar
a una instalación de Playwright fuera del proyecto; no es una dependencia del
sitio. `UI_BROWSER` permite elegir otro canal de Chromium instalado.
`UI_SCREENSHOT_DIR` habilita capturas, preferiblemente en una carpeta temporal.
`HELP_CENTER_URL` permite cambiar la URL local. Detener el servidor al terminar.

La prueba de navegador comprueba escritorio y móvil en ambos temas, logos,
desbordamiento horizontal, búsqueda en español, límite de resultados, navegación
con teclado y ausencia de peticiones externas. La prueba del build recorre enlaces
y anclas, verifica las 32 URLs documentales e impide publicar documentos internos,
snapshots y PDF. Revisar también las capturas visualmente.

El recorte usa Pillow fijado en el manifiesto Python. La suite de imágenes y
`test_documentation_crops.py` comprueban píxeles sintéticos, EXIF, discrepancias,
trazabilidad y binarios recuperables con transportes simulados. El render de
`jira-images-build.cjs` usa un PNG recortado por el código real bajo ambas bases
URL. Los escenarios de la skill son un guion de evaluación manual, no una prueba
de integración ejecutada. Véase [recortes y prueba real](../project-docs/recortes-capturas.md).

`fixtures/public-docs-sha256.json` fija el contenido original de los 24 artículos y
los ocho índices, normalizando únicamente CRLF/LF. Solo debe actualizarse ante una
migración documental aprobada, nunca para hacer pasar un cambio de interfaz.

`jira-images-build.cjs` construye un artículo temporal con una imagen Jira bajo
`/documentation-poc/` y `/` (preview), verifica el HTML, alt y archivo servido.
No modifica artículos reales ni llama a Jira o Claude. La suite Python de
`.github/scripts/tests/test_documentation_images.py` simula selección, descarga,
validación, aplicación atómica, publicación y recuperación de binarios.

La regresión sintética de DOC-104 en esa suite comprueba la precedencia de la
solicitud ADF obtenida por API sobre el texto de Automation sin identificador,
la lectura de solicitud, épica y seis tareas, y una petición capturada con cuatro
imágenes y URLs deterministas. La propuesta simulada verifica referencias Markdown
y binarios recuperables, sin red ni secretos reales. `diagnose-context` verifica
el contexto textual; `diagnose-images` descarga y valida el catálogo compartido
con generación, sin Claude ni acciones de publicación o notificación. Véanse
los inputs exactos de DOC-104 y la descarga del informe en
[el flujo del agente](../project-docs/flujo-agente-documentacion.md#diagnóstico-manual-de-imágenes-después-del-merge).

La suite histórica exige que `docs/production-snapshots/` no exista. Si hay
snapshots locales previos, esa prueba falla aunque el build los excluya. No deben
eliminarse datos locales para ocultar ese fallo.

El plugin `@cmfcmf/docusaurus-search-local` utiliza Lunr y componentes de
autocomplete como dependencias transitivas. No configura el servicio Algolia ni
envía consultas fuera del sitio. El índice se genera únicamente en producción;
la búsqueda no funciona con `npm run start`.
