"""
Routes incoming documents/photos and follow-up text messages to the
right tool function, based on the user's current state (see
handlers/state.py). This is the glue between Telegram updates and the
pure functions in utils/tools/*.py.
"""
import logging
from pathlib import Path

from telegram import InputFile, Update
from telegram.ext import ContextTypes

import config
from handlers import state
from utils import file_manager
from utils.decorators import guarded
from utils.task_queue import task_queue
from utils.tools import archive_tools, document_tools, file_analysis, image_tools, pdf_tools

logger = logging.getLogger(__name__)

EXT_FOR_ACTION_INPUT = {
    "merge_pdf": [".pdf"],
    "split_pdf": [".pdf"],
    "compress_pdf": [".pdf"],
    "pdf_text": [".pdf"],
    "resize_image": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "compress_image": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "convert_image": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "ocr_image": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "txt2pdf": [".txt"],
    "pdf2txt": [".pdf"],
    "docx2txt": [".docx"],
    "txt2docx": [".txt"],
    "docx2pdf": [".docx"],
    "zip_create": None,  # any file type
    "zip_extract": [".zip"],
    "analyze_file": None,  # any file type
}


async def _download_incoming_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[str, str] | None:
    """Downloads the incoming document/photo to a temp path.
    Returns (local_path, original_filename) or None if nothing usable."""
    user_id = update.effective_user.id
    msg = update.effective_message

    tg_file = None
    filename = None

    if msg.document:
        if not file_manager.check_size_ok(msg.document.file_size or 0):
            await msg.reply_text(f"⚠️ File too large. Max size is {config.MAX_FILE_SIZE_MB}MB.")
            return None
        tg_file = await msg.document.get_file()
        filename = msg.document.file_name or "file"
    elif msg.photo:
        photo = msg.photo[-1]
        tg_file = await photo.get_file()
        filename = f"photo_{photo.file_unique_id}.jpg"

    if tg_file is None:
        return None

    local_path = file_manager.new_temp_path(user_id, filename)
    await tg_file.download_to_drive(custom_path=str(local_path))
    return str(local_path), filename


@guarded("file_upload")
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = state.get_state(context)
    if st is None:
        await update.message.reply_text(
            "I've got a file, but I'm not sure what to do with it yet. "
            "Use /menu to pick a tool first, or check /help for direct commands."
        )
        return

    action = st["action"]
    allowed_exts = EXT_FOR_ACTION_INPUT.get(action)

    downloaded = await _download_incoming_file(update, context)
    if downloaded is None:
        return
    local_path, filename = downloaded

    if allowed_exts and Path(filename).suffix.lower() not in allowed_exts:
        await update.message.reply_text(
            f"⚠️ That file type isn't right for {state.ACTION_LABELS[action]}. "
            f"Expected: {', '.join(allowed_exts)}"
        )
        return

    state.add_file(context, local_path)

    if action in state.MULTI_FILE_ACTIONS:
        count = len(st["files"])
        await update.message.reply_text(f"✅ Got it ({count} file{'s' if count != 1 else ''} so far). Send another or /done.")
        return

    if action in state.PARAM_ACTIONS:
        st["meta"]["filename"] = filename
        await update.message.reply_text(state.PARAM_ACTIONS[action], parse_mode="Markdown")
        return

    # auto-run actions
    await _run_action(update, context, action, st["files"], filename)
    state.clear_state(context)


@guarded("done")
async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = state.get_state(context)
    if st is None or st["action"] not in state.MULTI_FILE_ACTIONS:
        await update.message.reply_text("Nothing to finish right now.")
        return

    if not st["files"]:
        await update.message.reply_text("You haven't sent any files yet. Send at least one, or /cancel.")
        return

    if st["action"] == "merge_pdf" and len(st["files"]) < 2:
        await update.message.reply_text("Send at least 2 PDFs to merge, or /cancel.")
        return

    await _run_action(update, context, st["action"], st["files"], None)
    state.clear_state(context)


@guarded("param_input")
async def handle_param_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if this text was consumed as a parameter for a pending action."""
    st = state.get_state(context)
    if st is None or st["action"] not in state.PARAM_ACTIONS:
        return False

    param = update.message.text.strip()
    await _run_action(update, context, st["action"], st["files"], st["meta"].get("filename"), param=param)
    state.clear_state(context)
    return True


async def _run_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str,
                       files: list[str], filename: str | None, param: str | None = None):
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("⏳ Working on it...")

    try:
        result = await task_queue.submit(_execute, action, files, filename, param, user_id)
    except RuntimeError as e:
        await status_msg.edit_text(f"⚠️ {e}")
        return
    except Exception as e:
        logger.exception("Tool execution failed for action=%s", action)
        await status_msg.edit_text(f"❌ Failed: {e}")
        return

    await status_msg.delete()

    def _looks_like_existing_file(s: str) -> bool:
        try:
            return len(s) < 1000 and Path(s).exists()
        except (OSError, ValueError):
            return False

    if isinstance(result, str) and not _looks_like_existing_file(result):
        # plain text result (e.g. extracted text, OCR output)
        text = result
        if len(text) > 3500:
            path = file_manager.new_temp_path(user_id, "result.txt")
            Path(path).write_text(text, encoding="utf-8")
            await update.message.reply_document(InputFile(str(path)), filename="result.txt",
                                                  caption="Output was long, sent as a file.")
        else:
            await update.message.reply_text(text or "(empty result)")
    elif isinstance(result, list):
        for path in result[:10]:
            await update.message.reply_document(InputFile(path))
        if len(result) > 10:
            await update.message.reply_text(f"...and {len(result) - 10} more files (only first 10 sent).")
    else:
        await update.message.reply_document(InputFile(str(result)))


def _execute(action: str, files: list[str], filename: str | None, param: str | None, user_id: int):
    """Runs synchronously inside the task queue's thread pool."""
    out_dir = file_manager.user_temp_dir(user_id)

    if action == "merge_pdf":
        out = out_dir / "merged.pdf"
        return pdf_tools.merge_pdfs(files, str(out))

    if action == "split_pdf":
        page_range = None if (param or "").lower() == "all" else param
        return pdf_tools.split_pdf(files[0], str(out_dir / "split"), page_range)

    if action == "compress_pdf":
        out = out_dir / f"compressed_{Path(filename).stem}.pdf"
        return pdf_tools.compress_pdf(files[0], str(out))

    if action == "pdf_text":
        return pdf_tools.extract_text(files[0])

    if action == "resize_image":
        out = out_dir / f"resized_{Path(filename).name}"
        if "%" in param:
            pct = float(param.replace("%", "").strip())
            return image_tools.resize_image(files[0], str(out), percent=pct)
        w, h = param.lower().split("x")
        return image_tools.resize_image(files[0], str(out), width=int(w), height=int(h))

    if action == "compress_image":
        quality = 60 if param.lower() == "default" else int(param)
        out = out_dir / f"compressed_{Path(filename).name}"
        return image_tools.compress_image(files[0], str(out), quality=quality)

    if action == "convert_image":
        target = param.lower().lstrip(".")
        out = out_dir / f"{Path(filename).stem}.{target}"
        return image_tools.convert_image(files[0], str(out))

    if action == "ocr_image":
        return image_tools.ocr_image(files[0])

    if action == "txt2pdf":
        out = out_dir / f"{Path(filename).stem}.pdf"
        return document_tools.txt_to_pdf(files[0], str(out))

    if action == "pdf2txt":
        out = out_dir / f"{Path(filename).stem}.txt"
        return document_tools.pdf_to_txt(files[0], str(out))

    if action == "docx2txt":
        out = out_dir / f"{Path(filename).stem}.txt"
        return document_tools.docx_to_txt(files[0], str(out))

    if action == "txt2docx":
        out = out_dir / f"{Path(filename).stem}.docx"
        return document_tools.txt_to_docx(files[0], str(out))

    if action == "docx2pdf":
        out = out_dir / f"{Path(filename).stem}.pdf"
        return document_tools.docx_to_pdf(files[0], str(out))

    if action == "zip_create":
        out = out_dir / "archive.zip"
        return archive_tools.create_zip(files, str(out))

    if action == "zip_extract":
        extracted = archive_tools.extract_zip(files[0], str(out_dir / "extracted"))
        return extracted

    if action == "analyze_file":
        info = file_analysis.analyze_file(files[0], filename)
        lines = ["File Analysis"]
        for k, v in info.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    raise ValueError(f"Unknown action: {action}")
