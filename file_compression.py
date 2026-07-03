"""
Compresión automática de archivos subidos al crear tickets/subtareas/mensajes.

Estrategia:
- Imágenes (PNG/JPG/JPEG/GIF/WebP): reoptimizar con Pillow.
    * Si el lado más largo > MAX_DIMENSION (1920), redimensionar preservando aspecto.
    * JPEG: guardar con quality=85, optimize=True.
    * PNG: convertir a JPEG si no tiene canal alpha significativo (ahorra ~70%).
      Si tiene alpha real, dejarlo como PNG pero con optimize=True.
    * GIF/WebP animados: no tocar (preservan animación).
- Otros archivos (PDF, DOCX, XLSX, TXT, LOG, ZIP): devolver tal cual.
    (Los formatos Office ya son ZIPs internamente; PDF requiere Ghostscript
    para comprimir bien, complejidad no vale la pena para el ahorro.)

Uso desde una vista Flask:

    from file_compression import compress_upload
    bytes_out, new_filename, new_mime, stats = compress_upload(file_storage)
    with open(path, 'wb') as fh:
        fh.write(bytes_out)
    print(f"Comprimido {stats['ratio']*100:.0f}% ({stats['original_size']} -> {stats['final_size']})")
"""
from __future__ import annotations

import io
import logging
from typing import Tuple, Optional

_logger = logging.getLogger(__name__)

# Config
MAX_IMAGE_DIMENSION = 1920      # Lado más largo en píxeles
JPEG_QUALITY = 85               # Buen balance calidad/tamaño
PNG_TO_JPEG_THRESHOLD_KB = 200  # Sobre este tamaño y sin alpha real, convertir PNG a JPEG

try:
    from PIL import Image, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    _logger.warning("Pillow no está disponible; compresión de imágenes desactivada")


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


def _get_ext(filename: str) -> str:
    filename = filename or ''
    if '.' in filename:
        return '.' + filename.rsplit('.', 1)[1].lower()
    return ''


def _has_significant_alpha(img) -> bool:
    """True si la imagen tiene transparencia real (algún pixel con alpha < 250)."""
    if img.mode not in ('RGBA', 'LA', 'PA') and 'transparency' not in img.info:
        return False
    if img.mode not in ('RGBA', 'LA'):
        return 'transparency' in img.info
    try:
        alpha = img.getchannel('A') if img.mode == 'RGBA' else img.split()[-1]
        # Muestreo rápido: mirar min alpha
        return alpha.getextrema()[0] < 250
    except Exception:
        return True  # Si no podemos determinar, mejor conservar el alpha


def _is_animated(img) -> bool:
    try:
        return getattr(img, 'is_animated', False) or getattr(img, 'n_frames', 1) > 1
    except Exception:
        return False


def compress_image(raw_bytes: bytes, filename: str) -> Tuple[bytes, str, str]:
    """Comprime una imagen. Devuelve (bytes, filename_final, mime).

    Si la compresión no ayuda o falla, devuelve los bytes originales."""
    if not PIL_AVAILABLE:
        return raw_bytes, filename, ''

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()
    except Exception as e:
        _logger.debug("No se pudo abrir imagen para comprimir: %s", e)
        return raw_bytes, filename, ''

    # No tocar GIF/WebP animados
    if _is_animated(img):
        return raw_bytes, filename, ''

    original_size = len(raw_bytes)
    ext = _get_ext(filename)

    # 1) Redimensionar si es más grande que MAX_IMAGE_DIMENSION
    max_side = max(img.size)
    if max_side > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max_side
        new_w = int(img.size[0] * scale)
        new_h = int(img.size[1] * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # 2) Decidir formato de salida
    has_alpha = _has_significant_alpha(img)

    if ext in ('.png',) and not has_alpha and original_size > PNG_TO_JPEG_THRESHOLD_KB * 1024:
        # PNG grande sin transparencia real → convertir a JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        new_bytes = buf.getvalue()
        # Cambiar nombre a .jpg
        new_filename = (filename.rsplit('.', 1)[0] + '.jpg') if '.' in filename else filename + '.jpg'
        return _return_smaller(raw_bytes, filename, 'image/png',
                               new_bytes, new_filename, 'image/jpeg')

    if ext in ('.jpg', '.jpeg'):
        # Recomprimir JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        new_bytes = buf.getvalue()
        return _return_smaller(raw_bytes, filename, 'image/jpeg',
                               new_bytes, filename, 'image/jpeg')

    if ext == '.png':
        # PNG con alpha: solo optimize (preservar transparencia)
        if img.mode == 'P':
            img = img.convert('RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        new_bytes = buf.getvalue()
        return _return_smaller(raw_bytes, filename, 'image/png',
                               new_bytes, filename, 'image/png')

    if ext in ('.webp', '.bmp'):
        # Convertir a JPEG si es grande y sin alpha, sino a PNG
        if has_alpha:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            new_bytes = buf.getvalue()
            new_filename = (filename.rsplit('.', 1)[0] + '.png')
            return _return_smaller(raw_bytes, filename, 'image/' + ext[1:],
                                   new_bytes, new_filename, 'image/png')
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
            new_bytes = buf.getvalue()
            new_filename = (filename.rsplit('.', 1)[0] + '.jpg')
            return _return_smaller(raw_bytes, filename, 'image/' + ext[1:],
                                   new_bytes, new_filename, 'image/jpeg')

    return raw_bytes, filename, ''


def _return_smaller(orig_bytes, orig_name, orig_mime,
                    new_bytes, new_name, new_mime):
    """Devuelve la versión más pequeña. Si la compresión no ayudó, mantiene original."""
    if len(new_bytes) < len(orig_bytes) * 0.95:  # Al menos 5% de ahorro
        return new_bytes, new_name, new_mime
    return orig_bytes, orig_name, orig_mime


def compress_upload(file_storage) -> Tuple[bytes, str, str, dict]:
    """Recibe un objeto FileStorage de Werkzeug y devuelve la versión comprimida.

    Args:
        file_storage: request.files['...']

    Returns:
        (bytes, filename, mime_type, stats)
        stats: {'original_size': int, 'final_size': int, 'ratio': float 0..1, 'compressed': bool}
    """
    original_filename = file_storage.filename or 'archivo'
    original_mime = file_storage.mimetype or ''

    # Leer todo el contenido
    raw = file_storage.stream.read()
    # Reset del stream por si alguien lo vuelve a leer
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    original_size = len(raw)

    ext = _get_ext(original_filename)
    if ext in IMAGE_EXTENSIONS:
        out_bytes, out_filename, out_mime = compress_image(raw, original_filename)
        final_mime = out_mime or original_mime
    else:
        out_bytes = raw
        out_filename = original_filename
        final_mime = original_mime

    final_size = len(out_bytes)
    compressed = final_size < original_size
    ratio = (1 - final_size / original_size) if original_size > 0 else 0.0

    return out_bytes, out_filename, final_mime, {
        'original_size': original_size,
        'final_size': final_size,
        'ratio': ratio,
        'compressed': compressed,
    }
