"""
Admin-only commands: usage dashboard, user list, ban/unban, recent logs.
Access is gated by config.ADMIN_IDS (set via the ADMIN_IDS env var,
comma-separated Telegram user IDs).
"""
import datetime as dt

from telegram import Update
from telegram.ext import ContextTypes

import config
import database
from utils.task_queue import task_queue


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def admin_only_guard(update: Update) -> bool:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 This command is admin-only.")
        return False
    return True


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only_guard(update):
        return

    total_users = database.get_user_count()
    active_today = database.get_active_today()
    total_commands = database.get_total_commands()
    top = database.get_top_commands(10)

    lines = [
        "📈 *Admin Dashboard*",
        "",
        f"👥 Total users: {total_users}",
        f"🟢 Active today: {active_today}",
        f"⚙️ Total commands run: {total_commands}",
        f"🧵 Task queue: {task_queue.status}",
        "",
        "*Top commands:*",
    ]
    for row in top:
        lines.append(f"  • {row['command']}: {row['total_uses']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only_guard(update):
        return

    rows = database.get_recent_log(20)
    if not rows:
        await update.message.reply_text("No activity logged yet.")
        return

    lines = ["🧾 *Recent activity:*"]
    for r in rows:
        ts = dt.datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M:%S")
        mark = "✅" if r["success"] else "❌"
        lines.append(f"{mark} `{ts}` user `{r['user_id']}` → /{r['command']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only_guard(update):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/ban <user_id>`", parse_mode="Markdown")
        return
    target_id = int(context.args[0])
    database.set_banned(target_id, True)
    await update.message.reply_text(f"🚫 Banned user {target_id}.")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only_guard(update):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/unban <user_id>`", parse_mode="Markdown")
        return
    target_id = int(context.args[0])
    database.set_banned(target_id, False)
    await update.message.reply_text(f"✅ Unbanned user {target_id}.")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /broadcast <message> — sends a message to every known user.
    Note: this can hit Telegram rate limits on large user bases; a production
    deployment should throttle sends (e.g. ~25 msgs/sec) - see comment below."""
    if not await admin_only_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast <message>`", parse_mode="Markdown")
        return

    text = " ".join(context.args)
    with database.get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

    sent, failed = 0, 0
    for row in rows:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast done. Sent: {sent}, Failed: {failed}")
