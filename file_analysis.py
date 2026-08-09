"""
Basic file analysis: MIME/type detection, size, and a lightweight
content preview depending on the detected type.
"""
import mimetypes
from pathlib import Path

from utils.file_manager import human_size


def analyze_file(path: str, original_filename: str = None) -> dict:
    p = Path(path)
    name = original_filename or p.name
    size = p.stat().st_size
    mime, _ = mimetypes.guess_type(name)
    mime = mime or "application/octet-stream"

    info = {
        "filename": name,
        "size_bytes": size,
        "size_human": human_size(size),
        "mime_type": mime,
        "extension": p.suffix.lower(),
    }

    # Lightweight content preview
    try:
        if mime.startswith("text/") or p.suffix.lower() in (".txt", ".csv", ".json", ".md", ".py", ".log"):
            text = p.read_text(encoding="utf-8", errors="replace")
            info["preview"] = text[:300]
            info["line_count"] = text.count("\n") + 1
        elif p.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(path)
            info["pages"] = len(reader.pages)
            info["encrypted"] = reader.is_encrypted
        elif mime.startswith("image/"):
            from PIL import Image

            img = Image.open(path)
            info["dimensions"] = f"{img.width}x{img.height}"
            info["image_format"] = img.format
    except Exception as e:
        info["preview_error"] = str(e)

    return info
