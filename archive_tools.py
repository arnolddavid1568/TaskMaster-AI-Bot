"""
ZIP creation and extraction, with basic zip-bomb / path-traversal guards.
"""
import zipfile
from pathlib import Path

_MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200MB safety cap


def create_zip(file_paths: list[str], output_path: str) -> str:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            zf.write(fp, arcname=Path(fp).name)
    return output_path


def extract_zip(zip_path: str, output_dir: str) -> list[str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    extracted = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        total_size = sum(info.file_size for info in zf.infolist())
        if total_size > _MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Archive too large to extract safely (uncompressed size exceeds limit).")

        for info in zf.infolist():
            # guard against path traversal (zip slip)
            dest = Path(output_dir) / info.filename
            if not str(dest.resolve()).startswith(str(Path(output_dir).resolve())):
                continue
            if info.is_dir():
                continue
            zf.extract(info, output_dir)
            extracted.append(str(dest))

    return extracted


def list_zip_contents(zip_path: str) -> list[dict]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return [
            {"name": i.filename, "size": i.file_size, "compressed": i.compress_size}
            for i in zf.infolist()
        ]
