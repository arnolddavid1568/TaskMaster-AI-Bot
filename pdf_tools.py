"""
PDF operations built on pypdf. All functions are synchronous/blocking —
call them through utils.task_queue.task_queue.submit() from handlers so
big files don't block the event loop.
"""
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def merge_pdfs(paths: list[str], output_path: str) -> str:
    writer = PdfWriter()
    for p in paths:
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def split_pdf(path: str, output_dir: str, page_range: str = None) -> list[str]:
    """page_range like '1-3,5' (1-indexed, inclusive). If None, splits
    into one file per page."""
    reader = PdfReader(path)
    total = len(reader.pages)
    out_paths = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if page_range:
        indices = _parse_page_range(page_range, total)
        writer = PdfWriter()
        for i in indices:
            writer.add_page(reader.pages[i])
        out_path = str(Path(output_dir) / "split_selection.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        out_paths.append(out_path)
    else:
        for i in range(total):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            out_path = str(Path(output_dir) / f"page_{i + 1}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            out_paths.append(out_path)
    return out_paths


def _parse_page_range(spec: str, total_pages: int) -> list[int]:
    indices = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start, end = int(start), int(end)
            indices.extend(range(start - 1, min(end, total_pages)))
        elif part.isdigit():
            n = int(part)
            if 1 <= n <= total_pages:
                indices.append(n - 1)
    return sorted(set(indices))


def compress_pdf(path: str, output_path: str) -> str:
    """Lossy-ish compression: strips unused objects, compresses streams,
    and downsamples/removes duplicate resources where pypdf allows."""
    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # Pages must belong to the writer before their content streams can be
    # re-compressed (pypdf requires an indirect reference from a writer).
    for page in writer.pages:
        try:
            page.compress_content_streams()
        except Exception:
            pass  # if a page can't be compressed, leave it as-is rather than fail the whole job

    writer.compress_identical_objects()
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def extract_text(path: str) -> str:
    reader = PdfReader(path)
    chunks = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunks.append(f"--- Page {i} ---\n{text.strip()}")
    return "\n\n".join(chunks)


def get_pdf_info(path: str) -> dict:
    reader = PdfReader(path)
    meta = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "title": getattr(meta, "title", None),
        "author": getattr(meta, "author", None),
    }
