# Validación del Centro de Ayuda

Requiere Node 24 y Python 3. Ejecutar desde la raíz:

```sh
npm ci
python -B -m unittest discover -s tests
python -B -m unittest discover -s .github/scripts/tests
npm run build
node tests/verify-help-center-build.cjs
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

`fixtures/public-docs-sha256.json` fija el contenido original de los 24 artículos y
los ocho índices, normalizando únicamente CRLF/LF. Solo debe actualizarse ante una
migración documental aprobada, nunca para hacer pasar un cambio de interfaz.

La suite histórica exige que `docs/production-snapshots/` no exista. Si hay
snapshots locales previos, esa prueba falla aunque el build los excluya. No deben
eliminarse datos locales para ocultar ese fallo.

El plugin `@cmfcmf/docusaurus-search-local` utiliza Lunr y componentes de
autocomplete como dependencias transitivas. No configura el servicio Algolia ni
envía consultas fuera del sitio. El índice se genera únicamente en producción;
la búsqueda no funciona con `npm run start`.
