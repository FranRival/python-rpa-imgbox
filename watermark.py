import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from PIL import Image, ImageEnhance

# ============================================================
#   CONFIGURACION — modifica solo esta seccion
# ============================================================

CARPETA_FUENTE   = r"C:\Users\dell\Desktop\listo\links127"
CARPETA_SALIDA   = r"C:\Users\dell\Downloads\procesadas"
MARCA_DE_AGUA    = r"C:\Users\dell\Downloads\logo-con-fondo.png"

POSICION  = "bottom-right"   # bottom-right | bottom-left | top-right | top-left | center
ESCALA    = 0.40              # tamano del banner: 0.10 = 10% del ancho de cada imagen
OPACIDAD  = 1.0              # transparencia: 0.0 invisible — 1.0 solido
MARGEN    = 0                # pixeles de margen desde el borde
HILOS     = 4                 # procesos paralelos (4 a 8 recomendado)

# ============================================================

SUPPORTED = {'.jpg', '.jpeg', '.png'}
print_lock = Lock()
counter = {'ok': 0, 'fail': 0}
counter_lock = Lock()

def log(msg):
    with print_lock:
        print(msg, flush=True)

def load_watermark(path):
    return Image.open(path).convert('RGBA')

def scale_watermark(wm, target_w, target_h, scale):
    desired_w = max(1, int(target_w * scale))
    ratio = desired_w / wm.width
    desired_h = max(1, int(wm.height * ratio))
    max_h = int(target_h * 0.9)
    if desired_h > max_h:
        desired_h = max_h
        ratio = desired_h / wm.height
        desired_w = max(1, int(wm.width * ratio))
    return wm.resize((desired_w, desired_h), Image.LANCZOS)

def apply_opacity(wm, opacity):
    r, g, b, a = wm.split()
    a = ImageEnhance.Brightness(a).enhance(opacity)
    return Image.merge('RGBA', (r, g, b, a))

def calc_position(img_w, img_h, wm_w, wm_h, position, margin):
    positions = {
        'bottom-right': (img_w - wm_w - margin, img_h - wm_h - margin),
        'bottom-left':  (margin,                 img_h - wm_h - margin),
        'top-right':    (img_w - wm_w - margin,  margin),
        'top-left':     (margin,                  margin),
        'center':       ((img_w - wm_w) // 2,     (img_h - wm_h) // 2),
    }
    return positions.get(position, positions['bottom-right'])

def process_image(src, dst, wm_original, total):
    try:
        img = Image.open(src)
        fmt = img.format
        img_rgba = img.convert('RGBA')
        wm = scale_watermark(wm_original, img.width, img.height, ESCALA)
        wm = apply_opacity(wm, OPACIDAD)
        x, y = calc_position(img.width, img.height, wm.width, wm.height, POSICION, MARGEN)
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay.paste(wm, (x, y), wm)
        result = Image.alpha_composite(img_rgba, overlay)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if fmt == 'JPEG' or src.suffix.lower() in {'.jpg', '.jpeg'}:
            result = result.convert('RGB')
            result.save(dst, format='JPEG', quality=95, subsampling=0)
        else:
            result.save(dst, format='PNG', optimize=True)
        with counter_lock:
            counter['ok'] += 1
            done = counter['ok'] + counter['fail']
        log(f"  [{int(done/total*100):3d}%] OK    {src.name}  ({img.width}x{img.height}px)")
        return True
    except Exception as exc:
        with counter_lock:
            counter['fail'] += 1
            done = counter['ok'] + counter['fail']
        log(f"  [{int(done/total*100):3d}%] ERROR {src.name}: {exc}")
        return False

def find_images(source_dir, wm_path):
    wm_resolved = wm_path.resolve()
    images = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if Path(f).suffix.lower() in SUPPORTED:
                full = (Path(root) / f).resolve()
                if full != wm_resolved:
                    images.append(full)
    return images

def main():
    source_dir = Path(CARPETA_FUENTE).resolve()
    output_dir = Path(CARPETA_SALIDA).resolve()
    wm_path    = Path(MARCA_DE_AGUA).resolve()

    if not source_dir.is_dir():
        sys.exit(f"\n  ERROR: Carpeta fuente no existe:\n  {source_dir}\n")
    if not wm_path.is_file():
        sys.exit(f"\n  ERROR: Marca de agua no existe:\n  {wm_path}\n")
    if source_dir == output_dir:
        sys.exit(f"\n  ERROR: La carpeta de salida debe ser distinta a la fuente.\n")

    print(f"\n{'='*60}")
    print(f"  Fuente     : {source_dir}")
    print(f"  Salida     : {output_dir}")
    print(f"  Watermark  : {wm_path}")
    print(f"  Posicion   : {POSICION}")
    print(f"  Escala     : {int(ESCALA*100)}% del ancho")
    print(f"  Opacidad   : {int(OPACIDAD*100)}%")
    print(f"  Margen     : {MARGEN}px")
    print(f"  Hilos      : {HILOS}")
    print(f"{'='*60}\n")

    wm_original = load_watermark(wm_path)
    images = find_images(source_dir, wm_path)
    total = len(images)

    if total == 0:
        sys.exit("  No se encontraron imagenes JPG/PNG.\n")

    print(f"  Imagenes encontradas: {total}\n")

    tasks = [(src, output_dir / src.relative_to(source_dir)) for src in images]

    with ThreadPoolExecutor(max_workers=HILOS) as executor:
        futures = [executor.submit(process_image, src, dst, wm_original, total) for src, dst in tasks]
        for f in as_completed(futures):
            pass

    print(f"\n{'='*60}")
    print(f"  Completadas : {counter['ok']}")
    print(f"  Errores     : {counter['fail']}")
    print(f"  Guardadas en: {output_dir}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()