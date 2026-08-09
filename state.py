"""
Minimal per-user state machine for multi-step flows (upload a file ->
optionally send a parameter -> get a result). State lives in
context.user_data, which python-telegram-bot already keeps per-user.
"""

# Actions that just need ONE file and then run immediately
AUTO_RUN_ACTIONS = {
    "compress_pdf", "pdf_text", "ocr_image", "zip_extract", "analyze_file",
    "txt2pdf", "pdf2txt", "docx2txt", "txt2docx", "docx2pdf",
}

# Actions that need ONE file, then a text parameter before running
PARAM_ACTIONS = {
    "split_pdf": "Send the page range to extract (e.g. `1-3,5`) or `all` to split every page.",
    "resize_image": "Send the target size, e.g. `800x600` or `50%`.",
    "compress_image": "Send a quality level 1-100 (lower = smaller file), or `default`.",
    "convert_image": "Send the target format: `png`, `jpg`, `webp`, or `bmp`.",
}

# Actions that collect MULTIPLE files until the user sends /done
MULTI_FILE_ACTIONS = {"merge_pdf", "zip_create"}

ACTION_LABELS = {
    "merge_pdf": "📄 Merge PDFs",
    "split_pdf": "📄 Split PDF",
    "compress_pdf": "📄 Compress PDF",
    "pdf_text": "📄 Extract PDF text",
    "resize_image": "🖼️ Resize image",
    "compress_image": "🖼️ Compress image",
    "convert_image": "🖼️ Convert image format",
    "ocr_image": "🖼️ OCR (image to text)",
    "txt2pdf": "📝 TXT → PDF",
    "pdf2txt": "📝 PDF → TXT",
    "docx2txt": "📝 DOCX → TXT",
    "txt2docx": "📝 TXT → DOCX",
    "docx2pdf": "📝 DOCX → PDF",
    "zip_create": "🗜️ Create ZIP",
    "zip_extract": "🗜️ Extract ZIP",
    "analyze_file": "📊 Analyze file",
}


def set_action(context, action: str):
    context.user_data["state"] = {"action": action, "files": [], "meta": {}}


def get_state(context) -> dict | None:
    return context.user_data.get("state")


def clear_state(context):
    context.user_data.pop("state", None)


def add_file(context, path: str):
    state = get_state(context)
    if state is not None:
        state["files"].append(path)
