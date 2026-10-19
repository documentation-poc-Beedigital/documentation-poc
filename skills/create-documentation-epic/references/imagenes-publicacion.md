# Seleccionar imágenes para la propuesta documental

## Fase A: revisar la selección

Distingue adjuntos de **evidencia** e imágenes destinadas a **publicación**. Una captura que ayuda a contrastar hechos no tiene por qué aparecer en el artículo. Propón solo imágenes que ayuden a localizar una opción, completar un paso o reconocer un resultado. Excluye de publicación las obsoletas, contradictorias, duplicadas o decorativas; conserva la evidencia y sus discrepancias en el contexto textual.

Inspecciona los archivos accesibles antes de describirlos. Registra qué has inspeccionado y qué no; no afirmes que una imagen está revisada si solo conoces su nombre. Si contiene datos personales, credenciales o información sensible, solicita una versión adecuada para publicación y conserva ese pendiente. No incluyas la original en la selección pública ni asumas que el workflow la anonimizará. PNG y JPEG son los únicos formatos admitidos.

En el plan completo muestra, por imagen: archivo/localizador, finalidad (evidencia o publicación), motivo, ticket previsto, ubicación junto al paso correspondiente, descripción observada y texto alternativo. En A usa identificadores locales explícitamente provisionales; no inventes claves ni IDs Jira. CREAR sigue aprobando únicamente las acciones del plan mostrado y su destino, incluidos los adjuntos seleccionados. No autoriza ejecutar el agente.

### Recortes revisables dentro del plan A

Antes de escribir en Jira, comprueba el acceso a los bytes originales, su visualización y una herramienta de recorte real (por ejemplo Pillow). No presupongas estas capacidades en todas las cuentas de ChatGPT. Una miniatura o vista redimensionada no sirve para obtener coordenadas. Si faltan acceso visual o herramientas de recorte, explica la limitación y ofrece continuar con el original o pedir una captura preparada; no registres un recorte no inspeccionado.

Inspecciona cada original y propón quitar únicamente interfaz ajena al producto: pestañas, barra de direcciones, marcadores, barra de tareas del sistema y bordes externos innecesarios. Conserva cabeceras de Beesible, navegación del producto, botones, avisos y contexto funcional. Una captura limpia o móvil puede no necesitar recorte. No uses porcentajes fijos, coordenadas inventadas, nombres, alt o descripciones para decidir límites. Ante un borde dudoso conserva el original y marca la revisión pendiente.

Calcula SHA-256 sobre los bytes originales y mide sus dimensiones. El sistema usa coordenadas del raster original sin rotación automática; para recortar exige EXIF ausente o igual a 1. Con otra orientación, conserva el original sin recorte u ofrece una copia normalizada: será un nuevo original, con nueva inspección, hash, dimensiones y aprobación del plan. No transformes silenciosamente coordenadas de una vista autoorientada.

Prepara la preview mediante un recorte real del original con `(left, top, right, bottom)` enteros en píxeles, límites derecho e inferior exclusivos. Por ejemplo, `Image.open(original).crop((left, top, right, bottom))` tras comprobar orientación y dimensiones. No redimensiones, retoques ni uses generación de imágenes para reconstruir capturas. Presenta esa preview y su motivo dentro del plan A, junto con archivo, dimensiones originales, SHA-256, coordenadas, alt y ubicación. La aprobación del plan incluye los recortes mostrados: no solicites confirmaciones redundantes. Conserva estos datos y la versión aprobada del plan en continuidad. Si cambias materialmente los límites, revisa el cambio antes de escribirlo.

## Fase B: registrar identidades verificadas

### Verificar el original definitivo

Adjunta el original inspeccionado intacto; el agente generará el derivado. Antes de guardar `crop`, recupera los bytes del adjunto definitivo con herramientas autorizadas y compara SHA-256 y dimensiones con el archivo inspeccionado. No basta el nombre o tamaño. Si no coinciden o no puedes verificarlo, no registres ese recorte: conserva el pendiente y resuelve el acceso o revisa el nuevo original. No modifiques ni elimines el adjunto original de Jira. No envíes una preview recortada como original con coordenadas del archivo previo.

Adjunta dentro de la autorización a la épica documental o a una Task hija directa incluida en el lote. Si la imagen solo está en un ticket original ajeno al lote, su ID no es válido para publicación: prepara una copia en un ticket documental autorizado y verifica su nuevo ID. No cambies tickets originales. Si faltan herramientas de adjuntos, conserva el paso pendiente; no añadas clientes ni autenticación.

Recupera el inventario del ticket después de cargar. Registra la clave y el **ID real del adjunto**, nombre, tipo y tamaño. Dos archivos llamados `captura-001.png` son identidades distintas. No uses el nombre como identificador ni infieras el ID desde una URL. Ante timeout, consulta antes de volver a adjuntar.

Materializa la selección aprobada con el contrato siguiente y vuelve a leer la descripción convertida para verificar que el bloque llega intacto. Mantén los hechos importantes en prosa: el agente recibe descripciones y catálogo, no píxeles ni comentarios. Mide de nuevo el lote, incluido el bloque. Verifica todo antes de solicitar la autorización independiente de ejecución.

## Contrato `documentation-images-v1`

En una descripción humana del modo estructurado, o en la descripción de la épica/Task recuperada de Jira, añade **un único bloque de código** con lenguaje `documentation-images-v1` y JSON estricto:

````markdown
```documentation-images-v1
{
  "version": 1,
  "images": [
    {
      "issue_key": "APP-124",
      "attachment_id": "10423",
      "description": "Formulario vigente con el botón Guardar debajo de las preferencias.",
      "alt": "Preferencias con el botón Guardar",
      "placement": "Junto al paso de guardar las preferencias",
      "reason": "Ayuda a localizar la acción final"
    }
  ]
}
```
````

Las claves/IDs del ejemplo no son valores del entorno. Cada entrada contiene los seis campos mostrados, todos cadenas, y opcionalmente `crop`. `version` es el entero `1`; `attachment_id` es una cadena decimal positiva sin ceros iniciales. `issue_key` cumple el contrato de claves Jira vigente. Descripción, alt, placement y reason son textos no vacíos, sin saltos de línea ni caracteres de control, hasta 2.000 caracteres; alt es texto plano sin corchetes ni barras invertidas. No se permiten otros campos adicionales, claves JSON repetidas, URLs ni destinos. La misma pareja ticket/ID aparece una sola vez en el lote: coloca el registro en una descripción y referencia su identidad desde las otras en prosa.

El lote permite hasta diez imágenes, 2.000.000 bytes por archivo y 8.000.000 bytes en total; las dimensiones no pueden superar 20.000.000 píxeles. Si excede esos límites, solicita versiones adecuadas o reduce la selección aprobada. Un lote sin bloque mantiene el comportamiento anterior; `images: []` también es válido.

No mezcles este contrato con `DOCUMENTATION_SOURCE_V1` ni cambies `jira_epic_key`/`jira_task_keys`. En modo legado el manifiesto sigue siendo toda la descripción de la tarea documental; coloca la selección en la descripción de la épica o de una Task autorizada. Si el conector usa ADF, emplea un codeBlock con `attrs.language="documentation-images-v1"` y JSON literal como texto, o un bloque Markdown literal conservado íntegro por la conversión. No añadas el marcador suelto en prosa.

## Qué recibirá la propuesta

El workflow consulta metadatos `attachment` de los tickets del lote validado, recupera solo los IDs elegidos, valida archivo/tamaño y crea nombres estables con ticket, ID y SHA-256. El modelo recibe un catálogo textual con identidad, ruta, descripción, ubicación, motivo y alt. Usa imágenes relevantes junto a los pasos; puede omitirlas. Solo las utilizadas se aplican con los Markdown en la misma transacción y PR. No se publican binarios en abstención.

La revisión humana comprueba privacidad, vigencia y correspondencia visual con el recorrido: la validación técnica no certifica estos hechos. `diagnose-context` comprueba el contexto textual sin descargar píxeles. `diagnose-images` comparte la descarga, validación y recorte de producción; informa identidades, cantidades, coordenadas y metadatos originales/derivados seguros sin Claude, publicaciones ni notificaciones, y elimina los temporales al terminar. El artefacto de propuesta conserva catálogo, hashes y archivos completos de los documentos e imágenes utilizados; una captura omitida puede constar en el catálogo disponible, pero su binario no se incorpora.

## Extensión opcional de recorte (versión 1)

Añade solo este campo a una entrada aprobada cuando se haya revisado su preview:

```json
{
  "crop": {
    "left": 12,
    "top": 96,
    "right": 1420,
    "bottom": 860,
    "original_width": 1440,
    "original_height": 900,
    "original_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  }
}
```

Son coordenadas ilustrativas; nunca las apliques a una captura sin inspeccionarla.
`crop` contiene exactamente esos siete campos. Los seis valores numéricos son
enteros JSON (no booleanos, decimales ni cadenas); el hash es hexadecimal minúsculo
de 64 caracteres. Se exige `0 <= left < right <= original_width` y
`0 <= top < bottom <= original_height`, dimensiones positivas y hasta 20.000.000
píxeles. `right` y `bottom` son exclusivos: el ejemplo produciría 1408×764 píxeles.
Las coordenadas pertenecen al archivo original exacto, nunca a una miniatura,
versión redimensionada o archivo diferente. `crop: null` no es válido; omite el
campo para publicar el original. Las selecciones anteriores siguen funcionando.

El agente valida el original y comprueba hash y dimensiones antes de recortar y
antes de Claude; cualquier discrepancia aborta sin fallback. No rota ni aplica
EXIF automáticamente: admite orientación ausente o igual a 1 y rechaza las demás.
Rechaza archivos malformados, multiframe, excesivos y recortes de PNG de 16 bits
o modos que requerirían perder precisión. Decodifica PNG/JPEG y aplica solo el
rectángulo; deriva PNG sin pérdida, sin redimensionado ni retoque. El JPEG se
decodifica una vez, sin recompresión JPEG. Convierte paleta/transparencia a
colores equivalentes cuando hace falta y elimina EXIF, ICC, comentarios y DPI;
no aplica gestión de color. Si se necesita fidelidad a un perfil ICC, prepara
antes un original apropiado y revísalo. El original de Jira permanece intacto.

En el catálogo `original` contiene `width`, `height`, `size`, `mime_type` y
`sha256` del archivo descargado. Los campos superiores `width`, `height`, `size`,
`mime_type` y `sha256` describen el archivo publicado. `crop` conserva la selección
aprobada. Sin recorte, ambos conjuntos coinciden y los bytes se conservan.
La ruta usa ticket, ID y hash del resultado; se reutiliza solo un archivo idéntico
ya controlado, nunca se sobrescribe otro. Los límites de bytes se comprueban
independientemente para originales y derivados. Catálogo, Markdown y binarios
utilizados se conservan en artefactos recuperables, con aplicación atómica junto
a los documentos. Claude recibe únicamente el catálogo textual ya transformado.
