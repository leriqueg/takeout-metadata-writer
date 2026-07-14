# Google Takeout — Análisis de Metadatos en Fotos

## Antecedentes

Google Takeout ofrece un proceso de exportación de los archivos almacenados en Google
Photos. El resultado son archivos comprimidos (`.tar.gz` o `.zip`) que contienen todos
los artefactos multimedia almacenados en la nube. Este proceso es la única manera de
descargar las fotos en masa, ya que **no residen en Google Drive** — aunque ocupan el
espacio de almacenamiento de la cuenta.

## Problema

Al descargar y descomprimir los archivos del Takeout, se genera una estructura de
directorios heredada de la aplicación legacy **Picassa**. Las carpetas se nombran con
lo que parece ser el año de la foto (no está claro si es el año de captura o de
subida). Pero hay un problema más grave:

- **Fecha de creación del archivo**: se setea a la fecha/hora en que se generó el
  Takeout.
- **Fecha de modificación del archivo**: se setea a la fecha/hora en que se escribió
  en el disco.

Esto significa que **se pierde la fecha original de la foto**. Algunos archivos
multimedia contienen metadatos EXIF con la fecha real de captura, pero otros no
dependiendo del dispositivo o configuración de la cámara.

## Metadatos disponibles

Dentro de las carpetas del Takeout existen archivos JSON con metadatos de Google.
Por cada foto hay un archivo `.json` adjunto con la siguiente estructura:

```json
{
  "title": "DSC01449.JPG",
  "description": "“Te voy a peinar hasta que quedes bien rosadito!!”",
  "imageViews": "75",
  "creationTime": {
    "timestamp": "1188399825",
    "formatted": "29 ago 2007, 3:03:45 p.m. UTC"
  },
  "photoTakenTime": {
    "timestamp": "1188399825",
    "formatted": "29 ago 2007, 3:03:45 p.m. UTC"
  },
  "geoData": { ... },
  "people": [{ "name": "Santiago Jose" }],
  "url": "https://photos.google.com/photo/AF1QipONId_..."
}
```

### Campos relevantes

| Campo | Descripción |
|---|---|
| `creationTime` | Fecha en que el archivo fue subido/subido a Google Photos (según análisis manual) |
| `photoTakenTime` | Fecha real de captura de la foto (dato confiable) |
| `title` | Nombre del archivo multimedia asociado |

## Solución propuesta

Un proyecto en Python con interfaz TUI (Terminal User Interface) básica que:

1. **Escanea recursivamente** una carpeta de Takeout descomprimido.
2. Por cada archivo multimedia, localiza su JSON complementario:
   - `IMG01244-20120712-1009.jpg`
   - `IMG01244-20120712-1009.jpg.supplemental-metadata.json`
3. Contrasta la metadata del archivo (EXIF, fechas del sistema) contra los valores
   del JSON.
4. Usa `photoTakenTime` como **fecha de creación real** del archivo.
5. Usa `creationTime` como **fecha de modificación** del archivo.
6. Expone un resumen previo a la escritura.
7. Como paso definitivo, **modifica la metadata del archivo original** seteando los
   valores correctos.

## Notas técnicas

- **`photoTakenTime`**: fecha real de captura → debe convertirse en fecha de creación
  del archivo.
- **`creationTime`**: fecha de subida a Google Photos → debe convertirse en fecha de
  modificación del archivo (útil para ordenar por subida).
- El proceso debe funcionar para fotos, videos y cualquier otro multimedia que Google
  Photos almacene.
- Los archivos JSON siguen el patrón de nomenclatura:
  `<nombre_archivo>.<extensión>.supplemental-metadata.json`
