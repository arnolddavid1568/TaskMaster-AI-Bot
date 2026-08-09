"""
Handlers for tools that don't need a file upload — they take arguments
directly on the command line (or operate on a replied-to message).
"""
from telegram import InputFile, Update
from telegram.ext import ContextTypes

from utils import file_manager
from utils.decorators import guarded
from utils.task_queue import task_queue
from utils.tools import (
    ascii_tools,
    calculator,
    date_tools,
    dev_tools,
    security_tools,
    text_tools,
    translation,
    url_tools,
)


def _get_text_arg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Prefers command args; falls back to the text of a replied-to message."""
    if context.args:
        return " ".join(context.args)
    if update.message.reply_to_message and update.message.reply_to_message.text:
        return update.message.reply_to_message.text
    return ""


# ---------- Text tools ----------

@guarded("summarize")
async def summarize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/summarize <text>` or reply to a message with /summarize.",
                                          parse_mode="Markdown")
        return
    result = await task_queue.submit(text_tools.summarize, text)
    await update.message.reply_text(result)


@guarded("rewrite")
async def rewrite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/rewrite <text>` or reply to a message with /rewrite.",
                                          parse_mode="Markdown")
        return
    result = await task_queue.submit(text_tools.rewrite, text)
    await update.message.reply_text(result)


@guarded("wordcount")
async def wordcount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/wordcount <text>` or reply to a message with /wordcount.",
                                          parse_mode="Markdown")
        return
    stats = text_tools.word_count(text)
    lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in stats.items()]
    await update.message.reply_text("\n".join(lines))


@guarded("clean")
async def clean_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/clean <text>` or reply to a message with /clean.",
                                          parse_mode="Markdown")
        return
    await update.message.reply_text(text_tools.clean_text(text))


# ---------- Translation ----------

@guarded("translate")
async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/translate <target_lang_code> <text>`\nExample: `/translate fr Hello there`",
            parse_mode="Markdown",
        )
        return
    target_lang = context.args[0]
    text = " ".join(context.args[1:])
    try:
        result = await task_queue.submit(translation.translate_text, text, target_lang)
        await update.message.reply_text(f"🌍 ({result['source_lang']} → {result['target_lang']}):\n{result['translated']}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Translation failed: {e}")


# ---------- URL tools ----------

@guarded("urlinfo")
async def urlinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/urlinfo <url>`", parse_mode="Markdown")
        return
    url = context.args[0]
    try:
        meta = await task_queue.submit(url_tools.get_url_metadata, url)
        lines = [f"🔗 {meta['url']} (status {meta['status_code']})"]
        if meta.get("title"):
            lines.append(f"Title: {meta['title']}")
        if meta.get("description"):
            lines.append(f"Description: {meta['description'][:300]}")
        if meta.get("content_type"):
            lines.append(f"Content-Type: {meta['content_type']}")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Couldn't fetch that URL: {e}")


@guarded("qr")
async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/qr <text or url>`", parse_mode="Markdown")
        return
    out_path = file_manager.new_temp_path(update.effective_user.id, "qr.png")
    await task_queue.submit(url_tools.generate_qr, text, str(out_path))
    await update.message.reply_photo(InputFile(str(out_path)))


# ---------- Security ----------

@guarded("genpass")
async def genpass_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 16
    if context.args and context.args[0].isdigit():
        length = int(context.args[0])
    pwd = security_tools.generate_password(length)
    await update.message.reply_text(f"🔐 `{pwd}`", parse_mode="Markdown")


@guarded("hash")
async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/hash <text> [algorithm]` (default: sha256)", parse_mode="Markdown")
        return
    algo = "sha256"
    args = context.args
    if args[-1].lower() in ("md5", "sha1", "sha256", "sha512"):
        algo = args[-1].lower()
        args = args[:-1]
    text = " ".join(args)
    try:
        digest = security_tools.hash_text(text, algo)
        await update.message.reply_text(f"🔐 {algo}: `{digest}`", parse_mode="Markdown")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


# ---------- Calculator ----------

@guarded("calc")
async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/calc <expression>` e.g. `/calc (12+8)*3`", parse_mode="Markdown")
        return
    expr = " ".join(context.args)
    try:
        result = calculator.safe_eval(expr)
        await update.message.reply_text(f"🧮 {expr} = {result}")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


@guarded("percent")
async def percent_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/percent <value> <percent>` e.g. `/percent 250 15`", parse_mode="Markdown")
        return
    try:
        value, percent = float(context.args[0]), float(context.args[1])
        result = calculator.percent_of(value, percent)
        await update.message.reply_text(f"🧮 {percent}% of {value} = {result}")
    except ValueError:
        await update.message.reply_text("⚠️ Please provide two numbers.")


@guarded("convert")
async def convert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: `/convert <value> <from_unit> <to_unit>` e.g. `/convert 10 km mi`",
                                          parse_mode="Markdown")
        return
    try:
        value = float(context.args[0])
        result = calculator.convert_unit(value, context.args[1], context.args[2])
        await update.message.reply_text(f"🧮 {value} {context.args[1]} = {round(result, 4)} {context.args[2]}")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


# ---------- Date tools ----------

@guarded("age")
async def age_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/age <YYYY-MM-DD>`", parse_mode="Markdown")
        return
    try:
        result = date_tools.calculate_age(" ".join(context.args))
        await update.message.reply_text(
            f"🎂 Age: {result['years']} years ({result['total_days']} days)\n"
            f"Next birthday in {result['days_to_next_birthday']} days."
        )
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


@guarded("datediff")
async def datediff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/datediff <date1> <date2>`", parse_mode="Markdown")
        return
    try:
        result = date_tools.date_difference(context.args[0], context.args[1])
        await update.message.reply_text(
            f"📅 {result['total_days']} days apart (~{result['approx_years']}y "
            f"{result['approx_months']}m {result['approx_days']}d)"
        )
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


@guarded("countdown")
async def countdown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/countdown <date>`", parse_mode="Markdown")
        return
    try:
        result = date_tools.countdown(" ".join(context.args))
        if result["status"] == "upcoming":
            await update.message.reply_text(f"⏳ {result['days_remaining']} days until {result['target_date']}")
        else:
            await update.message.reply_text(f"📅 {result['target_date']} was {result['days_remaining']} days ago")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


# ---------- ASCII ----------

@guarded("ascii")
async def ascii_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_text_arg(update, context)
    if not text:
        await update.message.reply_text("Usage: `/ascii <text>`", parse_mode="Markdown")
        return
    banner = ascii_tools.make_banner(text)
    await update.message.reply_text(f"```\n{banner}\n```", parse_mode="Markdown")


# ---------- Dev tools ----------

@guarded("json")
async def json_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = _get_text_arg(update, context)
    if not raw:
        await update.message.reply_text("Usage: `/json <raw json>` or reply to a message with /json.",
                                          parse_mode="Markdown")
        return
    try:
        pretty = dev_tools.format_json(raw)
        await update.message.reply_text(f"```json\n{pretty[:3800]}\n```", parse_mode="Markdown")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


@guarded("base64")
async def base64_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 or context.args[0].lower() not in ("encode", "decode"):
        await update.message.reply_text("Usage: `/base64 encode|decode <text>`", parse_mode="Markdown")
        return
    mode = context.args[0].lower()
    text = " ".join(context.args[1:])
    try:
        result = dev_tools.base64_encode(text) if mode == "encode" else dev_tools.base64_decode(text)
        await update.message.reply_text(f"`{result}`", parse_mode="Markdown")
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")


@guarded("uuid")
async def uuid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = 1
    if context.args and context.args[0].isdigit():
        count = int(context.args[0])
    uuids = dev_tools.generate_uuids(count)
    await update.message.reply_text("\n".join(f"`{u}`" for u in uuids), parse_mode="Markdown")


# ---------- Telegram utilities ----------

@guarded("id")
async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await update.message.reply_text(f"👤 {target.first_name} — ID: `{target.id}`", parse_mode="Markdown")
    else:
        user = update.effective_user
        chat = update.effective_chat
        await update.message.reply_text(
            f"👤 Your ID: `{user.id}`\n💬 Chat ID: `{chat.id}`", parse_mode="Markdown"
        )


FORMATTING_EXAMPLES = (
    "*Telegram formatting cheat-sheet (Markdown)*\n\n"
    "`*bold*` → *bold*\n"
    "`_italic_` → _italic_\n"
    "`` `code` `` → `code`\n"
    "```\n```pre-formatted block```\n```\n"
    "`[link](https://example.com)` → [link](https://example.com)"
)


@guarded("fmt")
async def fmt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(FORMATTING_EXAMPLES, parse_mode="Markdown")
