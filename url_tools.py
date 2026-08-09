"""
URL metadata extraction (title, description, og:image, status code) and
QR code generation.
"""
import re
from urllib.parse import urlparse

import qrcode
import requests

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TaskMasterBot/1.0)"}


def get_url_metadata(url: str) -> dict:
    if not urlparse(url).scheme:
        url = "https://" + url

    resp = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
    html = resp.text

    def meta(pattern):
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    title = meta(r"<title[^>]*>(.*?)</title>")
    description = meta(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']')
    og_title = meta(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']')
    og_image = meta(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']')

    return {
        "url": resp.url,
        "status_code": resp.status_code,
        "title": og_title or title,
        "description": description,
        "image": og_image,
        "content_type": resp.headers.get("Content-Type"),
        "server": resp.headers.get("Server"),
    }


def generate_qr(data: str, output_path: str) -> str:
    img = qrcode.make(data)
    img.save(output_path)
    return output_path
