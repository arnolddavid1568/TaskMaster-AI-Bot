"""
Small developer-utility functions: JSON pretty-printing/validation,
Base64 encode/decode, and UUID generation.
"""
import base64
import json
import uuid


def format_json(raw: str) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def minify_json(raw: str) -> str:
    parsed = json.loads(raw)
    return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)


def base64_encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode(text: str) -> str:
    try:
        return base64.b64decode(text.encode("ascii")).decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Invalid Base64 input: {e}")


def generate_uuid(version: int = 4) -> str:
    if version == 1:
        return str(uuid.uuid1())
    return str(uuid.uuid4())


def generate_uuids(count: int = 5) -> list[str]:
    count = max(1, min(count, 50))
    return [str(uuid.uuid4()) for _ in range(count)]
