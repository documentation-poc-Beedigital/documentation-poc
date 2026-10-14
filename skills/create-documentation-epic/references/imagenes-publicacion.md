# Seleccionar imágenes para la propuesta documental

## Fase A: revisar la selección

Distingue adjuntos de **evidencia** e imágenes destinadas a **publicación**. Una captura que ayuda a contrastar hechos no tiene por qué aparecer en el artículo. Propón solo imágenes que ayuden a localizar una opción, completar un paso o reconocer un resultado. Excluye de publicación las obsoletas, contradictorias, duplicadas o decorativas; conserva la evidencia y sus discrepancias en el contexto textual.

Inspecciona los archivos accesibles antes de describirlos. Registra qué has inspeccionado y qué no; no afirmes que una imagen está revisada si solo conoces su nombre. Si contiene datos personales, credenciales o información sensible, solicita una versión adecuada para publicación y conserva ese pendiente. No incluyas la original en la selección pública ni asumas que el workflow la anonimizará. PNG y JPEG son los únicos formatos admitidos.

En el plan completo muestra, por imagen: archivo/localizador, finalidad (evidencia o publicación), motivo, ticket previsto, ubicación junto al paso correspondiente, descripción observada y texto alternativo. En A usa identificadores locales explícitamente provisionales; no inventes claves ni IDs Jira. CREAR sigue aprobando únicamente las acciones del plan mostrado y su destino, incluidos los adjuntos seleccionados. No autoriza ejecutar el agente.

## Fase B: registrar identidades verificadas

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

Las claves/IDs del ejemplo no son valores del entorno. Cada entrada contiene exactamente los seis campos mostrados, todos cadenas. `version` es el entero `1`; `attachment_id` es una cadena decimal positiva sin ceros iniciales. `issue_key` cumple el contrato de claves Jira vigente. Descripción, alt, placement y reason son textos no vacíos, sin saltos de línea ni caracteres de control, hasta 2.000 caracteres; alt es texto plano sin corchetes ni barras invertidas. No se permiten campos adicionales, claves JSON repetidas, URLs ni destinos. La misma pareja ticket/ID aparece una sola vez en el lote: coloca el registro en una descripción y referencia su identidad desde las otras en prosa.

El lote permite hasta diez imágenes, 2.000.000 bytes por archivo y 8.000.000 bytes en total; las dimensiones no pueden superar 20.000.000 píxeles. Si excede esos límites, solicita versiones adecuadas o reduce la selección aprobada. Un lote sin bloque mantiene el comportamiento anterior; `images: []` también es válido.

No mezcles este contrato con `DOCUMENTATION_SOURCE_V1` ni cambies `jira_epic_key`/`jira_task_keys`. En modo legado el manifiesto sigue siendo toda la descripción de la tarea documental; coloca la selección en la descripción de la épica o de una Task autorizada. Si el conector usa ADF, emplea un codeBlock con `attrs.language="documentation-images-v1"` y JSON literal como texto, o un bloque Markdown literal conservado íntegro por la conversión. No añadas el marcador suelto en prosa.

## Qué recibirá la propuesta

El workflow consulta metadatos `attachment` de los tickets del lote validado, recupera solo los IDs elegidos, valida archivo/tamaño y crea nombres estables con ticket, ID y SHA-256. El modelo recibe un catálogo textual con identidad, ruta, descripción, ubicación, motivo y alt. Usa imágenes relevantes junto a los pasos; puede omitirlas. Solo las utilizadas se aplican con los Markdown en la misma transacción y PR. No se publican binarios en abstención.

La revisión humana comprueba privacidad, vigencia y correspondencia visual con el recorrido: la validación técnica no certifica estos hechos. El diagnóstico existente comprueba el contexto textual y no descarga ni valida píxeles. El artefacto de propuesta conserva catálogo, hashes y archivos completos de los documentos e imágenes utilizados; una captura omitida puede constar en el catálogo disponible, pero su binario no se incorpora.
