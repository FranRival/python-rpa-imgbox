### 1. Links-obtener

### ¿Qué hace este script?

Este script realiza web scraping sobre el buscador de Poringa comenzando desde:

https://www.----.net/buscar/?q=%4---57

Recorre varias páginas usando paginación (`?p=1`, `?p=2`, etc.), extrae todos los enlaces que contengan:

/posts/imagenes/

Y guarda los resultados en:

links.txt

---

### Archivos necesarios

### Archivos de entrada

No necesita archivos externos.  
Toda la configuración está definida dentro del script.

### Librerías requeridas

El script requiere:

- requests  
- beautifulsoup4  

Instalación:

pip install requests beautifulsoup4

### Archivo generado

- links.txt → Contiene todos los enlaces encontrados (uno por línea).

---

### Proceso que realiza

1. Accede al buscador con la query `@Carls57`.  
2. Construye URLs paginadas usando `?p=1`, `?p=2`, etc.  
3. Realiza peticiones HTTP simulando navegador (User-Agent).  
4. Analiza el HTML con BeautifulSoup.  
5. Extrae todos los enlaces `<a>` que contengan `/posts/imagenes/`.  
6. Elimina duplicados automáticamente.  
7. Se detiene si:
   - Llega al límite de páginas (`MAX_PAGES`).  
   - Encuentra varias páginas sin enlaces nuevos (`MAX_EMPTY_PAGES`).  
   - O ocurre un error de conexión.  

---

### Resultado final

Genera un archivo llamado `links.txt` con todos los enlaces únicos encontrados, ordenados y listos para usar en otros procesos de automatización.


--------------------------------------

### 2.Descargar descargar.py

### ¿Qué hace este script?

Este script recorre múltiples carpetas dentro de un directorio base, analiza un archivo `source.html` en cada una y descarga automáticamente todas las imágenes detectadas en ese HTML.

Las imágenes se guardan dentro de la misma carpeta correspondiente.

---

### ¿Qué necesita?

- Una carpeta base (`BASE_DIR`) que contenga subcarpetas.
- Cada subcarpeta debe tener un archivo llamado `source.html`.
- Librerías:
  - requests
  - beautifulsoup4

Instalación:

pip install requests beautifulsoup4

---

### ¿Qué proceso realiza?

1. Recorre cada subcarpeta dentro de `BASE_DIR`.
2. Busca un archivo `source.html`.
3. Extrae todas las URLs de imágenes (`img src`, `data-src`, etc.).
4. Normaliza las URLs (corrige `//`, ignora rutas inválidas o base64).
5. Genera un `Referer` automático basado en el dominio de cada imagen.
6. Descarga las imágenes evitando duplicados.
7. Guarda cada imagen en su carpeta correspondiente.

---

### Resultado final

Cada carpeta que tenga `source.html` terminará con todas sus imágenes descargadas localmente.



### 2.Descargar /carpeta-superior/ descargar.py

### 1. Cambio de ruta base
- `BASE_DIR` ahora apunta a:
  C:\Users\dell\Downloads\marzo\aaa

---

### 2. Procesamiento recursivo
- Antes: recorría solo subcarpetas directas con `os.listdir`.
- Ahora: usa `os.walk(BASE_DIR)` → procesa carpetas de forma recursiva (incluye sub-subcarpetas).

---

### 3. Sistema de reintentos en descargas
- La función `descargar_imagen` ahora incluye:
  - Parámetro `reintentos=2`
  - Bucle de intentos automáticos
  - Espera de 1.5 segundos entre reintentos
- Mejora la tolerancia a fallos de red.

---

### 4. Timeout más controlado
- Antes: `timeout=40`
- Ahora: `timeout=(10, 20)` → separa tiempo de conexión y lectura.

---

### 5. Manejo de errores más robusto
- Se añadió try/except al leer `source.html`.
- Mejor control si el archivo está corrupto o no puede abrirse.

---

### 6. Pequeña mejora en descarga
- Se agrega `r.close()` explícito tras guardar la imagen.
- Se detiene escritura si `chunk` está vacío.

---

### Resumen general

Esta versión es más robusta, más tolerante a errores y capaz de procesar carpetas de forma recursiva.


### 3.Limpiar-img (ya es un ejecutable)

### ¿Qué hace este script?

Es una herramienta con interfaz gráfica (Tkinter) que limpia y organiza carpetas de posts.

- Aplana subcarpetas (mueve archivos al nivel principal).
- Detecta archivos basura (por nombre o tamaño).
- Mueve la basura a una carpeta llamada `basura`.

---

### ¿Qué necesita?

- Una carpeta raíz seleccionada manualmente desde la interfaz.
- Subcarpetas dentro de esa carpeta (cada una considerada un "post").
- Librerías estándar de Python (no requiere instalar paquetes externos).

Opcional:
- `icon.ico` si se empaqueta como `.exe` con PyInstaller.

---

### ¿Qué considera "basura"?

Un archivo es basura si:

- Pesa menos de 1024 bytes.
- Su nombre contiene patrones como:
  - apple
  - touch
  - icon
  - placeholder
  - sprite
  - thumb
  - logo
  - dimensiones tipo 300x250

---

### ¿Qué proceso realiza?

1. El usuario selecciona una carpeta raíz.
2. Recorre cada subcarpeta (post).
3. Aplana subcarpetas internas.
4. Elimina subcarpetas vacías.
5. Detecta archivos basura.
6. Mueve esos archivos a una carpeta global llamada `basura`.
7. Evita sobrescribir archivos agregando sufijos numerados.

---

### Resultado final

- Cada carpeta queda limpia y sin subcarpetas internas.
- Archivos pequeños o irrelevantes se mueven a `/basura`.
- Se muestra el progreso en una ventana con log visual.


### 4.Subir IMG-images2

- orquestador


---

### 5.extraer-images2

### ¿Qué hace este script?

Este script analiza un archivo Excel, extrae URLs específicas desde contenido HTML dentro de las celdas y las organiza ordenadamente en filas debajo de cada columna.

Solo extrae URLs que comiencen con:

https://images2.imgbox.com/

---

### ¿Qué necesita?

- Un archivo Excel llamado:
  
  10.xlsx

- La(s) pestaña(s) definidas en:

  SHEETS = ["Sheet1"]

- Librería:

  openpyxl

Instalación:

pip install openpyxl

---

### ¿Qué proceso realiza?

1. Abre el archivo Excel.
2. Recorre cada columna de la hoja indicada.
3. Lee el contenido HTML en la fila 2 de cada columna.
4. Extrae todas las URLs que coincidan con el patrón de ImgBox.
5. Borra datos antiguos debajo (desde fila 3 hacia abajo).
6. Escribe cada URL encontrada en filas consecutivas (desde fila 3).

---

### Resultado final

El mismo archivo Excel queda actualizado:

- Fila 2 → contiene el HTML original.
- Desde fila 3 hacia abajo → aparecen las URLs limpias y separadas.
- Solo se guardan enlaces de images2.imgbox.com.


### 5. Extraer-images2 Diferencias detectadas en esta versión limpiar-varios - 

### 1. Procesamiento por carpeta completa
- Antes: procesaba un único archivo definido como `10.xlsx`.
- Ahora: procesa automáticamente todos los archivos `.xlsx` dentro de una carpeta (`FOLDER_PATH`).

---

### 2. Cambio en la configuración
- Se reemplaza `EXCEL_FILE` por:
  
  FOLDER_PATH

- Se reemplaza `SHEETS = ["Sheet1"]` por:
  
  TARGET_SHEET = "Sheet1"

---

### 3. Nueva función `process_file()`
- Se añade una función intermedia para:
  - Abrir cada archivo.
  - Verificar si existe la hoja objetivo.
  - Procesarla.
  - Guardarla individualmente.

---

### 4. Búsqueda automática de archivos
- Usa `os.listdir(FOLDER_PATH)` para detectar todos los `.xlsx`.
- Ya no depende de un solo archivo fijo.

---

### 5. Mayor escalabilidad
- Permite procesar múltiples archivos Excel en lote.
- Ideal para automatización masiva.

---

### Resumen general

Esta versión convierte el script en una herramienta batch (procesamiento por lotes), capaz de limpiar múltiples archivos Excel automáticamente dentro de una carpeta.


### 5. Extraer-images2 / plural limpiar.py  

### Descripción del Script de Extracción de URLs (Versión Multi-Hoja)

### ¿Qué hace este script?

Este script abre un archivo Excel y extrae URLs de ImgBox desde varias hojas específicas, organizándolas en filas debajo de cada columna.

Extrae únicamente URLs que comiencen con:

https://images2.imgbox.com/

---

### ¿Qué necesita?

- Un archivo Excel llamado:

  batchproceso.xlsx

- Que contenga las siguientes hojas:

  batch1, batch2, batch3, batch4,  
  batch5, batch6, batch7, batch8,  
  febrero

- Librería:

  openpyxl

Instalación:

pip install openpyxl

---

### ¿Qué proceso realiza?

1. Abre el archivo Excel.
2. Recorre cada hoja definida en la lista `SHEETS`.
3. Verifica que la hoja exista.
4. En cada hoja:
   - Lee el HTML de la fila 2 en cada columna.
   - Extrae las URLs de images2.imgbox.com.
   - Borra datos antiguos desde la fila 3 hacia abajo.
   - Escribe las URLs encontradas en filas consecutivas.
5. Guarda el archivo sobrescribiendo el original.

---

### Resultado final

El mismo archivo `batchproceso.xlsx` queda actualizado:

- Cada hoja procesada contiene las URLs limpias.
- Fila 2 mantiene el HTML original.
- Desde fila 3 hacia abajo se listan las URLs extraídas.


---

### 6.construccio-figures

### ¿Qué hace este script?

Este script toma un archivo Excel con URLs organizadas por columnas y genera un nuevo archivo Excel donde convierte esas URLs en bloques HTML `<figure>` listos para WordPress.

---

### ¿Qué necesita?

- Archivo de entrada:

  10.xlsx

- Debe contener:
  - Fila 1 → nombre de carpeta (usado como atributo alt).
  - Desde fila 3 hacia abajo → URLs de imágenes.

- Librería:

  openpyxl

Instalación:

pip install openpyxl

---

### ¿Qué proceso realiza?

1. Abre el archivo Excel original.
2. Lee únicamente la hoja `Sheet1`.
3. Crea un nuevo archivo Excel.
4. Copia la fila 1 (nombres de carpeta).
5. Recorre las URLs desde la fila 3.
6. Construye bloques HTML tipo:

   `<figure class="wp-block-image size-large"><img src="URL" alt="NOMBRE"/></figure>`

7. Une todos los bloques en una sola celda (fila 2 de cada columna).
8. Guarda el nuevo archivo en el Escritorio.

---

### Resultado final

Se genera un nuevo archivo Excel en el Escritorio con:

- Fila 1 → nombres de carpeta.
- Fila 2 → todo el HTML concatenado listo para pegar en WordPress.


### 6.Multiples-pestanas-1-archivo

### Diferencias detectadas en esta versión

### 1. Nuevo archivo de salida
- Antes: el archivo de salida conservaba el mismo nombre del original.
- Ahora: genera un archivo nuevo llamado:

  estructura.xlsx

- Siempre se guarda en el Escritorio.

---

### 2. Procesamiento de múltiples hojas
- Antes: solo procesaba `Sheet1`.
- Ahora: procesa todas las hojas del archivo automáticamente.

---

### 3. Exclusión de hojas específicas
- Se introduce:

  IGNORE_SHEETS = {"basura"}

- Cualquier hoja llamada "basura" será ignorada.

---

### 4. Creación dinámica de hojas en el archivo destino
- Elimina la hoja por defecto del nuevo Excel.
- Crea una nueva hoja por cada pestaña procesada.
- Mantiene el mismo nombre de cada hoja original.

---

### 5. Mayor escalabilidad
- Ahora funciona como herramienta multi-hoja.
- Permite estructurar proyectos completos en un solo archivo.
- Ideal para procesamiento masivo de batches.

---

### Resumen general

Esta versión evoluciona el script de una herramienta de una sola hoja a un sistema multi-hoja automatizado, generando un archivo estructurado completo y limpio.

---

### 6.construccion-figures - todos-los-archivos

### Diferencias detectadas en esta versión

### 1. Procesamiento por carpeta completa
- Antes: trabajaba con un único archivo definido manualmente.
- Ahora: procesa automáticamente todos los archivos `.xlsx` dentro de:

  SOURCE_FOLDER

---

### 2. Soporte batch multi-archivo
- Usa:

  SOURCE_FOLDER.glob("*.xlsx")

- Permite generar múltiples archivos de salida en una sola ejecución.

---

### 3. Hoja fija obligatoria
- Solo procesa archivos que contengan `Sheet1`.
- Si no existe, el archivo se omite automáticamente.

---

### 4. Archivo de salida por cada Excel
- Genera un nuevo archivo por cada archivo procesado.
- Mantiene el mismo nombre original.
- Guarda los resultados en:

  DEST_FOLDER (Escritorio).

---

### 5. Simplificación respecto a versión multi-hoja
- Ya no procesa todas las pestañas.
- Vuelve a un modelo de hoja única (`Sheet1`).
- No tiene sistema de exclusión (`IGNORE_SHEETS`).

---

### Resumen general

Esta versión convierte el script en una herramienta batch multi-archivo (pero de hoja única), ideal para procesar múltiples proyectos automáticamente en una sola ejecución.


## FUERA DE CARPETAS - Crop

### 📌 Análisis del Script — Recorte Automático con Control de Resolución

---

### 1. Tipo de herramienta

- Procesador batch de imágenes.
- Recorte proporcional automático (crop simétrico).
- Preserva estructura de carpetas (modo espejo).
- Incluye validaciones de seguridad por resolución.

---

### 2. Configuración Principal

- `CARPETA_ORIGEN`  
  Carpeta raíz donde se encuentran las imágenes originales.

- `CARPETA_DESTINO`  
  Carpeta donde se guardarán las imágenes recortadas.

- `PORCENTAJE_CORTE = 0.10`  
  Recorta 10% por cada lado (izquierda, derecha, arriba y abajo).

- `ANCHO_MINIMO = 600 px`  
- `ALTO_MINIMO = 600 px`  
  Evita procesar imágenes demasiado pequeñas.

- `EXTENSIONES`  
  Solo procesa `.jpg`, `.jpeg`, `.png`.

---

### 3. Lógica de Procesamiento

#### A) Validación inicial
- Abre la imagen con Pillow.
- Obtiene ancho y alto.
- Si la imagen es menor a la resolución mínima → se omite.

---

#### B) Cálculo del recorte
- Calcula:
  - `dx = ancho * 10%`
  - `dy = alto * 10%`
- Recorte simétrico desde los cuatro bordes.

---

#### C) Validación de seguridad extra
Antes de recortar verifica que:

- El tamaño final no quede por debajo de 600x600.
- Si el recorte compromete la resolución mínima → se omite.

Esto evita:
- Imágenes demasiado pequeñas.
- Recortes destructivos.

---

#### D) Crop real

Se usa: crop_box = (dx, dy, ancho - dx, alto - dy)


Resultado:
- Recorte centrado.
- Eliminación de márgenes laterales.
- Mantiene proporción original.

---

### 4. Procesamiento Recursivo

La función `recorrer_carpeta()`:

- Usa `os.walk()` para recorrer subcarpetas.
- Replica la estructura original en la carpeta destino.
- Genera una estructura espejo automática.

Ejemplo:

origen/
└── carpeta1/
└── imagen.jpg

destino/
└── carpeta1/
└── imagen.jpg


---

### 5. Manejo de Errores

- Cada imagen se procesa dentro de `try/except`.
- Si falla una imagen:
  - Se imprime el error.
  - El script continúa con las demás.
- No detiene el procesamiento batch.

---

### 6. Tipo de Crop Aplicado

✔ Crop proporcional  
✔ Simétrico  
✔ No redimensiona  
✔ No reescala  
✔ No deforma  
✔ No altera calidad original  

Es un recorte físico real, no un resize.

---

### 7. Arquitectura del Script

Modelo modular:

- `procesar_imagen()` → lógica individual.
- `recorrer_carpeta()` → orquestador batch.
- `if __name__ == "__main__"` → ejecución controlada.

Permite evolucionar fácilmente hacia:

- GUI
- Versión .exe
- Integración en pipeline mayor
- Agregado de watermark
- Soporte para porcentajes dinámicos

---

### 8. Resultado Final

Convierte una carpeta completa de imágenes en una versión recortada:

- Limpia márgenes automáticamente.
- Mantiene resolución mínima segura.
- Preserva estructura original.
- Funciona como herramienta de saneamiento visual masivo.

---

### 🎯 Clasificación del Script

Es una herramienta de:

- Crop automático no destructivo en estructura
- Procesamiento batch recursivo
- Control de calidad por resolución
- Optimización previa a publicación o subida masiva

---

### 📌 Análisis del Script — Limpieza Selectiva de Carpetas (Filtro por `source.html`) - eliminar-vacios

---

### 1. Tipo de herramienta

- Script de saneamiento estructural.
- Limpieza automática por condición exacta.
- Clasificación de carpetas vacías funcionalmente.
- Sistema de cuarentena mediante carpeta `basura`.

---

### 2. Configuración Principal

- `CARPETA_MADRE`  
  Carpeta raíz que contiene múltiples subcarpetas a evaluar.

- `NOMBRE_BASURA = "basura"`  
  Carpeta destino donde se moverán las carpetas descartadas.

- `ARCHIVO_OBJETIVO = "source.html"`  
  Archivo que define la condición exacta de descarte.

---

### 3. Lógica del Sistema

El script evalúa **cada subcarpeta directa** dentro de `CARPETA_MADRE`.

---

### 4. Condición Exacta de Eliminación

Una carpeta se mueve a `basura` únicamente si:

- Contiene exactamente **1 archivo**
- Y ese archivo es `source.html`

Condición literal aplicada:

len(archivos) == 1
AND
archivos[0].lower() == "source.html"


Esto significa:

- No debe haber imágenes
- No debe haber carpetas internas
- No debe haber archivos adicionales

Es un filtro extremadamente preciso.

---

### 5. Flujo de Procesamiento

#### A) Preparación
- Crea la carpeta `basura` si no existe.
- Evita errores si ya estaba creada.

---

#### B) Iteración
- Usa `os.listdir()` sobre la carpeta madre.
- Evalúa solo elementos que sean directorios.
- Ignora explícitamente la carpeta `basura`.

---

#### C) Decisión

Si cumple la condición:
- Se mueve completamente la carpeta usando `shutil.move()`.

Si no cumple:
- Se conserva intacta.

---

### 6. Qué Está Detectando Realmente

Este script identifica carpetas que:

- Solo contienen el archivo base `source.html`.
- No tienen imágenes descargadas.
- No fueron procesadas correctamente.
- Están incompletas o vacías operativamente.

En términos prácticos:
Detecta “carpetas fallidas”.

---

### 7. Seguridad del Sistema

✔ No elimina definitivamente  
✔ No borra archivos  
✔ Solo mueve a carpeta de cuarentena  
✔ No procesa subcarpetas profundas  
✔ No afecta estructura interna válida  

Es reversible.

---

### 8. Arquitectura del Script

Modelo minimalista:

- `limpiar_carpetas()` → lógica central
- `if __name__ == "__main__"` → ejecución controlada

No depende de librerías externas.
No requiere entorno especial.
Opera con librerías estándar (`os`, `shutil`).

---

### 9. Patrón de Uso Dentro del Pipeline

Este script funciona como etapa de:

- Validación post-descarga
- Filtrado previo a subida
- Limpieza antes de procesamiento masivo
- Control de calidad estructural

Encaja perfectamente entre:

Descarga → Limpieza estructural → Subida / Procesamiento

---

### 🎯 Clasificación del Script

Es una herramienta de:

- Clasificación automática por condición exacta
- Limpieza estructural no destructiva
- Sistema de cuarentena reversible
- Saneamiento de proyectos incompletos

---

### Resultado Final

Después de ejecutarlo:

- Las carpetas incompletas quedan centralizadas en `/basura`.
- Las carpetas válidas permanecen intactas.
- La estructura principal queda depurada y lista para continuar el pipeline.


---

### 📌 Análisis del Script — Mover Carpetas según `faltantes.txt` (Versión con Interfaz GUI) - faltantes

---

### 1. Tipo de herramienta

- Clasificador automático de carpetas.
- Basado en lista blanca (`faltantes.txt`).
- Interfaz gráfica (Tkinter).
- Sistema de movimiento seguro (no elimina, solo reubica).

---

### 2. Objetivo del Script

Dado un archivo `faltantes.txt` con nombres válidos:

- Mantiene las carpetas que coincidan con la lista.
- Mueve las que NO estén en la lista a una carpeta llamada `Faltantes`.

Es un sistema de filtrado inverso:
La lista define qué debe quedarse.

---

### 3. Flujo General del Sistema

#### Paso 1 — Selección del archivo
El usuario selecciona `faltantes.txt` mediante un explorador.

#### Paso 2 — Lectura de datos
Se construye un `set()` con:

nombres_validos = set(...)


Ventaja:
- Búsqueda extremadamente rápida (O(1)).
- Ideal para grandes volúmenes de carpetas.

---

### 4. Lógica de Clasificación

El script analiza todas las carpetas dentro del directorio donde está el `faltantes.txt`.

Para cada carpeta:

- Si es directorio
- Y no es la carpeta `Faltantes`
- Y su nombre NO está en `nombres_validos`

Entonces:

→ Se mueve a `/Faltantes`

---

### 5. Seguridad Implementada

✔ No elimina nada  
✔ No sobrescribe si ya existe en destino  
✔ Evita mover la carpeta `Faltantes`  
✔ Muestra reporte final detallado  

Si una carpeta ya existía en destino:
- Se agrega a lista de omitidas.
- No se pierde información.

---

### 6. Reporte Final

Al terminar muestra un resumen:

- Carpetas movidas
- Carpetas omitidas (ya existían en destino)

Ejemplo conceptual:

Proceso terminado.

Carpetas movidas:
['A1', 'A2', 'A3']

Carpetas omitidas:
['B1']


---

### 7. Arquitectura Modular

Funciones separadas:

- `procesar()` → lógica principal
- `seleccionar_archivo()` → explorador
- `ejecutar()` → puente entre GUI y lógica

Separación clara entre:
Interfaz y procesamiento.

---

### 8. Tipo de Clasificación que Realiza

Este script implementa:

- Validación por lista blanca.
- Limpieza estructural inteligente.
- Control de carpetas faltantes en proyectos grandes.

Es especialmente útil cuando:

- Tienes cientos de carpetas.
- Solo algunas deben permanecer.
- El resto son sobrantes, errores o duplicados.

---

### 9. Posición Dentro del Pipeline

Encaja perfectamente después de:

- Validación de Excel.
- Comparación contra base de datos.
- Detección de proyectos faltantes.

Funciona como:

Control estructural post-auditoría.

---

### 🎯 Clasificación del Script

Es una herramienta de:

- Filtro estructural por lista externa
- Clasificación masiva automatizada
- Limpieza no destructiva
- Interfaz amigable para usuario no técnico

---

### Resultado Final

Tras ejecutarlo:

- Solo permanecen en la raíz las carpetas listadas en `faltantes.txt`.
- Todas las demás quedan centralizadas en `/Faltantes`.
- El sistema queda ordenado y coherente con la auditoría realizada.

----

### 📌 Análisis del Script — Optimización y Estandarización de Imágenes (Resize + Compresión Web) - size

---

### 1. Tipo de herramienta

- Optimizador de imágenes para web.
- Redimensionamiento condicional.
- Conversión forzada a JPEG.
- Compresión avanzada con parámetros optimizados.
- Procesamiento batch en carpeta única.

---

### 2. Objetivo del Script

Transformar imágenes originales en versiones:

- Más ligeras
- Estandarizadas en ancho
- Compatibles con web
- Optimizadas para carga rápida

Todo se guarda en una subcarpeta llamada:

New/


---

### 3. Configuración Principal

- `carpeta_entrada`  
  Carpeta base con imágenes originales.

- `carpeta_salida = New`  
  Subcarpeta automática dentro de la misma carpeta.

- `max_ancho = 1200 px`  
  Ancho máximo permitido.

- `calidad = 75`  
  Punto de equilibrio entre peso y calidad visual.

---

### 4. Lógica de Procesamiento

#### A) Filtro de extensiones

Procesa únicamente:

- `.jpg`
- `.jpeg`
- `.png`

---

#### B) Conversión a RGB

img = img.convert("RGB")


Esto garantiza:

- Eliminación de canal alpha.
- Compatibilidad total con formato JPEG.
- Evita errores al guardar PNG con transparencia.

---

#### C) Redimensionamiento Condicional

Solo si:

img.width > max_ancho


Entonces:

- Calcula ratio proporcional.
- Mantiene proporción original.
- Usa `Image.LANCZOS` (alta calidad).

No amplía imágenes pequeñas.
No deforma.
No recorta.

---

### 5. Compresión Web Optimizada

Al guardar usa:

quality=75
optimize=True
progressive=True
subsampling=2


Significado:

- `quality=75` → compresión eficiente sin degradación visible fuerte.
- `optimize=True` → optimiza tablas Huffman.
- `progressive=True` → carga progresiva en navegadores.
- `subsampling=2` → compresión cromática eficiente.

Esto lo convierte en un JPEG web-ready profesional.

---

### 6. Conversión Universal a JPG

Independientemente del formato original:

- Todos los archivos terminan como `.jpg`.
- Uniformiza el output.
- Ideal para WordPress y CDNs.

---

### 7. Reporte de Ahorro

Después de procesar cada imagen:

Muestra:

imagen.png | 2450 KB → 480 KB


Permite visualizar:

- Reducción real de peso.
- Impacto inmediato en rendimiento.

---

### 8. Arquitectura del Script

- No es recursivo.
- Procesa solo la carpeta raíz.
- No replica estructura.
- Genera carpeta destino automática.

Modelo simple, directo y eficiente.

---

### 9. Posición Dentro del Pipeline

Este script funciona como:

- Etapa de optimización final antes de subir.
- Paso previo a CDN.
- Fase de preparación para publicación.
- Reductor de peso para Core Web Vitals.

Encaja después de:

Recorte → Limpieza → Optimización → Subida

---

### 🎯 Clasificación del Script

Es una herramienta de:

- Normalización de resolución
- Compresión inteligente
- Estandarización de formato
- Optimización web profesional
- Reducción de peso masiva

---

### Resultado Final

Tras ejecutarlo:

- Todas las imágenes quedan en `/New`.
- Ninguna supera 1200px de ancho.
- Todas están en formato JPEG optimizado.
- El peso se reduce significativamente.
- Listas para publicación rápida y eficiente.

----



## 📁 Estructura Actual del Proyecto `uploader/`

uploader/
│
├─ uploader.py # Orquestador principal en Python
├─ requirements.txt # Dependencias exactas (pip freeze)
├─ Dockerfile # Entorno reproducible
├─ README.md
│
├─ 1.links-obtener/ # Scraping con paginación → genera links.txt
├─ 2.descargar/ # Descarga masiva desde source.html (modo simple y recursivo)
├─ 3.limpiar-img/ # Limpieza y aplanado de carpetas (GUI / .exe)
├─ 4.subir-img-orquestador/ # Automatización subida a ImgBox (Selenium)
├─ 5.extraer-images2/ # Extracción URLs images2 desde Excel (single, multi-hoja y batch)
├─ 6.construccion-figures/ # Generación HTML <figure> (single, multi-hoja y multi-archivo)
│
├─ links.txt # Input dinámico (rutas o URLs base)
└─ escritorio/ # Outputs temporales / archivos generados


---

## 🔄 Flujo General del Sistema

1. **1.links-obtener**  
   → Scraping de posts  
   → Genera `links.txt`

2. **2.descargar**  
   → Lee `source.html` en cada carpeta  
   → Descarga imágenes (con reintentos y modo recursivo)

3. **3.limpiar-img**  
   → Aplana subcarpetas  
   → Elimina basura (por tamaño o patrón)  
   → Centraliza en `/basura`

4. **4.subir-img-orquestador**  
   → Automatiza subida a ImgBox  
   → Obtiene HTML resultante

5. **5.extraer-images2**  
   → Extrae URLs finales de `images2.imgbox.com`  
   → Soporta:
   - Un solo archivo
   - Multi-hoja
   - Batch por carpeta

6. **6.construccion-figures**  
   → Convierte URLs en bloques `<figure>`  
   → Soporta:
   - Hoja única
   - Multi-hoja
   - Multi-archivo batch

---

## 🧠 Arquitectura Evolutiva

El sistema evolucionó desde scripts individuales a:

- Procesamiento recursivo
- Sistemas batch multi-archivo
- Soporte multi-hoja
- Generación estructurada lista para WordPress
- Separación clara por fases del pipeline

---

## 🎯 Resultado Final del Pipeline

Desde scraping inicial hasta HTML final listo para pegar en WordPress, todo el proceso puede automatizarse de forma modular y escalable.

Este proyecto ya funciona como un **pipeline completo de ingestión → limpieza → subida → estructuración HTML**.
