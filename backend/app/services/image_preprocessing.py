"""Image preprocessing for improved OCR quality (OpenCV when available, else PIL)."""
from __future__ import annotations

import logging

from PIL import Image, ImageOps, ImageFilter

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore
    HAS_CV2 = True
except Exception:  # pragma: no cover - opencv optional
    HAS_CV2 = False


def open_image(data: bytes) -> Image.Image:
    img = Image.open(data if isinstance(data, bytes) else __import__("io").BytesIO(data))
    img = img.convert("RGB")
    return img


def preprocess_for_ocr(img: Image.Image, render_dpi: int | None = None) -> Image.Image:
    """Preprocess a page image before OCR: deskew, denoise, grayscale, threshold."""
    dpi = render_dpi or 200
    target_min = int(dpi / 72 * 1000)  # ~ 200 DPI worth of typical text baseline width
    if img.width < 1200:
        scale = 1200 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

    if HAS_CV2:
        try:
            return _preprocess_cv2(img)
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenCV preprocessing failed (%s); using PIL fallback", exc)

    # PIL fallback: grayscale, autocontrast, slight sharpen.
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray)
    return gray.filter(ImageFilter.SHARPEN)


def _preprocess_cv2(img: Image.Image) -> Image.Image:
    import numpy as np

    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    # Denoise.
    arr = cv2.fastNlMeansDenoising(arr, None, 10, 7, 21)
    # Adaptive threshold for clean binarisation.
    arr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 12)
    return Image.fromarray(arr)
