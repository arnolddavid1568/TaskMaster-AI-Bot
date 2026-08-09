"""
Image operations built on Pillow (+ pytesseract for OCR, optional —
degrades gracefully if tesseract isn't installed on the host).
"""
from PIL import Image


def resize_image(path: str, output_path: str, width: int = None, height: int = None, percent: float = None) -> str:
    img = Image.open(path)
    orig_w, orig_h = img.size

    if percent:
        new_w = int(orig_w * percent / 100)
        new_h = int(orig_h * percent / 100)
    elif width and height:
        new_w, new_h = width, height
    elif width:
        new_w = width
        new_h = int(orig_h * (width / orig_w))
    elif height:
        new_h = height
        new_w = int(orig_w * (height / orig_h))
    else:
        raise ValueError("Provide width, height, or percent")

    resized = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
    resized.save(output_path)
    return output_path


def compress_image(path: str, output_path: str, quality: int = 60) -> str:
    img = Image.open(path)
    if img.mode in ("RGBA", "P") and output_path.lower().endswith((".jpg", ".jpeg")):
        img = img.convert("RGB")
    img.save(output_path, optimize=True, quality=quality)
    return output_path


def convert_image(path: str, output_path: str) -> str:
    img = Image.open(path)
    target_format = output_path.rsplit(".", 1)[-1].upper()
    if target_format == "JPG":
        target_format = "JPEG"
    if target_format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(output_path, format=target_format)
    return output_path


def ocr_image(path: str) -> str:
    try:
        import pytesseract
    except ImportError:
        return "⚠️ OCR isn't available on this deployment (pytesseract/tesseract not installed)."
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text.strip() or "(No text detected in image)"
    except Exception as e:
        return f"⚠️ OCR failed: {e}"


def get_image_info(path: str) -> dict:
    img = Image.open(path)
    return {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
    }
