"""
ASCII banner generation via pyfiglet.
"""
import pyfiglet


def make_banner(text: str, font: str = "standard") -> str:
    text = text[:40]  # keep banners reasonably sized for Telegram
    try:
        return pyfiglet.figlet_format(text, font=font)
    except pyfiglet.FontNotFound:
        return pyfiglet.figlet_format(text, font="standard")


def list_fonts(limit: int = 30) -> list[str]:
    return sorted(pyfiglet.FigletFont.getFonts())[:limit]
