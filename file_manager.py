"""
Handles temporary file storage: unique per-user working directories,
size validation, and scheduled auto-deletion so the disk never fills
up on a free-tier host.
"""
import shutil
import time
import uuid
from pathlib import Path

import config


def user_temp_dir(user_id: int) -> Path:
    d = config.TEMP_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_temp_path(user_id: int, filename: str) -> Path:
    d = user_temp_dir(user_id)
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    return d / safe_name


def cleanup_user_dir(user_id: int):
    d = config.TEMP_DIR / str(user_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def cleanup_expired():
    """Deletes any temp file older than FILE_RETENTION_MINUTES. Call this
    periodically from a JobQueue task."""
    cutoff = time.time() - (config.FILE_RETENTION_MINUTES * 60)
    if not config.TEMP_DIR.exists():
        return
    for user_dir in config.TEMP_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        for f in user_dir.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass
        # remove empty user dirs
        try:
            if not any(user_dir.iterdir()):
                user_dir.rmdir()
        except OSError:
            pass


def check_size_ok(size_bytes: int) -> bool:
    return size_bytes <= config.MAX_FILE_SIZE_MB * 1024 * 1024


def human_size(num_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"
