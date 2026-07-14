# takeout-metadata-writer

Restaura las fechas reales de captura y subida de fotos y videos exportados desde
Google Takeout, usando los metadatos contenidos en los archivos JSON complementarios
que Google incluye en la exportación.

## Motivación

Cuando exportás tus fotos de Google Photos mediante Takeout, los archivos resultantes
pierden sus fechas originales:

- La **fecha de creación** del archivo es la fecha en que se generó el Takeout.
- La **fecha de modificación** es la fecha en que se escribió en disco.

Esto hace imposible ordenar cronológicamente las fotos con el explorador de archivos.
Afortunadamente, Google incluye un archivo JSON por cada foto con dos fechas clave:

- `photoTakenTime` → la fecha real de captura.
- `creationTime` → la fecha de subida a Google Photos.

## Funcionalidades

- **Escaneo recursivo**: procesa una carpeta de Takeout descomprimida completament.
- **Emparejamiento inteligente**: localiza el JSON complementario para cada archivo
  multimedia siguiendo el patrón de nomenclatura de Google.
- **Resumen previo**: muestra un informe de lo que se va a modificar antes de
  escribir.
- **Restauración de fechas**: setea la fecha de creación del archivo con
  `photoTakenTime` y la fecha de modificación con `creationTime`.
- **Interfaz TUI**: interfaz de terminal simple para operar sin complicaciones.

## Uso

```bash
# Modo resumen (solo muestra lo que se haría)
python -m takeout_metadata_writer /ruta/al/takeout --dry-run

# Modo escritura (aplica los cambios)
python -m takeout_metadata_writer /ruta/al/takeout
```

## Estructura de archivos esperada

```
Takeout/
├── Google Photos/
│   ├── 2007/
│   │   ├── DSC01449.JPG
│   │   ├── DSC01449.JPG.supplemental-metadata.json
│   │   ├── VID_20210101_123456.mp4
│   │   └── VID_20210101_123456.mp4.supplemental-metadata.json
│   └── ...
└── ...
```

## Stack técnico

- **Python 3.10+**
- **Sin dependencias externas** — usa solo la biblioteca estándar para el
  procesamiento principal.
- **Opcional**: `pyexiv2` o `Pillow` para escribir metadatos EXIF en una fase
  futura.
- TUI construida con la biblioteca estándar (`argparse`, `os`, `pathlib`, `json`,
  `datetime`, `stat`, etc.).

## Licencia

MIT
