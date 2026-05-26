#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path
from html.parser import HTMLParser

class HTMLExtractor(HTMLParser):
    """Extrae URL, título y cuenta comentarios"""
    
    def __init__(self):
        super().__init__()
        self.url = None
        self.title = None
        self.h1 = None
        self.comment_count = 0
        self.in_title = False
        self.in_h1 = False
        self.current_h1 = ""
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
        
        # Extraer URL del meta tag og:url
        if tag == "meta":
            if attrs_dict.get("property") == "og:url":
                self.url = attrs_dict.get("content")
    
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


def contar_comentarios(contenido_html):
    """
    Cuenta los comentarios buscando el contador de comentarios en la página
    """
    
    # Intenta encontrar el contador en el HTML (ej: "<span class="count">6</span>")
    match = re.search(r'<span\s+class="count">(\d+)</span>', contenido_html)
    if match:
        try:
            return int(match.group(1))
        except:
            pass
    
    # Si no encuentra el contador, cuenta los divs con class="comment"
    comment_divs = re.findall(r'<div\s+class="comment', contenido_html)
    return len(comment_divs)


def procesar_carpetas(ruta_madre, ruta_output="resultado.txt"):
    """
    Procesa todas las carpetas y extrae:
    - URL del post
    - Título
    - Cantidad de comentarios
    
    Solo escribe en el archivo si hay comentarios
    """
    
    resultados = []
    contador = {
        "procesados": 0,
        "con_comentarios": 0,
        "sin_comentarios": 0,
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
            parser = HTMLExtractor()
            parser.feed(contenido_html)
            
            # Obtén datos
            url = parser.url or "Sin URL"
            titulo = parser.title or parser.h1 or "Sin título"
            num_comentarios = contar_comentarios(contenido_html)
            
            # IMPORTANTE: Solo escribe si hay comentarios
            if num_comentarios > 0:
                resultado = f"{url} - {titulo} - {num_comentarios}"
                resultados.append(resultado)
                contador["con_comentarios"] += 1
                print(f"✓ {subcarpeta.name}: {num_comentarios} comentarios")
            else:
                contador["sin_comentarios"] += 1
                print(f"⊘ {subcarpeta.name}: Sin comentarios (ignorado)")
        
        except Exception as e:
            contador["errores"] += 1
            print(f"✗ {subcarpeta.name}: Error - {str(e)}")
    
    # Escribe el archivo de salida
    if resultados:
        with open(ruta_output, 'w', encoding='utf-8') as f:
            f.write("\n".join(resultados))
        
        print("-" * 80)
        print(f"\n✓ Archivo creado: {ruta_output}")
        print(f"\nEstadísticas:")
        print(f"  Procesados: {contador['procesados']}")
        print(f"  Con comentarios: {contador['con_comentarios']}")
        print(f"  Sin comentarios: {contador['sin_comentarios']}")
        print(f"  Errores: {contador['errores']}")
        print(f"  Total líneas en resultado: {len(resultados)}")
    else:
        print("-" * 80)
        print(f"\n⚠ No se encontraron posts con comentarios")
        print(f"\nEstadísticas:")
        print(f"  Procesados: {contador['procesados']}")
        print(f"  Con comentarios: {contador['con_comentarios']}")
        print(f"  Sin comentarios: {contador['sin_comentarios']}")
        print(f"  Errores: {contador['errores']}")


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
