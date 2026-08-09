"""
Password generation (cryptographically secure via `secrets`) and hashing.
"""
import hashlib
import secrets
import string


def generate_password(length: int = 16, use_upper=True, use_lower=True, use_digits=True, use_symbols=True) -> str:
    length = max(4, min(length, 128))
    pool = ""
    if use_lower:
        pool += string.ascii_lowercase
    if use_upper:
        pool += string.ascii_uppercase
    if use_digits:
        pool += string.digits
    if use_symbols:
        pool += "!@#$%^&*()-_=+[]{}"
    if not pool:
        pool = string.ascii_letters + string.digits

    # Ensure at least one char from each selected category
    password_chars = []
    categories = []
    if use_lower:
        categories.append(string.ascii_lowercase)
    if use_upper:
        categories.append(string.ascii_uppercase)
    if use_digits:
        categories.append(string.digits)
    if use_symbols:
        categories.append("!@#$%^&*()-_=+[]{}")

    for cat in categories:
        password_chars.append(secrets.choice(cat))
    while len(password_chars) < length:
        password_chars.append(secrets.choice(pool))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars[:length])


def hash_text(text: str, algorithm: str = "sha256") -> str:
    algorithm = algorithm.lower()
    if algorithm not in hashlib.algorithms_guaranteed:
        raise ValueError(f"Unsupported algorithm '{algorithm}'")
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def hash_all_common(text: str) -> dict:
    return {algo: hash_text(text, algo) for algo in ("md5", "sha1", "sha256", "sha512")}
