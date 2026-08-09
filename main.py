"""
TaskMaster AI Bot — entrypoint.

Run locally:
    python main.py

Deploy on Render/Railway: point the service at this file (see README.md
and render.yaml / Procfile for platform-specific config). Requires the
BOT_TOKEN env var at minimum.
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database
from handlers import admin, instant_tools, menu, router
from utils.file_manager import cleanup_expired

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def unrecognized_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches plain text messages. If the user has a pending param-based
    action, feed it there; otherwise nudge them toward /help."""
    consumed = await router.handle_param_text(update, context)
    if consumed:
        return
    await update.message.reply_text(
        "Not sure what to do with that. Try /menu for file tools or /help for the full command list."
    )


async def periodic_cleanup(context: ContextTypes.DEFAULT_TYPE):
    cleanup_expired()


def build_app() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    database.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    # --- Menu / navigation ---
    app.add_handler(CommandHandler("start", menu.start_cmd))
    app.add_handler(CommandHandler("help", menu.help_cmd))
    app.add_handler(CommandHandler("menu", menu.menu_cmd))
    app.add_handler(CommandHandler("cancel", menu.cancel_cmd))
    app.add_handler(CallbackQueryHandler(menu.menu_callback))

    # --- File-flow control commands ---
    app.add_handler(CommandHandler("done", router.done_cmd))

    # --- Direct file-tool shortcuts (skip the menu, jump straight to "send a file") ---
    from handlers import state as state_mod

    def make_direct_action_cmd(action: str):
        async def _cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            state_mod.set_action(context, action)
            if action in state_mod.MULTI_FILE_ACTIONS:
                await update.message.reply_text(
                    f"📤 Send the files one at a time. When done, send /done (or /cancel)."
                )
            else:
                await update.message.reply_text("📤 Send the file to process (or /cancel).")
        return _cmd

    direct_commands = {
        "mergepdf": "merge_pdf",
        "splitpdf": "split_pdf",
        "compresspdf": "compress_pdf",
        "pdftext": "pdf_text",
        "resize": "resize_image",
        "imgcompress": "compress_image",
        "imgconvert": "convert_image",
        "ocr": "ocr_image",
        "txt2pdf": "txt2pdf",
        "pdf2txt": "pdf2txt",
        "docx2txt": "docx2txt",
        "txt2docx": "txt2docx",
        "docx2pdf": "docx2pdf",
        "zipcreate": "zip_create",
        "unzip": "zip_extract",
        "analyze": "analyze_file",
    }
    for cmd_name, action_name in direct_commands.items():
        app.add_handler(CommandHandler(cmd_name, make_direct_action_cmd(action_name)))

    # --- Instant (no-file) tools ---
    app.add_handler(CommandHandler("summarize", instant_tools.summarize_cmd))
    app.add_handler(CommandHandler("rewrite", instant_tools.rewrite_cmd))
    app.add_handler(CommandHandler("wordcount", instant_tools.wordcount_cmd))
    app.add_handler(CommandHandler("clean", instant_tools.clean_cmd))
    app.add_handler(CommandHandler("translate", instant_tools.translate_cmd))
    app.add_handler(CommandHandler("urlinfo", instant_tools.urlinfo_cmd))
    app.add_handler(CommandHandler("qr", instant_tools.qr_cmd))
    app.add_handler(CommandHandler("genpass", instant_tools.genpass_cmd))
    app.add_handler(CommandHandler("hash", instant_tools.hash_cmd))
    app.add_handler(CommandHandler("calc", instant_tools.calc_cmd))
    app.add_handler(CommandHandler("percent", instant_tools.percent_cmd))
    app.add_handler(CommandHandler("convert", instant_tools.convert_cmd))
    app.add_handler(CommandHandler("age", instant_tools.age_cmd))
    app.add_handler(CommandHandler("datediff", instant_tools.datediff_cmd))
    app.add_handler(CommandHandler("countdown", instant_tools.countdown_cmd))
    app.add_handler(CommandHandler("ascii", instant_tools.ascii_cmd))
    app.add_handler(CommandHandler("json", instant_tools.json_cmd))
    app.add_handler(CommandHandler("base64", instant_tools.base64_cmd))
    app.add_handler(CommandHandler("uuid", instant_tools.uuid_cmd))
    app.add_handler(CommandHandler("id", instant_tools.id_cmd))
    app.add_handler(CommandHandler("fmt", instant_tools.fmt_cmd))

    # --- Admin ---
    app.add_handler(CommandHandler("stats", admin.stats_cmd))
    app.add_handler(CommandHandler("logs", admin.logs_cmd))
    app.add_handler(CommandHandler("ban", admin.ban_cmd))
    app.add_handler(CommandHandler("unban", admin.unban_cmd))
    app.add_handler(CommandHandler("broadcast", admin.broadcast_cmd))

    # --- File uploads (must come after commands) ---
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, router.handle_file))

    # --- Fallback: any other text (feeds pending param actions) ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_text))

    # --- Periodic temp-file cleanup ---
    if app.job_queue:
        app.job_queue.run_repeating(periodic_cleanup, interval=600, first=60)

    return app


def main():
    app = build_app()
    logger.info("%s starting...", config.BOT_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
