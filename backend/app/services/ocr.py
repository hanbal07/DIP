"""OCR service with pluggable engines (PaddleOCR, Tesseract, or mock).

The OCR engine is configured via `OCR_ENGINE`. For tests and development the `mock` engine
returns deterministic placeholder text. OCR is only invoked for pages that genuinely lack
extractable text (scanned documents).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OcrPageResult:
    text: str
    confidence: float


class OCRService:
    def __init__(self) -> None:
        self.engine = settings.ocr_engine.lower()

    def supports(self) -> bool:
        return self.engine in {"paddleocr", "tesseract", "mock"}

    def ocr_image(self, pil_image) -> OcrPageResult:
        """Run OCR on a PIL image; returns extracted text + mean confidence."""
        if self.engine == "mock":
            return self._mock_ocr(pil_image)
        if self.engine == "paddleocr":
            return self._paddle_ocr(pil_image)
        if self.engine == "tesseract":
            return self._tesseract_ocr(pil_image)
        raise RuntimeError(f"unsupported OCR engine: {self.engine}")

    # ---------------------------------------------------------------- mock

    def _mock_ocr(self, pil_image) -> OcrPageResult:
        """Deterministic placeholder text for tests (never used in production)."""
        w, h = pil_image.size
        # A modest confidence value derived deterministically from image size; this is a
        # development stub and must not be confused with genuine OCR confidence.
        confidence = round(0.5 + ((w + h) % 20) / 100.0, 3)
        return OcrPageResult(
            text=f"[OCR placeholder page content {w}x{h}]",
            confidence=confidence,
        )

    # ------------------------------------------------------------- paddleocr

    def _paddle_ocr(self, pil_image) -> OcrPageResult:
        try:
            from paddleocr import PaddleOCR

            if not hasattr(self, "_paddle"):
                self._paddle = PaddleOCR(lang=settings.ocr_lang, show_log=False)
            result = self._paddle.ocr(pil_image, cls=True)
            lines = []
            confs: list[float] = []
            for page in result or []:
                for line in page or []:
                    box, (text, conf) = line
                    lines.append(text)
                    confs.append(float(conf))
            return OcrPageResult(
                text="\n".join(lines),
                confidence=float(sum(confs) / len(confs)) if confs else 0.0,
            )
        except Exception as exc:  # pragma: no cover - depends on optional native lib
            logger.error("PaddleOCR failed: %s", exc)
            raise

    # ------------------------------------------------------------ tesseract

    def _tesseract_ocr(self, pil_image) -> OcrPageResult:
        try:
            import pytesseract
            from pytesseract import Output

            kwargs: dict = {}
            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            data = pytesseract.image_to_data(
                pil_image, lang=settings.ocr_lang, output_type=Output.DICT, **kwargs
            )
            text_parts = []
            confs: list[float] = []
            n = len(data["text"])
            for i in range(n):
                word = (data["text"][i] or "").strip()
                if word:
                    text_parts.append(word)
                    try:
                        confs.append(float(data["conf"][i]))
                    except (TypeError, ValueError):
                        pass
            return OcrPageResult(
                text=" ".join(text_parts),
                confidence=float(sum(confs) / len(confs)) if confs else 0.0,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Tesseract OCR failed: %s", exc)
            raise


def get_ocr_service() -> OCRService:
    return OCRService()
