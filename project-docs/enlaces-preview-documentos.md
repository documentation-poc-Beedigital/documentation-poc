# Enlaces a documentos en la preview

La descripción se genera en `.github/scripts/prepare-documentation-pull-request.py`.
Conserva los metadatos editoriales y añade un bloque HTML gestionado bajo cada
documento, además de un bloque para la preview general. No cambia propuestas,
prompt, skill ni contenido publicado.

## Fuente del despliegue

Se revisó el comentario real de Cloudflare en la
[PR #121](https://github.com/documentation-poc-Beedigital/documentation-poc/pull/121#issuecomment-6609827215).
La app `cloudflare-workers-and-pages` (85455), mediante su bot (73139402), publica
una tabla con `Latest commit`, `Status`, `Preview URL` y `Branch Preview URL`.
Se utiliza únicamente `Preview URL`, la URL inmutable anunciada por la app.
El alias de rama puede cambiar de despliegue y no sirve para fijar un commit.
La [integración oficial](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
documenta los comentarios de preview y los checks de los builds. Los workflows
existentes de GitHub Pages solo despliegan `main`; no generan estas previews.

## Rutas y comprobación del commit

El plugin `src/plugins/document-preview-routes.cjs` escribe
`document-preview-routes.json` en la raíz del build. Recoge `source` y `permalink`
del contenido cargado por Docusaurus: incluye artículos nuevos, actualizados e
índices, y respeta `slug`, `routeBasePath`, `baseUrl` y `trailingSlash`.
Aplica `applyTrailingSlash` de Docusaurus, igual que su router: el permalink de
los metadatos todavía puede no tener esa normalización final.
No deriva URLs de los nombres de archivo. Los borradores no se enlazan.
El manifiesto incluye el SHA completo de `CF_PAGES_COMMIT_SHA`, variable
proporcionada por Cloudflare Pages durante el build.

El actualizador exige que el comentario se refiera al head actual y que el
manifiesto contenga exactamente su SHA completo. Una URL antigua, una ejecución
fallida o pendiente, una ruta ausente o un manifiesto no verificable nunca se
presentan como preview vigente. Los enlaces apuntan al artículo completo.

## Ejecución y permisos

`document-preview-links.yml` reacciona a apertura, reapertura y nuevos commits
de PR, y a creación/edición del comentario de Cloudflare. No sondea: cada evento
hace una lectura acotada y una descarga con timeout. Permite recuperación manual
con `workflow_dispatch` y `pr_number`. Si la descarga no está disponible todavía,
se indica como no verificable hasta otro evento o una ejecución manual.

## Diagnóstico de la descarga

La [ejecución 41840378248](https://github.com/documentation-poc-Beedigital/documentation-poc/actions/runs/41840378248)
terminó correctamente, pero solo registró `Preview no verificable: HTTPError`.
Ese log no permite recuperar el código HTTP ni distinguir un rechazo de acceso,
un archivo ausente o una redirección. No demuestra que sean necesarias credenciales.

El diagnóstico utiliza códigos y mensajes controlados: `http_error` con código
HTTP, `redirect_rejected`, `connection_error`, `timeout`, `invalid_json`,
`incompatible_manifest` y `sha_mismatch`. No registra cuerpos de respuesta,
destinos de redirección, cookies, cabeceras ni texto libre de excepciones.
La descarga sigue sin enviar el token de GitHub y rechaza las redirecciones
antes de seguirlas. No se añaden credenciales ni se modifican controles de acceso.

El resumen de Actions distingue enlaces actualizados, vigentes sin cambios,
pendientes, no verificables y escrituras omitidas por cambios concurrentes.
También aclara si se modificó la descripción de la PR: retirar enlaces antiguos
para mostrar un error no equivale a verificar una preview. Los estados pendientes
o no verificables emiten un aviso. El verde del job solo indica que el proceso
terminó. El paso expone `preview_status` y `body_changed` como outputs.

Solo procesa PR abiertas de `github-actions[bot]`, del propio repositorio, con
rama `automation/documentation-*`. El job privilegiado utiliza exclusivamente
código de la rama predeterminada. Nunca ejecuta código ni instala dependencias
de la PR. Lee comentarios y datos de PR con `GITHUB_TOKEN`, y requiere
`pull-requests: write`, `contents: read` e `issues: read`; no necesita token de
Cloudflare, permisos de checks, deployments ni secretos nuevos.

Las ediciones se limitan a los bloques `document-preview:*`. Las PR anteriores
sin bloques se adoptan añadiendo slots junto a sus rutas sin regenerar títulos,
versiones, motivos ni evidencias. Se conserva el texto humano externo. Una
segunda lectura de la PR descarta la escritura si cambiaron el SHA o el body.
La API de GitHub no ofrece una operación atómica de comparación y escritura del
body; queda una pequeña ventana de concurrencia entre esa lectura y el PATCH.

## Comprobación manual con Python y curl

El workflow `Diagnose preview manifest (read only)` se activa únicamente mediante
`workflow_dispatch`. Una vez disponible en Actions, se puede ejecutar manualmente
desde su pantalla. Prepararlo no lo ejecuta ni modifica las protecciones.
Su URL es fija:
`https://fdbe23fb.documentation-poc.pages.dev/document-preview-routes.json`.

Primero vuelve a consultar en GitHub el head de la PR #121 y el comentario de la
app Cloudflare, sin escribir en la PR. En la comprobación de preparación, el head
era `c76c8420bcd7ec27ec03cfa7e5c538efb8dd2c2b`, el comentario indicaba `c76c842`
y anunciaba exactamente ese despliegue. Si cambia el head, el diagnóstico de la
URL fija sigue siendo útil, pero no se presenta como preview vigente.

El segundo paso no recibe `GH_TOKEN`. Ejecuta desde el mismo runner un GET con
el opener urllib y la política de redirecciones del actualizador, y otro con
curl. Este último ignora `.curlrc`, desactiva netrc y descarta el cuerpo en el
dispositivo nulo. No usa cookies ni credenciales. Las cabeceras recibidas por
curl se capturan en memoria y se filtran antes de imprimir o guardar el resumen.
No se publican logs brutos ni artefactos de respuestas. No hay sondeo ni reintentos.

El resumen compara solo el código HTTP y `Content-Type`, `Server`, `cf-ray` y
`cf-mitigated`, además del estado controlado de conexión/redirección. Ninguno de
estos GET valida el JSON ni el SHA interno: un HTTP 200 no implica verificación
del manifiesto.

| Resultado observado | Qué permite distinguir |
| --- | --- |
| Python 403, curl 200 | Diferencia dependiente del cliente en el mismo runner; aún no distingue User-Agent, TLS u otra señal. |
| Ambos 403 y `cf-mitigated: challenge` | Cloudflare está devolviendo un challenge, no el JSON esperado. |
| Ambos 403 sin esa cabecera | El código por sí solo no demuestra falta de credenciales ni una regla concreta; correlacionar los `cf-ray` con los eventos existentes de Cloudflare. |
| Ambos 200 | El fallo no se reproduce en ese runner y momento; contrastar con el evento original. |
| 3xx | Hay una redirección que ambos clientes deben rechazar; no se imprime su destino. |
| Sin código HTTP | El fallo ocurrió en conexión, TLS o timeout, antes de una respuesta HTTP utilizable. |

La [documentación de Cloudflare](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/)
identifica `cf-mitigated: challenge` como señal de Challenge Page y su tipo de
contenido como `text/html`. Que Edge InPrivate abra la URL no aísla la causa:
también cambian la red de origen y las características del cliente. La prueba
del mismo runner reduce esa incertidumbre sin cambiar reglas ni añadir secretos.

## Activación pendiente

1. Incorporar los cambios a la rama predeterminada mediante el proceso habitual.
   Los eventos `issue_comment` y `workflow_dispatch` necesitan el workflow allí.
2. El siguiente build de la rama de propuesta debe incluir el plugin. Las previews
   ya construidas no contienen el manifiesto y se indicarán como no verificables.
3. Mantener habilitados los comentarios de preview de la integración existente
   y los builds de las ramas `automation/documentation-*`. Si la organización
   restringe la escritura de PR por Actions, permitir `pull-requests: write` a
   este workflow. No hace falta ampliar permisos de la app Cloudflare.
4. Mantener `CF_PAGES_COMMIT_SHA` sin sobrescribir y el manifiesto accesible en
   la raíz del despliegue. Los entornos protegidos por Cloudflare Access necesitan
   una vía de lectura del manifiesto; sin ella se informa de preview no verificable.

No se ha cambiado la configuración remota ni ejecutado ningún despliegue.

## Validación local

```text
python -B -m unittest discover -s .github/scripts/tests -p test_document_preview_links.py
python -B -m unittest discover -s .github/scripts/tests -p test_prepare_documentation_pull_request.py
node --test tests/document-preview-routes-build.cjs
git diff --check
```

Las pruebas simulan el formato del comentario real, estados pendientes/fallidos,
SHA antiguo, manifiesto ausente/antiguo, identidad no fiable, actualización
repetida y edición humana concurrente. Los builds usan documentos temporales y
comprueban sus permalinks y HTML con bases personalizadas, slug e índices y ambos
valores de `trailingSlash`.
