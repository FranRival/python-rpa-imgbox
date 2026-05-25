#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path
from html.parser import HTMLParser

class HTMLCommentExtractor(HTMLParser):
    """Extrae comentarios HTML y el título/h1"""
    
    def __init__(self):
        super().__init__()
        self.comments = []
        self.title = None
        self.h1 = None
        self.in_title = False
        self.in_h1 = False
        self.current_h1 = ""
    
    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
    
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False
            if self.current_h1:
                self.h1 = self.current_h1.strip()
                self.current_h1 = ""
    
    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title = data.strip()
        elif self.in_h1:
            self.current_h1 += data
    
    def handle_comment(self, data):
        self.comments.append(data.strip())


def extract_nombre_from_comments(comments):
    """
    Extrae SOLO nombres reales de los comentarios HTML.
    Evita completamente palabras técnicas, URLs, etc.
    
    Solo extrae si:
    - Está en un patrón explícito: "su nombres es Juan", "data: Carlos"
    - Es un nombre muy simple (2-3 palabras, solo letras)
    """
    
    # Palabras a ignorar completamente (técnicas, basura, etc)
    palabras_ignorar = {
        'sitio', 'web', 'jquery', 'javascript', 'html', 'css', 'php', 'python',
        'función', 'script', 'archivo', 'página', 'blog', 'post', 'artículo',
        'contenido', 'código', 'tema', 'plugin', 'framework', 'librería',
        'api', 'base', 'datos', 'servidor', 'cliente', 'desarrollo',
        'diseño', 'responsive', 'mobile', 'desktop', 'version', 'actualización',
        'bug', 'fix', 'error', 'solución', 'tutorial', 'guía', 'ejemplo',
        'demo', 'template', 'herramienta', 'tool', 'widget', 'componente'
    }
    
    for comment in comments:
        comment_clean = comment.replace("\n", " ").strip()
        
        # Ignorar comentarios muy largos o que contengan caracteres raros
        if len(comment_clean) > 60 or '-' in comment_clean or ',' in comment_clean:
            continue
        
        # Ignorar si contiene palabras técnicas
        if any(palabra in comment_clean.lower() for palabra in palabras_ignorar):
            continue
        
        # Patrón 1: "su nombres es Juan" o "su nombre es Juan"
        match = re.search(r"su\s+nombres?\s+(?:es\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 2: "data: Juan" o "data Juan"
        match = re.search(r"data\s*:?\s*([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 3: "ella es María" o "nombre María"
        match = re.search(r"(?:ella\s+es|nombre)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 4: "se llama Juan" o "se llama Juan García"
        match = re.search(r"se\s+llama\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 5: "está en Instagram Juan" o "este es su Instagram Juan"
        match = re.search(r"(?:está\s+en\s+instagram|este\s+es\s+su\s+instagram|instagram)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 6: "este es su Facebook Juan" o "facebook Juan"
        match = re.search(r"(?:este\s+es\s+su\s+facebook|facebook)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 7: "cafecito Juan" o "mi cafecito es Juan"
        match = re.search(r"(?:mi\s+)?cafecito(?:\s+es\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)", comment_clean, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            if 3 <= len(nombre) <= 40 and nombre.count(' ') <= 2:
                return nombre
        
        # Patrón 4: Solo si es MUY limpio - solo 1 o 2 palabras, solo letras y espacios
        if 3 <= len(comment_clean) <= 35:
            palabras = comment_clean.split()
            # Solo 1 o 2 palabras, todas deben ser válidas (capitalizadas o todo minúsculas)
            if len(palabras) <= 2:
                if all(re.match(r"^[A-Za-záéíóúñÁÉÍÓÚÑ]+$", p) for p in palabras):
                    # Verifica que no sea una palabra reservada
                    if not any(p.lower() in palabras_ignorar for p in palabras):
                        return comment_clean
    
    return None


def procesar_carpetas(ruta_madre, ruta_output="resultado.txt"):
    """
    Procesa todas las carpetas y extrae la información.
    
    Args:
        ruta_madre: Ruta a la carpeta padre
        ruta_output: Ruta del archivo de salida
    """
    
    resultados = []
    contador = {
        "procesados": 0,
        "exitosos": 0,
        "errores": 0
    }
    
    ruta_madre = Path(ruta_madre)
    
    if not ruta_madre.exists():
        print(f"Error: La ruta {ruta_madre} no existe")
        return
    
    print(f"Buscando carpetas en: {ruta_madre}")
    print("-" * 80)
    
    # Recorre todas las subcarpetas
    for subcarpeta in sorted(ruta_madre.iterdir()):
        if not subcarpeta.is_dir():
            continue
        
        # Busca archivos HTML en la subcarpeta
        archivos_html = list(subcarpeta.glob("*.html"))
        
        if not archivos_html:
            continue
        
        # Toma el primer HTML encontrado
        archivo_html = archivos_html[0]
        contador["procesados"] += 1
        
        try:
            # Lee el archivo HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                contenido_html = f.read()
            
            # Extrae información
            parser = HTMLCommentExtractor()
            parser.feed(contenido_html)
            
            # Obtén el título (prefiere title, luego h1)
            titulo = parser.title or parser.h1 or "Sin título"
            
            # Extrae el nombre de los comentarios
            nombre = extract_nombre_from_comments(parser.comments)
            
            if nombre:
                resultado = f"{titulo} - {nombre}"
                resultados.append(resultado)
                contador["exitosos"] += 1
                print(f"✓ {subcarpeta.name}: {resultado}")
            else:
                print(f"⚠ {subcarpeta.name}: No se encontró nombre en comentarios")
        
        except Exception as e:
            contador["errores"] += 1
            print(f"✗ {subcarpeta.name}: Error - {str(e)}")
    
    # Escribe el archivo de salida
    if resultados:
        with open(ruta_output, 'w', encoding='utf-8') as f:
            f.write("\n".join(resultados))
        
        print("-" * 80)
        print(f"\n✓ Archivo creado: {ruta_output}")
        print(f"Procesados: {contador['procesados']}")
        print(f"Exitosos: {contador['exitosos']}")
        print(f"Errores: {contador['errores']}")
        print(f"Total de líneas: {len(resultados)}")
    else:
        print("\n⚠ No se encontraron resultados")


if __name__ == "__main__":
    import sys
    
    # ============================================================
    # CONFIGURA AQUÍ LA RUTA DE TUS CARPETAS
    # ============================================================
    RUTA_CARPETA_MADRE = r"C:\Users\dell\Downloads\descarga\links"
    ARCHIVO_SALIDA = "resultado.txt"
    # ============================================================
    
    # Inicializar variables con valores predeterminados
    carpeta_madre = RUTA_CARPETA_MADRE
    archivo_salida = ARCHIVO_SALIDA
    
    # Prioridad: 1) Argumento línea de comandos, 2) Variables configuradas
    if len(sys.argv) > 1:
        carpeta_madre = sys.argv[1]
        if len(sys.argv) > 2:
            archivo_salida = sys.argv[2]
        print(f"Usando ruta desde línea de comandos: {carpeta_madre}")
    else:
        print(f"Usando ruta configurada: {carpeta_madre}")
    
    procesar_carpetas(carpeta_madre, archivo_salida)
