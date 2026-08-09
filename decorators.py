"""
Cross-cutting decorators applied to every command/callback handler:
- guarded(): checks ban status + rate limit + logs usage, in one line.
"""
import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def guarded(command_name: str):
    """Decorator for command/message handlers.
    Wraps the handler with ban check, rate limiting, and usage logging.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if user is None:
                return

            database.upsert_user(user.id, user.username or "", user.first_name or "")

            if database.is_banned(user.id):
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "🚫 You have been banned from using this bot."
                    )
                return

            allowed, retry_after = rate_limiter.allow(user.id)
            if not allowed:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        f"⏳ You're sending requests too fast. Try again in {retry_after:.0f}s."
                    )
                database.log_command(user.id, command_name, success=False)
                return

            try:
                result = await func(update, context, *args, **kwargs)
                database.log_command(user.id, command_name, success=True)
                return result
            except Exception as e:
                logger.exception("Error in handler %s", command_name)
                database.log_command(user.id, command_name, success=False)
                if update.effective_message:
                    await update.effective_message.reply_text(
                        f"❌ Something went wrong while running that. ({e.__class__.__name__})"
                    )

        return wrapper

    return decorator
