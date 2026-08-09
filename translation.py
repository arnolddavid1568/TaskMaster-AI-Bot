"""
Translation via deep-translator's GoogleTranslator backend (free, no API
key required). Falls back to reporting an error if the network call fails.
"""
from deep_translator import GoogleTranslator


def translate_text(text: str, target_lang: str = "en", source_lang: str = "auto") -> dict:
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    result = translator.translate(text)
    return {"translated": result, "source_lang": source_lang, "target_lang": target_lang}


def list_supported_languages() -> dict:
    return GoogleTranslator().get_supported_languages(as_dict=True)
