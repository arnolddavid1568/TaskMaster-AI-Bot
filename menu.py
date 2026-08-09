"""
/start, /help, and the inline-button category menu that drives all the
file-based tools (PDF, image, document, archive, file analysis).
Instant text-command tools (calculator, password gen, etc.) are handled
in handlers/instant_tools.py and don't need this menu.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from handlers import state
from utils.decorators import guarded

WELCOME = (
    "👋 *Welcome to {name}!*\n\n"
    "I'm a Swiss-army-knife bot for files, text, dev utilities, and more.\n\n"
    "Tap a category below to get started with file tools, or use "
    "/help to see every command (most tools also work as direct commands, "
    "no menu needed)."
).format(name=config.BOT_NAME)

HELP_TEXT = """
*{name} — Command Reference*

*📄 PDF*
/mergepdf — merge multiple PDFs
/splitpdf — split a PDF by page range
/compresspdf — shrink a PDF's size
/pdftext — extract text from a PDF

*🖼️ Image*
/resize — resize an image
/imgcompress — compress an image
/imgconvert — convert image format
/ocr — extract text from an image

*📝 Document*
/txt2pdf /pdf2txt /docx2txt /txt2docx /docx2pdf

*🔤 Text*
/summarize <text or reply> — summarize
/rewrite <text or reply> — rewrite/clean up
/wordcount <text or reply> — count words/chars/sentences
/clean <text or reply> — strip extra whitespace/junk

*🌍 Translation*
/translate <lang_code> <text> — e.g. `/translate fr Hello there`

*🔗 URL*
/urlinfo <url> — fetch title/description/metadata
/qr <text or url> — generate a QR code

*📊 File analysis*
/analyze — send a file to inspect type/size/contents

*🔐 Security*
/genpass [length] — generate a strong password
/hash <text> [algo] — hash text (default sha256)

*🧮 Calculator*
/calc <expression> — e.g. `/calc (12+8)*3`
/percent <value> <percent> — e.g. `/percent 250 15`
/convert <value> <from> <to> — e.g. `/convert 10 km mi`

*📅 Date*
/age <YYYY-MM-DD> — calculate age
/datediff <date1> <date2> — days between two dates
/countdown <date> — days remaining until a date

*🗜️ Archive*
/zipcreate — combine files into a .zip
/unzip — extract a .zip archive

*🎨 ASCII*
/ascii <text> — turn text into an ASCII banner

*💻 Developer*
/json <raw json or reply> — pretty-print/validate JSON
/base64 encode|decode <text>
/uuid [count] — generate UUID(s)

*📱 Telegram utilities*
/id — get your Telegram user & chat ID (reply to a message to check theirs)
/fmt — show Markdown/HTML formatting examples

*⚙️ Other*
/menu — open the button-based tool menu
/cancel — cancel a pending file operation
""".format(name=config.BOT_NAME)


CATEGORIES = {
    "cat_pdf": ("📄 PDF Tools", ["merge_pdf", "split_pdf", "compress_pdf", "pdf_text"]),
    "cat_image": ("🖼️ Image Tools", ["resize_image", "compress_image", "convert_image", "ocr_image"]),
    "cat_doc": ("📝 Document Tools", ["txt2pdf", "pdf2txt", "docx2txt", "txt2docx", "docx2pdf"]),
    "cat_archive": ("🗜️ Archive Tools", ["zip_create", "zip_extract"]),
    "cat_analysis": ("📊 File Analysis", ["analyze_file"]),
}


def main_menu_keyboard():
    rows = [[InlineKeyboardButton(label, callback_data=key)] for key, (label, _) in CATEGORIES.items()]
    return InlineKeyboardMarkup(rows)


def category_keyboard(cat_key: str):
    _, actions = CATEGORIES[cat_key]
    rows = [[InlineKeyboardButton(state.ACTION_LABELS[a], callback_data=f"action:{a}")] for a in actions]
    rows.append([InlineKeyboardButton("« Back", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)


@guarded("start")
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@guarded("help")
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


@guarded("menu")
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pick a category:", reply_markup=main_menu_keyboard())


@guarded("cancel")
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.clear_state(context)
    await update.message.reply_text("✅ Cancelled. Nothing pending now.")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_home":
        await query.edit_message_text("Pick a category:", reply_markup=main_menu_keyboard())
        return

    if query.data in CATEGORIES:
        label, _ = CATEGORIES[query.data]
        await query.edit_message_text(f"{label} — choose a tool:", reply_markup=category_keyboard(query.data))
        return

    if query.data.startswith("action:"):
        action = query.data.split(":", 1)[1]
        state.set_action(context, action)

        if action in state.MULTI_FILE_ACTIONS:
            verb = "PDFs" if action == "merge_pdf" else "files"
            msg = f"📤 Send the {verb} one at a time. When you're done, send /done (or /cancel to stop)."
        else:
            msg = "📤 Send the file you'd like to process (or /cancel)."

        await query.edit_message_text(f"*{state.ACTION_LABELS[action]}*\n\n{msg}", parse_mode="Markdown")
