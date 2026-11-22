# opnflash-datos

Datos públicos que muestra [opnflash.com](https://www.opnflash.com). Se actualizan solos cada hora con GitHub Actions y se sirven con GitHub Pages en `https://openphenomena.github.io/opnflash-datos/datos/`.

- `datos/portada.json`: datos del mapa (sismos, alertas, eventos naturales, clima espacial, satélites).
- `datos/titulares.json`: titulares de medios (solo titular, medio, hora y enlace).
- `datos/capas.json`: capas del modo Experto.
- `datos/directos.json`: señales de vídeo en directo.
- `datos/traducciones.json`: traducciones automáticas de titulares.

Cada dato conserva su fuente y su licencia; la lista completa está en https://www.opnflash.com/fuentes.html.

`herramientas/` contiene los programas que recogen los datos y `referencia/` las listas de fuentes.
