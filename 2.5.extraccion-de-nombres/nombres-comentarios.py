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
    Extrae nombres de los comentarios HTML.
    Busca patrones como:
    - "su nombres es Juan"
    - "data: Carlos"
    - "ella es María"
    - O solo el nombre
    """
    
    patterns = [
        r"su\s+nombres?\s+(?:es\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*,|$)",
        r"data\s*:?\s*([A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*,|$)",
        r"ella\s+es\s+([A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*,|$)",
        r"^([A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)$"  # Solo nombre al inicio
    ]
    
    for comment in comments:
        comment_clean = comment.replace("\n", " ").strip()
        
        # Intenta cada patrón
        for pattern in patterns[:-1]:  # Todos excepto el último
            match = re.search(pattern, comment_clean, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                if nombre and len(nombre) > 1:  # Evita resultados muy cortos
                    return nombre
        
        # Patrón simple: si el comentario es muy corto, podría ser solo un nombre
        if len(comment_clean) < 50 and len(comment_clean) > 1:
            # Verifica que contenga principalmente letras
            if re.match(r"^[A-Za-záéíóúñÁÉÍÓÚÑ\s]+$", comment_clean):
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
    
    # Prioridad: 1) Argumento línea de comandos, 2) Variable RUTA_CARPETA_MADRE, 3) Input del usuario
    if len(sys.argv) > 1:
        carpeta_madre = sys.argv[1]
        if len(sys.argv) > 2:
            archivo_salida = sys.argv[2]
    elif RUTA_CARPETA_MADRE and RUTA_CARPETA_MADRE != r"C:\Ruta\A\Tus\Carpetas":
        carpeta_madre = RUTA_CARPETA_MADRE
        print(f"Usando ruta configurada: {carpeta_madre}")
    else:
        carpeta_madre = input("Ingresa la ruta a la carpeta madre: ").strip()
        archivo_salida = input("Nombre del archivo de salida (predeterminado: resultado.txt): ").strip() or "resultado.txt"
    
    procesar_carpetas(carpeta_madre, archivo_salida)
