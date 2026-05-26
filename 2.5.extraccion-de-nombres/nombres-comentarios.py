#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path
from html.parser import HTMLParser


class HTMLExtractor(HTMLParser):
    """Extrae título, h1 y contenido de la sección #comments"""

    def __init__(self):
        super().__init__()
        self.title = None
        self.h1 = None
        self.comments_content = ""
        self.in_title = False
        self.in_h1 = False
        self.in_comments_section = False
        self.current_h1 = ""
        self.depth_in_comments = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True

        # Buscar sección #comments
        if attrs_dict.get("id") == "comments":
            self.in_comments_section = True
            self.depth_in_comments = 1
        elif self.in_comments_section:
            self.depth_in_comments += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

        elif tag == "h1":
            self.in_h1 = False

            if self.current_h1:
                self.h1 = self.current_h1.strip()
                self.current_h1 = ""

        # Controlar cuándo termina la sección comments
        if self.in_comments_section:
            self.depth_in_comments -= 1

            if self.depth_in_comments == 0:
                self.in_comments_section = False

    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title = data.strip()

        elif self.in_h1:
            self.current_h1 += data

        elif self.in_comments_section:
            self.comments_content += " " + data.strip()


def extract_nombre_from_comments(comments):
    """
    Extrae SOLO nombres reales de los comentarios.
    """

    palabras_ignorar = {
        'sitio', 'web', 'jquery', 'javascript', 'html', 'css',
        'php', 'python', 'función', 'script', 'archivo',
        'página', 'blog', 'post', 'artículo', 'contenido',
        'código', 'tema', 'plugin', 'framework', 'librería',
        'api', 'base', 'datos', 'servidor', 'cliente',
        'desarrollo', 'diseño', 'responsive', 'mobile',
        'desktop', 'version', 'actualización', 'bug',
        'fix', 'error', 'solución', 'tutorial', 'guía',
        'ejemplo', 'demo', 'template', 'herramienta',
        'tool', 'widget', 'componente', 'url', 'link',
        'href', 'src', 'class', 'id', 'div', 'span',
        'captcha', 'meta'
    }

    patrones = [
        (
            r"se\s+llama\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "se llama"
        ),
        (
            r"su\s+nombre\s+es\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "su nombre es"
        ),
        (
            r"ella\s+es\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "ella es"
        ),
        (
            r"este\s+es\s+su\s+instagram\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "instagram"
        ),
        (
            r"está\s+en\s+instagram\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "instagram"
        ),
        (
            r"instagram\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "instagram"
        ),
        (
            r"este\s+es\s+su\s+facebook\s+([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "facebook"
        ),
        (
            r"cafecito\s+(?:es\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "cafecito"
        ),
        (
            r"su\s+nombres?\s+(?:es\s+)?([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "nombre"
        ),
        (
            r"data\s*:?\s*([A-Za-záéíóúñÁÉÍÓÚÑ]+(?:\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+)?)",
            "data"
        ),
    ]

    for comment in comments:

        if not comment or not comment.strip():
            continue

        comment_clean = comment.replace("\n", " ").strip()

        sentences = re.split(r'[.!?;,]', comment_clean)

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) < 5 or len(sentence) > 200:
                continue

            # Ignorar texto técnico
            if any(
                palabra in sentence.lower()
                for palabra in palabras_ignorar
            ):
                continue

            # Buscar patrones
            for patron, nombre_patron in patrones:

                match = re.search(
                    patron,
                    sentence,
                    re.IGNORECASE
                )

                if match:

                    nombre = match.group(1).strip()

                    if 3 <= len(nombre) <= 40:

                        if nombre.count(' ') <= 2:

                            if re.match(
                                r"^[A-Za-záéíóúñÁÉÍÓÚÑ\s]+$",
                                nombre
                            ):
                                return nombre

        # Fallback
        if 3 <= len(comment_clean) <= 35:

            palabras = comment_clean.split()

            if len(palabras) <= 2:

                if all(
                    re.match(r"^[A-Za-záéíóúñÁÉÍÓÚÑ]+$", p)
                    for p in palabras
                ):

                    if not any(
                        p.lower() in palabras_ignorar
                        for p in palabras
                    ):
                        return comment_clean

    return None


def procesar_carpetas(
    ruta_madre,
    ruta_output="resultado.txt"
):
    """
    Procesa todas las carpetas y extrae la información.
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

    # Recorre subcarpetas
    for subcarpeta in sorted(ruta_madre.iterdir()):

        if not subcarpeta.is_dir():
            continue

        archivos_html = list(subcarpeta.glob("*.html"))

        if not archivos_html:
            continue

        archivo_html = archivos_html[0]

        contador["procesados"] += 1

        try:
            with open(
                archivo_html,
                'r',
                encoding='utf-8'
            ) as f:

                contenido_html = f.read()

            parser = HTMLExtractor()
            parser.feed(contenido_html)

            titulo = (
                parser.title
                or parser.h1
                or "Sin título"
            )

            comments_list = (
                [parser.comments_content]
                if parser.comments_content
                else []
            )

            nombre = extract_nombre_from_comments(
                comments_list
            )

            if nombre:

                resultado = f"{titulo} - {nombre}"

                resultados.append(resultado)

                contador["exitosos"] += 1

                print(
                    f"✓ {subcarpeta.name}: {resultado}"
                )

            else:
                print(
                    f"⚠ {subcarpeta.name}: "
                    f"No se encontró nombre"
                )

        except Exception as e:

            contador["errores"] += 1

            print(
                f"✗ {subcarpeta.name}: Error - {str(e)}"
            )

    # Guardar salida
    if resultados:

        with open(
            ruta_output,
            'w',
            encoding='utf-8'
        ) as f:

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
    # CONFIGURACIÓN
    # ============================================================

    RUTA_CARPETA_MADRE = (
        r"C:\Users\dell\Downloads\descarga\links"
    )

    ARCHIVO_SALIDA = "resultado.txt"

    # ============================================================

    carpeta_madre = RUTA_CARPETA_MADRE
    archivo_salida = ARCHIVO_SALIDA

    # Prioridad:
    # 1) Argumentos CLI
    # 2) Variables configuradas

    if len(sys.argv) > 1:

        carpeta_madre = sys.argv[1]

        if len(sys.argv) > 2:
            archivo_salida = sys.argv[2]

        print(
            f"Usando ruta desde línea de comandos: "
            f"{carpeta_madre}"
        )

    else:
        print(
            f"Usando ruta configurada: "
            f"{carpeta_madre}"
        )

    procesar_carpetas(
        carpeta_madre,
        archivo_salida
    )